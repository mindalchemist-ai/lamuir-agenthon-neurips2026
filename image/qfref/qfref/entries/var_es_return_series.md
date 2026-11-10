# VaR and ES of return series: loss sign, quantile rules, tail means, weights, horizons and windows

Use this note for value-at-risk (VaR), expected shortfall (ES, CVaR) and related backtests on return series, simulated wealth paths or simulated credit losses. Most steps below have more than one standard reading. Each skeleton takes the choice as an argument: read its value from the task instructions, and when the instructions leave it open, pick one, write the choice in a comment, and use the same choice in every output. The skeletons assume `import numpy as np`, `import pandas as pd` and `from scipy import stats, special`.

## 1. Loss sign and confidence level

A loss is the negative of a return or P&L, so the risky side is the upper tail of the loss. A confidence level such as 95% corresponds to the tail probability 1 - level. Some texts call the confidence level alpha, others call the tail probability alpha; decide from the numbers the task lists (0.95 and 0.99 are confidence levels, 0.05 and 0.01 are tail probabilities).

```text
def to_loss(returns):
    loss = -np.asarray(returns, dtype=float)
    return loss[np.isfinite(loss)]
```

## 2. Empirical VaR: which quantile rule

With n scenarios the empirical quantile is not unique. "kth_worst" takes the k-th largest loss with k = ceil(n * tail), which is the classical historical-simulation order statistic and equals -np.quantile(returns, tail, method="inverted_cdf"). In floating point 1 - 0.95 is 0.05000000000000004, so when n * tail is a whole number a step rule can move one observation further; the skeleton rounds the tail probability first. A NumPy method name ("linear" is the NumPy default and interpolates between neighbouring order statistics; "lower", "higher", "nearest", "inverted_cdf" pick one observed value) applies np.quantile to the losses at the confidence level. "linear" is symmetric (the loss quantile at the level is minus the return quantile at the tail); the step rules are not, so np.quantile(loss, level, method="inverted_cdf") is the (k+1)-th worst loss when n * tail is a whole number k.

## 3. ES: which tail mean

Three tail means are in use. "strict" is E[L | L > VaR], the mean of losses above VaR; it is empty, hence undefined, when VaR is the largest loss. "inclusive" is E[L | L >= VaR], which always contains the VaR scenario. "tail_mean" averages exactly the worst tail * n outcomes and takes only the needed fraction of the boundary scenario (Acerbi and Tasche 2002); it equals min over c of c + mean(max(L - c, 0)) / tail. For continuous data the three nearly agree. For losses on a grid (a count of defaults times a fixed loss, rounded P&L) many scenarios sit exactly at VaR and the three can differ by a large amount. Without ties at VaR (continuous data) the strict and inclusive means are equal. When losses tie at VaR (resampled or bootstrapped rows, simulated or discrete losses, rounded P&L), the default is the inclusive mean E[L | L >= VaR], the tail conditional expectation of Artzner, Delbaen, Eber and Heath (1999, Mathematical Finance 9(3), Definition 5.1: TCE = -E[X | X <= -VaR] on returns). Use the strict mean only when the task writes "strictly greater than VaR" or a formula with a strict inequality, and tail_mean when it asks for the "integrated quantile", "average VaR over the tail" or "coherent ES". Words such as "exceeding VaR" or "beyond VaR" do not by themselves ask for the strict mean. Compute both, print their difference and the number of losses equal to VaR, then report the one chosen.

```text
def empirical_var_es(returns, level, q_method, es_rule):
    loss = to_loss(returns)
    tail = round(1.0 - level, 12)
    worst_first = np.sort(loss)[::-1]
    if q_method == "kth_worst":
        k = max(int(np.ceil(len(loss) * tail - 1e-9)), 1)
        var = worst_first[k - 1]
    else:
        var = np.quantile(loss, level, method=q_method)
    if es_rule == "strict":
        above = loss[loss > var]
        es = above.mean() if above.size else np.nan
    elif es_rule == "inclusive":
        es = loss[loss >= var].mean()
    else:
        m = len(loss) * tail
        j = int(np.floor(m + 1e-9))
        es = (worst_first[:j].sum() + (m - j) * worst_first[min(j, len(loss) - 1)]) / m
    assert np.isnan(es) or es >= var - 1e-12
    return var, es
```

