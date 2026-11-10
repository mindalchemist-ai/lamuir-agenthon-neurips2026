# Backtest timing, cash accounting and return conventions

Use this reference for positions driven by historical signals, cash-funded trades and portfolio performance measurement. It explains financial accounting and information availability, not a strategy's choice of indicator or trading threshold.

## Map the conventions

Identify the observation time, decision time, fill time and valuation time separately. A signal using a period's final price is not available earlier in that period. A rule that fills at a later opening price does not earn the intervening return on newly purchased shares. Explicit task conventions determine corporate-action adjustments, price units, fees, financing, rounding and final liquidation.

An adjusted-price series may incorporate splits or distributions; its adjustment definition matters. Applying distributions again to a total-return-adjusted valuation can double count them. Adjusted fractional holdings describe a synthetic accounting convention and need not equal exchange-traded share counts through a corporate action.

## Cash and holdings at a trade

Let q be signed shares traded, positive for buying; p the execution price; h the shares before execution; B cash; and F the nonnegative transaction charge. The following identity assumes immediate settlement and no external cash movement at that instant.

**Cash and shares after execution**

$$
\begin{gathered}
B_{\mathrm{new}} = B-q\cdot p-F \\
h_{\mathrm{new}} = h+q
\end{gathered}
$$

**Value at the execution price**

$$
B_{\mathrm{new}}+h_{\mathrm{new}}\cdot p = B+h\cdot p-F
$$

Buying does not itself create a loss equal to the purchase notional: cash becomes an asset. Selling converts an asset to cash. Fees reduce equity. Between trades, financing accrues according to the stated lending/borrowing convention and holdings are marked to the chosen valuation price.

For a long purchase with flat charge f, proportional rate c and available cash B, assuming these are charged only when a positive trade occurs:

**Cash-feasible whole-share limit**

$$
q_{\mathrm{max}} = \max (0, \operatorname{floor}((B-f)/(p\cdot (1+c))))
$$

A risk budget divided by a stop distance is a sizing heuristic, not a loss guarantee: a gap can make the realized exit worse than the stop level. A trailing-stop decision depends on when its reference peak is observed; it does not imply execution at that peak or stop price.

## Returns from marked equity

For positive consecutive portfolio values $V_{\mathrm{prev}}$ and V, with no external flows between them:

**Single-period simple return**

$$
r = V/V_{\mathrm{prev}}-1
$$

When deposits or withdrawals occur, a raw value ratio mixes capital flows with performance. Time-weighted returns split the measurement at external flows and link the resulting subperiod returns. Purchases and sales within the portfolio are internal transfers, not external contributions.

**Geometrically linked wealth index**

$$
W_{t} = \prod _{j=1}^{t} (1+r_{j})
$$

A signal may deliberately sum historical returns or compound them; these are different ranking rules. Changing one to the other is not a harmless numerical improvement.

## Annualization and risk measures

Let A be observations per year, n the number of measured periods, and $s_{r}$ the standard deviation under the prescribed divisor. Arithmetic annual return and geometric annual growth answer different questions.

**Arithmetic annual mean**

$$
\mu _{\mathrm{annual}} = A\cdot \operatorname{mean}(r)
$$

**Compound annual growth for positive terminal wealth**

$$
\mathrm{growth}_{\mathrm{annual}} = W_{n}^{A/n}-1
$$

**Conventional volatility scaling**

$$
\mathrm{vol}_{\mathrm{annual}} = \sqrt{A}\cdot s_{r}
$$

The last expression assumes an appropriate uncorrelated-return approximation; serial covariance changes multi-period variance. Sharpe's numerator ordinarily uses excess returns and arithmetic mean. A specified alternative such as growth divided by volatility must be labeled as that convention, not silently replaced. Zero volatility makes the usual ratio undefined.

**Drawdown with positive high-water mark $H_{t}$**

$$
\begin{gathered}
H_{t} = \max (W_{\mathrm{initial}},W_{1},\ldots ,W_{t}) \\
\mathrm{drawdown}_{t} = 1-W_{t}/H_{t}
\end{gathered}
$$

Maximum drawdown is the maximum of this positive loss fraction. Whether the initial capital point belongs to the observed curve must be explicit; omitting it can hide a loss in the first period. Position-price drawdown and portfolio-equity drawdown differ when cash, leverage or fees are present.

## Long-short and repeated estimation

Net exposure is the sum of signed weights; gross exposure is the sum of their absolute values. A short book can be written two ways: signed weights, where each short weight is negative (with gross g split equally across n shorts, $-g/n$) and P&L is the sum of weight times return; or positive short sizes, where P&L is the long leg minus the short leg. Use one of them, not both, since applying a negative weight and then subtracting the short leg cancels the short side. Derive each sign from its long or short label, and check that the short leg's P&L has the opposite sign to its names' returns. A unit long leg minus a unit short leg has gross exposure two before any financing convention, so its reported return needs a stated capital denominator. Equity weights, return-spread indices and invested dollars are not interchangeable.

Forecasts, fitted transformations and rankings use information available by the decision time. When a position is the product of a signal and a volatility-based size, align the whole position with the return interval it earns: the holding applied to the return of day t is built only from data through day t−1, both its signal and its volatility size. Lagging only the signal while the size uses a volatility that already includes the same day's squared return is look-ahead; lagging a series that is already aligned shifts it twice. A rule that defines a position at every date has no flat state; a warm-up period without enough history is dropped or handled as the task states, not set to zero exposure silently. The evaluated return series starts at the stated first trading date; days before it belong to the warm-up and enter no performance statistic unless the task says so. When the task states an evaluation or trading start after a signal or risk warm-up → every statistic and regression (mean, volatility, Sharpe, drawdown, hit rate, factor regression) uses the returns from that start onward, flat or cash days inside the evaluation period included → check that the number of return observations equals the length of the stated evaluation period. A task that asks for full-history statistics keeps the full history.

