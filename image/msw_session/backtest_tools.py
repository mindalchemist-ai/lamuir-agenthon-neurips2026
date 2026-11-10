'Long-short backtest building blocks for the Python session: one information clock, complete-book rebalances.\n'
import numpy as np
import pandas as pd


def month_start_rows(index: pd.DatetimeIndex, start: int = 0) -> list[int]:
    """Row `start` plus the first row of every later calendar month (rebalance at the start of each month)."""
    idx = pd.DatetimeIndex(index); ym = idx.year * 12 + idx.month
    return [start] + [i for i in range(start + 1, len(idx)) if ym[i] != ym[i - 1]]


def _as_weights(w, columns) -> np.ndarray:
    """A weight vector aligned to columns: a Series/dict is matched by label (missing -> 0), an array by position."""
    if isinstance(w, (pd.Series, dict)):
        return pd.Series(w).reindex(columns).fillna(0.0).to_numpy(float)
    w = np.asarray(w, float)
    if w.shape != (len(columns),):
        raise ValueError(f"weight vector has shape {w.shape}, expected ({len(columns)},)")
    return w


def rebalanced_returns(returns: pd.DataFrame, rebalance_weights: dict, initial: pd.Series | None = None,
                       cost_bps: float = 0.0) -> pd.Series:
    """Daily simple portfolio returns of a strategy rebalanced at given rows, on returns' own index.

    rebalance_weights maps a row position t of `returns` to the weight vector set at row t's close, using data
    through t; it earns from row t+1 on. (A trade "on day i using the signal known at the previous close" is key
    i-1.) Rows before the first rebalance hold `initial` (default equal weights; pass zeros to start flat). Each
    rebalance costs cost_bps / 1e4 * sum |w_new - w_old|, charged on the first row the new weights earn.
    """
    n = returns.shape[1]
    w = _as_weights(initial if initial is not None else np.full(n, 1.0 / n), returns.columns); out = np.empty(len(returns)); r = np.nan_to_num(returns.to_numpy(float)); cost = 0.0
    for t in range(len(returns)):
        out[t] = float(w @ r[t]) - cost; cost = 0.0
        if t in rebalance_weights:
            new = _as_weights(rebalance_weights[t], returns.columns)
            cost = cost_bps / 1e4 * np.abs(new - w).sum(); w = new
    return pd.Series(out, index=returns.index)


def monthly_long_short(returns: pd.DataFrame, signal: pd.DataFrame, first_trade_row: int, n_long: int, n_short: int,
                       weight_long: float, weight_short: float, cost_bps: float = 0.0,
                       max_position: float | None = None) -> dict:
    """Cross-sectional long-short book opened on first_trade_row and rebalanced on the first row of every later month.

    Information clock: `signal` row t uses data up to and including row t, with no shift of its own; the engine ranks
    on row i-1 (known at the previous close) for a book that earns from row i. Shifting the signal as well lags it twice.
    Each rebalance replaces the whole book: a fresh zero vector, +weight_long on the top n_long and -weight_short on the
    bottom n_short, so a name that leaves either leg goes to 0. Before first_trade_row the book is flat. Costs are
    cost_bps per unit of turnover, charged on the first row the new book earns.
    max_position (default None: not applied) clips each position to +-max_position. Apply every limit the task states;
    when a stated per-name weight and a stated cap disagree, the task text decides, and the conflict should be reported.
    Returns the daily returns from first_trade_row on, the rebalance rows, their count and the weights by date.
    """
    rows = month_start_rows(returns.index, first_trade_row); book = {}
    for i in rows:
        s = signal.iloc[i - 1].dropna(); w = pd.Series(0.0, index=returns.columns)
        w[s.nlargest(n_long).index] = weight_long; w[s.nsmallest(n_short).index] = -weight_short
        book[i - 1] = w if max_position is None else w.clip(-max_position, max_position)
    r = rebalanced_returns(returns, book, initial=pd.Series(0.0, index=returns.columns), cost_bps=cost_bps)
    return dict(returns=r.iloc[first_trade_row:], rebalance_rows=rows, n_rebalances=len(rows),
                weights={returns.index[i + 1]: w for i, w in book.items()})


def factor_regression(r, factors, periods: int = 252) -> dict:
    """OLS of r on an intercept plus factor columns: annualised alpha (intercept * periods), betas,
    tracking error std(residuals, ddof=1) * sqrt(periods) and information ratio alpha / tracking error."""
    y = np.asarray(r, float); F = np.asarray(factors, float); X = np.column_stack([np.ones(len(y)), F])
    b = np.linalg.lstsq(X, y, rcond=None)[0]; res = y - X @ b
    te = float(np.std(res, ddof=1) * np.sqrt(periods)); alpha = float(b[0] * periods)
    return dict(alpha=alpha, betas=[float(x) for x in b[1:]], tracking_error=te,
                information_ratio=alpha / te if te > 0 else 0.0, residuals=res)


def arithmetic_metrics(x: pd.Series, annualization: float = 252.0, ddof: int = 1) -> dict:
    """Simple-return metrics: mean*factor, std(ddof)*sqrt(factor), their ratio, max drawdown of (1+x).cumprod()
    as a positive magnitude, and the share of positive days."""
    x = pd.Series(x).dropna(); ann = x.mean() * annualization; vol = x.std(ddof=ddof) * np.sqrt(annualization)
    wealth = (1 + x).cumprod(); mdd = float(-(wealth / wealth.cummax() - 1).min())
    return dict(annualized_return=float(ann), annualized_volatility=float(vol),
                sharpe_ratio=float(ann / vol) if vol > 0 else 0.0, max_drawdown=mdd, win_rate=float((x > 0).mean()))