## 4. Probability-weighted (age-weighted) VaR and ES

Age weighting gives scenario i the probability decay**age_i / sum(decay**age), with age 0 for the newest observation. The weights stay attached to their scenarios when the losses are sorted. The tail is the worst losses, so sort the losses from the worst and accumulate weight from there until the tail probability is reached; sorting returns in ascending order and averaging the entries after the quantile position averages the gains instead. The rule below is the weighted form of "kth_worst" (equal weights give the same VaR as section 2) and equals -np.quantile(returns, tail, weights=w, method="inverted_cdf") with the rounded tail, except when the cumulative weight lands exactly on the tail probability, where summation rounding decides; the skeleton uses a small tolerance there.

```text
def weighted_var_es(returns, level, decay):
    r = np.asarray(returns, dtype=float)
    w = decay ** np.arange(len(r))[::-1]
    w = w / w.sum()
    loss = -r
    order = np.argsort(-loss, kind="stable")
    L, p = loss[order], w[order]
    tail = round(1.0 - level, 12)
    cum = np.cumsum(p)
    i = int(np.searchsorted(cum, tail - 1e-12))
    var = L[i]
    before = cum[i - 1] if i > 0 else 0.0
    es_tail_mean = (np.dot(p[:i], L[:i]) + (tail - before) * L[i]) / tail
    at_or_above = L >= var
    es_inclusive = np.dot(p[at_or_above], L[at_or_above]) / p[at_or_above].sum()
    assert es_tail_mean >= var - 1e-12 and es_inclusive >= var - 1e-12
    return var, es_tail_mean, es_inclusive
```

When a multi-period scenario is weighted, its age is counted from the scenario's last day.

## 5. Parametric VaR and ES

Normal: VaR = -mu + sd * z and ES = -mu + sd * pdf(z) / tail, with z = norm.ppf(level). "Absolute" VaR keeps the mean; "relative" or "zero-mean" VaR sets mu = 0. The standard deviation divisor is a separate choice: ddof=1 is the unbiased sample variance, ddof=0 the maximum-likelihood one.

Student-t: scipy.stats.t.fit returns (df, loc, scale) by maximum likelihood with all three free. The scale is not the standard deviation: sd = scale * sqrt(df / (df - 2)) for df > 2. The ES formula needs df > 1; check df after fitting. Fixed parameters are passed as floc, fscale or f0 (df).

A "standardized t" has two meanings. (1) scipy's t(df) itself, loc 0 and scale 1, whose variance is df / (df - 2). (2) a t rescaled to unit variance, with scale sqrt((df - 2) / df). Use (1), t(df) as it is, when the task rules out shifting or rescaling the distribution or gives quantiles of t(df) directly; rescale to (2) only when the task says "unit variance" or asks for a t with the same variance as a normal it is compared with. For a sample drawn from or fitted to a distribution, compare its variance with df / (df - 2) to see which one is in use.

```text
def normal_var_es(returns, level, ddof, include_mean):
    x = np.asarray(returns, dtype=float)
    mu = x.mean() if include_mean else 0.0
    sd = x.std(ddof=ddof)
    z = stats.norm.ppf(level)
    return -mu + sd * z, -mu + sd * stats.norm.pdf(z) / (1.0 - level)

def student_t_var_es(returns, level, fit_kwargs, include_mean):
    df, loc, scale = stats.t.fit(np.asarray(returns, dtype=float), **fit_kwargs)
    assert df > 1, "ES of a t distribution needs df > 1"
    q = stats.t.ppf(level, df)
    m = loc if include_mean else 0.0
    var = -m + scale * q
    es = -m + scale * stats.t.pdf(q, df) * (df + q * q) / ((df - 1.0) * (1.0 - level))
    return var, es, (df, loc, scale)
```