```python
eval_ret = port_ret.loc[eval_start:]                     # the stated first trading or evaluation date
assert len(eval_ret) == (dates >= eval_start).sum()
hit_rate = (eval_ret > 0).mean()                          # every statistic and regression from eval_ret, not port_ret
```
A single lag is enough when the weights are built from data through t−1 and applied to the return of t; building from t−1 data and then shifting again uses information two days old. Once a sample already contains its rolling warm-up, do not trim it again. Walk-forward evaluation separates historical estimation from subsequent realizations. Selecting a model using a later full sample is a retrospective comparison, not proof of live predictive performance.

When a strategy holds constant target weights from one rebalance date to the next → start the weight frame as NaN, set the rebalance rows, then forward-fill. Rows before the first rebalance have no target yet: the task decides whether the evaluation starts at the first rebalance, holds no position until then, or holds a stated initial portfolio, and the choice changes volatility, Sharpe ratio and drawdown over that stretch:

```text
weights = pd.DataFrame(np.nan, index=dates, columns=assets)
weights.loc[rebalance_dates] = targets              # a complete row per rebalance: every asset, 0 for those exited
weights = weights.ffill()
before_first = weights.isna().all(axis=1)          # rows before the first rebalance: fill with the stated holding, or drop them
```

Check that every non-rebalance day carries the most recent target, an all-zero target included; a frame started with zeros stays zero between rebalances after `ffill`, so positions exist only on rebalance days. When the strategy holds share counts whose weights drift with prices, carry the shares instead and recompute the weights each day.

When a cross-sectional long-short book is rebalanced on the first trading day of every month from a daily signal → use the tested engine in the Python session rather than your own holdings loop: hand-written loops for this book keep slipping on the rebalance dates, the signal lag, exits and the first position. Write your own only where the task's rules differ from the contract in the comments below:

```python
from backtest_tools import monthly_long_short, factor_regression, arithmetic_metrics
res = monthly_long_short(returns, signal, first_trade_row, n_long, n_short, w_long, w_short, cost_bps)
# returns: daily simple returns, one column per asset, on the trading-day index (missing values handled as the task says)
# signal: same index and columns; row t uses data through row t; do not shift it (the engine ranks on row i-1 for row i)
# first_trade_row: the stated trading start as a row position; the book opens there, then rebalances each later month start
# each rebalance writes the whole book (exits at 0); costs are cost_bps per unit of turnover, on the first row it earns
# limits: pass max_position= only for a cap the task states; a stated per-name weight that breaks a stated cap is a conflict to report
r = res["returns"]                                                # daily returns from first_trade_row on
assert res["n_rebalances"] == 1 + sum(d > returns.index[first_trade_row] for d in returns.index.to_series().groupby(returns.index.to_period("M")).min())
```

When a long-short strategy rebalances monthly from a daily signal and trading starts on a stated row → the book opens on the trading start row (even mid-month) and is rebalanced on the first trading day of each later month; each rebalance ranks on the previous row's signal, known at that close. Here `signal` row t uses data up to row t with no shift of its own, and it shares the returns' date index (a signal built on an integer index and reindexed to dates is all NaN). Adapt the signal and sizes to the task:

```python
dates = returns.index                                            # trading days
first_of_month = dates.to_series().groupby(dates.to_period("M")).min()
start = dates[trade_start_row]                                   # the stated trading start
rebal = [start] + [d for d in first_of_month if d > start]       # open at the start, then each later month start
assert signal.index.equals(dates)
w = pd.DataFrame(np.nan, index=dates, columns=returns.columns)
for d in rebal:
    s = signal.iloc[dates.get_loc(d) - 1].dropna()               # previous row: known at the prior close
    assert len(s) >= n_long + n_short and s.std() > 0             # a valid, varying cross-section
    target = pd.Series(0.0, index=returns.columns)
    target[s.nlargest(n_long).index] = w_long
    target[s.nsmallest(n_short).index] = -w_short
    w.loc[d] = target                                             # the complete row, exits at 0
w = w.ffill().fillna(0.0)                                         # flat before the start
cost = (w - w.shift(1).fillna(0.0)).abs().sum(axis=1) * cost_rate
port = (w * returns).sum(axis=1) - cost                          # the rebalance row's weights earn from that row
eval_ret = port.loc[start:]
assert len(rebal) == 1 + sum(d > start for d in first_of_month)
```

## Accounting checks

At a trade, the change in equity at its fill price equals negative fees. With all positions closed and no flows or financing, terminal cash minus initial cash equals the sum of net completed-trade profits. If positions remain open, unrealized profit also belongs in total equity. The product of value-based returns reproduces the terminal-to-initial equity ratio on the same interval.

## Sources

[CFA Institute, GIPS Standards for Asset Owners (2020)](https://www.cfainstitute.org/-/media/documents/code/gips/2020-gips-standards-asset-owners.pdf), calculation methodology, for external-flow treatment and linked returns. Cash conservation, annualization distinctions and gross/net exposure above are direct accounting or algebraic identities. This note does not assert GIPS compliance of a backtest.