## 6. EWMA covariance

The recursion C_t = lam * C_(t-1) + (1 - lam) * x_t x_t' needs a starting matrix: the first observation's outer product, a sample covariance of the first m rows, or zero. It also needs a mean convention: raw returns (zero mean, the RiskMetrics form) or demeaned returns. The matrix after the last observation is the forecast for the next period, which is what "current" or "as of the last date" usually means. Annualize a volatility with the square root of the periods per year that the data frequency implies (for example 252 trading days, 52 weeks or 12 months); the frequency comes from the data, not from a fixed number.

```text
def ewma_cov(R, lam, seed_rule, demean):
    X = np.asarray(R, dtype=float)
    if demean:
        X = X - X.mean(axis=0)
    if seed_rule == "first_outer":
        C, start = np.outer(X[0], X[0]), 1
    elif seed_rule == "zero":
        C, start = np.zeros((X.shape[1], X.shape[1])), 0
    else:
        start = int(seed_rule)
        C = np.cov(X[:start].T, ddof=1)
    for x in X[start:]:
        C = lam * C + (1.0 - lam) * np.outer(x, x)
    return C

def annualized_vol(C, w, periods_per_year):
    return float(np.sqrt(w @ C @ w * periods_per_year))
```

For one series, seed "first_outer" with zero mean equals pd.Series(x**2).ewm(alpha=1 - lam, adjust=False).mean().

## 7. Multi-period horizons

Square-root-of-time scaling multiplies a one-period VaR or ES by sqrt(h); it is exact for independent normal returns with zero mean. With a mean, the h-period normal VaR is -h * mu + sqrt(h) * sd * z. For simulation-type methods an h-period scenario is the sum of h consecutive log returns, or the compounded product of h simple returns. Overlapping windows step one period at a time (n - h + 1 scenarios, strongly dependent); non-overlapping windows step h periods (about n / h scenarios) and need an anchor, either the first or the last observation.

```text
def horizon_returns(returns, h, kind, overlapping, anchor):
    x = pd.Series(np.asarray(returns, dtype=float))
    agg = x.rolling(h).sum() if kind == "log" else np.expm1(np.log1p(x).rolling(h).sum())
    agg = agg.dropna().to_numpy()
    if overlapping:
        return agg
    return agg[::h] if anchor == "first" else agg[::-1][::h][::-1]
```

## 8. Backtesting a VaR forecast

The forecast for day t uses data through day t - 1 only. An expanding window uses all earlier days; a rolling window uses the last W. A stated minimum number of observations sets the first test day. An exception is a loss above the forecast ("exceeds"); a loss equal to it counts only under an "at or above" wording. The Kupiec proportion-of-failures statistic is a likelihood ratio with one degree of freedom; scipy.special.xlogy keeps the log-likelihood finite when there are no exceptions or only exceptions.

```text
def var_backtest(returns, level, min_obs, window, q_method, strict_exceedance):
    r = np.asarray(returns, dtype=float)
    hits = []
    for t in range(min_obs, len(r)):
        hist = r[:t] if window is None else r[max(0, t - window):t]
        var_t, _ = empirical_var_es(hist, level, q_method, "inclusive")
        hits.append(-r[t] > var_t if strict_exceedance else -r[t] >= var_t)
    hits = np.array(hits)
    T, x, p = len(hits), int(hits.sum()), 1.0 - level
    loglik = lambda q: special.xlogy(x, q) + special.xlogy(T - x, 1.0 - q)
    lr = -2.0 * (loglik(p) - loglik(x / T))
    return T, x, x / T, float(stats.chi2.sf(lr, 1))
```

## 9. Cleaning a data feed and counting observations

Invalid entries in a return table include missing values, text in numeric columns, infinities, unparseable dates and repeated dates. A return is a change, not a level, so forward-filling a missing return repeats an earlier day's move that did not happen; filling with zero asserts that nothing moved. Dropping each row with any invalid value (listwise) keeps the assets aligned on the same dates. A large but finite return is a data point, not an anomaly, unless the task gives a rule for it. A count of valid observations is the number of rows that survive cleaning; the number of rows inside an estimation window is a different count. An estimation window of the latest N rows is cut from the cleaned table, and an unset N means the full cleaned sample.

```text
def clean_return_table(raw, date_col, value_cols, duplicate_keep, missing_rule):
    df = raw.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    vals = df[value_cols].apply(pd.to_numeric, errors="coerce").replace([np.inf, -np.inf], np.nan)
    df = pd.concat([df[[date_col]], vals], axis=1).dropna(subset=[date_col])
    df = df.drop_duplicates(subset=date_col, keep=duplicate_keep).sort_values(date_col).set_index(date_col)
    if missing_rule == "drop_row":
        df = df.dropna(how="any")
    elif missing_rule == "zero":
        df = df.fillna(0.0)
    return df, {"rows_read": len(raw), "rows_valid": len(df)}

def most_recent(df, n):
    if n is None:
        return df
    assert int(n) > 0
    return df.iloc[-int(n):]
```

## 10. Rolling estimates, rebalance dates and the evaluated sample

A rolling estimate dated t uses either rows t - W + 1 through t (it includes day t) or rows t - W through t - 1 (only earlier days). A quantity that sets the holdings earning day t's return must not contain day t; with the first form, apply it from day t + 1. pandas rolling uses min_periods equal to the window by default; min_periods=1 produces estimates from one or two rows. "Trailing N returns" means the last N values of the series, series.iloc[-N:], not the full history.

A month-end rebalance date is the latest date of that month present in the data. When the data stop before the month ends, the final row is not that month's last trading day.

Before the first rebalance there is no target portfolio. The evaluated sample can start at the first rebalance, hold no position until then, or hold a stated initial portfolio; the choice changes volatility, Sharpe ratio and drawdown. Days before the first available estimate are warm-up days.

```text
def rolling_slices(n_rows, W, include_current):
    for t in range(n_rows):
        lo, hi = (t - W + 1, t + 1) if include_current else (t - W, t)
        if lo >= 0:
            yield t, slice(lo, hi)

def month_last_rows(dates):
    d = pd.Series(pd.DatetimeIndex(dates), index=pd.DatetimeIndex(dates))
    last = d.groupby(d.index.to_period("M")).max()
    final = d.iloc[-1]
    month_complete = (final + pd.offsets.BDay(1)).month != final.month
    return [x for x in last if x != final or month_complete]

def hold_between_rebalances(targets, dates, before_first, effective_next_day):
    w = pd.DataFrame(np.nan, index=dates, columns=targets.columns)
    w.loc[targets.index] = targets.to_numpy()
    if effective_next_day:
        w = w.shift(1)
    w = w.ffill()
    if isinstance(before_first, str) and before_first == "start_at_first":
        return w.dropna(how="all")
    return w.fillna(pd.Series(before_first, index=targets.columns))
```

## 11. Portfolio return, leverage and scaling to a risk limit

With fractions w of wealth in risky assets with simple returns R, three account models are in use. "weighted_sum" is R @ w: the portfolio return is the weighted sum of the asset returns, and the remainder 1 - sum(w) earns nothing. "financed" is rf + (R - rf) @ w: the remainder is lent or borrowed at the cash rate. "excess_only" is (R - rf) @ w. When the task describes no cash account or financing rate for the remainder, the weighted sum is the literal reading and a cash leg is an added assumption; state it if you add one. The same period returns then drive wealth, Sharpe ratio and drawdown.

Gross exposure (leverage) is sum(|w|); net exposure is sum(w). A per-period cash rate from an annual rate is r / periods_per_year under simple division and (1 + r) ** (1 / periods_per_year) - 1 under compounding.

To meet a risk limit along a fixed direction, "comply with", "cap at" or "not exceed" reads as c = min(1, limit / risk), which scales down only; "scale to" or "target" reads as c = limit / risk.

```text
def portfolio_period_returns(R, w, account, rf_per_period):
    R, w = np.asarray(R, dtype=float), np.asarray(w, dtype=float)
    if account == "weighted_sum":
        return R @ w
    if account == "financed":
        return rf_per_period + (R - rf_per_period) @ w
    return (R - rf_per_period) @ w

def exposure(w):
    w = np.asarray(w, dtype=float)
    return {"gross": float(np.abs(w).sum()), "net": float(w.sum())}

def risk_scale(risk, limit, rule):
    assert risk > 0
    return min(1.0, limit / risk) if rule == "cap" else limit / risk
```

## Random streams in a simulation

Create the random generator once, before the simulation (`rng = np.random.default_rng(seed)`), and take every draw from that same object. A sampler or loop that calls `np.random.default_rng(seed)` again restarts the stream each time: later draws repeat the first numbers, the simulated losses lose most of their variation, and simulated quantiles come out systematically too low.

Arrays drawn from one generator take consecutive numbers, so the order of the draws fixes every sample. For a mixture that draws one array per component and then selects, draw the components in the order the task lists them; inside a single expression such as `np.where(u < p, a(), b())` the arguments are evaluated left to right, so swapping them, or flipping the condition to select the other component first, changes which numbers each component gets.

```python
u = rng.rand(n)                                  # selector first, if the task draws it first
first = rng.normal(0.0, sd_first, n)             # the component the task lists first
second = rng.normal(0.0, sd_second, n)
x = np.where(u < p_first, first, second)
```

## 13. Group breakdowns of a portfolio loss

For groups that partition the portfolio, two "mean loss" figures exist per group: the mean over scenarios of the group's total loss, and the mean loss of a single member. They differ by the group size. Group totals add up to the portfolio mean loss; per-member means do not. Wording such as "per name", "per bond" or "average member" points to the per-member figure; a table presented as the breakdown of a portfolio figure points to the group total. When the wording fits both, write the choice in a comment and check the sum.

```text
def group_loss_means(loss_by_name, groups):
    out = {}
    for label, cols in groups.items():
        total = loss_by_name[:, cols].sum(axis=1).mean()
        per_member = loss_by_name[:, cols].mean()
        assert np.isclose(total, len(cols) * per_member)
        out[label] = {"group_total": total, "per_member": per_member}
    assert np.isclose(sum(v["group_total"] for v in out.values()), loss_by_name.sum(axis=1).mean())
    return out
```

## 14. After a correction, rewrite every file that used it

When a function is fixed after its results were written, the files written earlier still hold the old values. Recompute and rewrite every output that used it, read the files back, and check the invariants that hold under every convention above: ES >= VaR for the same level and method, VaR at a higher level >= VaR at a lower level for the same method, and the expected number of rows and labels.

## Task wording -> API arguments

np.quantile and np.percentile: method="linear" is the default and interpolates; "inverted_cdf" is the step inverse of the empirical CDF; "lower", "higher", "nearest" and "midpoint" choose between the two neighbouring order statistics; weights=... is accepted only with method="inverted_cdf". np.percentile takes the level in percent.

scipy.stats distribution fit: dist.fit(x) estimates every parameter by maximum likelihood; floc=..., fscale=... and f0=... (shape) hold a parameter fixed; the returned order is shapes, then loc, then scale. stats.norm.fit returns the mean and the ddof=0 standard deviation.

Standard deviation: np.std and np.var default to ddof=0; pandas Series.std, DataFrame.std and DataFrame.cov default to ddof=1. "Sample" or "unbiased" means ddof=1; "population" or "maximum likelihood" means ddof=0.

pandas ewm: ewm(alpha=1 - lam, adjust=False) is the recursion seeded with the first value; adjust=True divides by the sum of the weights used so far; span=s means alpha = 2 / (s + 1), halflife=h means alpha = 1 - 0.5 ** (1 / h), com=c means alpha = 1 / (1 + c).

pandas rolling: rolling(W) needs W values by default; min_periods lowers that; the window ends at and includes the current row, so .shift(1) moves it to earlier rows only.


scipy.stats.chi2.sf(lr, 1) is the upper-tail p-value of a one-degree-of-freedom likelihood ratio; scipy.special.xlogy(a, b) returns 0 when a = 0.

## Sources

Jorion, Value at Risk, 3rd ed. (2007), ch. 5 (historical simulation, parametric VaR) and ch. 6 (backtesting). Acerbi and Tasche (2002), J. Banking and Finance 26(7), 1487-1503 (tail mean and conditional means at atoms). Rockafellar and Uryasev (2002), J. Banking and Finance 26(7), 1443-1471 (CVaR minimization formula). Hyndman and Fan (1996), American Statistician 50(4), 361-365 (sample quantile definitions). Boudoukh, Richardson and Whitelaw (1998), Risk 11(5), 64-67 (age-weighted historical simulation). J.P. Morgan/Reuters, RiskMetrics Technical Document, 4th ed. (1996), sec. 5.2 (EWMA). Kupiec (1995), J. Derivatives 3(2), 73-84 (proportion of failures). J.P. Morgan, CreditMetrics Technical Document (1997), ch. 8 (simulation). Docs: NumPy 2.5 numpy.quantile and Random Generator / legacy RandomState; SciPy 1.18 rv_continuous.fit, stats.t, special.xlogy; pandas 3.0 Series.ewm and Series.rolling.

## Sign summary

| Quantity | Readings | Pick by |
|---|---|---|
| Loss | loss = −return (or −P&L); a "negative log-return" series is already a loss | the task's definition; with returns, VaR is the lower tail of returns, with losses the upper tail of losses |
| Reported VaR / ES | a positive loss magnitude, or the return quantile with its negative sign | "loss", "magnitude", "positive" → positive; "return quantile", a formula written with the minus sign, or "≤ 0" → keep the sign; neither → positive magnitude, the usual reporting form, and say so |
| Confidence level vs tail probability | c = 0.99 ↔ tail α = 1 − c = 0.01 | the numbers listed (0.95, 0.99 are levels; 0.05, 0.01 are tails); pass the tail probability to a return quantile and the level to a loss quantile |
| ES tail | mean at or below the return VaR (`<=`), or strictly beyond it (`<`) | `<=` unless the task writes a strict inequality or "strictly"; the two differ only when values tie at the VaR (resampled, simulated or discrete samples) |
| Currency VaR | portfolio value × return-scale VaR | the value the task names (start-of-period value unless stated otherwise) |
| Position direction | a short position's P&L moves opposite to the price; pay/receive and buy/sell legs flip the sign the same way | the position or leg the task describes; compute P&L with the sign before forming losses |

```python
r = np.array([-0.031, 0.012, -0.004, 0.020, -0.018, 0.007, -0.025, 0.001, 0.015, -0.009])
level = 0.9
q_ret = np.quantile(r, 1 - level)              # lower tail of returns
q_loss = np.quantile(-r, level)                # upper tail of losses
assert np.isclose(-q_ret, q_loss)              # the same VaR, as a positive loss magnitude
es_le = -r[r <= q_ret].mean()                  # tail at or below the return VaR
assert es_le >= -q_ret                         # ES is at least VaR in magnitude
```
