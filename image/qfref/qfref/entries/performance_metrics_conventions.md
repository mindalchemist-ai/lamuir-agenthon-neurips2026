# Performance metrics: drawdown, Sharpe ratio, Sortino and Calmar ratios, win rate

Use this note when a task reports performance statistics of a return series or an equity curve. Each metric below has more than one standard reading; the table under each says which wording picks which one and what to use when the task is silent.

## Drawdown

Drawdown at time t compares the curve with its running peak: `dd_t = 1 − W_t / max_{s ≤ t} W_s` for a wealth or equity curve W.

| Choice | Options | Pick by |
|---|---|---|
| Curve | wealth `W_t = W_0 · Π(1 + r_s)` from simple returns; `exp(cumulative log return)` from log returns; a cumulative-return curve `R_t` | the series the task names. With log returns, drawdown is `1 − exp(L_t − max L)`, not the difference of log levels. On a cumulative-return curve, `1 + R_t` is the wealth index; dividing by the peak of `R_t` itself is a different number and is used only when the task writes it |
| First point | the starting capital (or 1.0) as the first point, so a loss in the first period counts; or the period-end values only | starting capital when the task starts the curve from an initial capital or a value of 1 and says nothing else; period-end values when it defines drawdown on the equity curve from the first close |
| Sign | a positive magnitude (0.25 for a 25% fall); or a negative number `(W − peak) / peak` | "magnitude", "non-negative", "peak-to-trough decline" → positive; "as a negative number", "≤ 0", or the formula with `W − peak` → negative; silent → positive magnitude, and use it as a positive denominator in a Calmar ratio |
| Scale | decimal or percent points | the unit notes of the output; see the unit conventions entry |

## Sharpe and Sortino ratios

| Choice | Options | Pick by |
|---|---|---|
| Numerator | mean excess return over a risk-free rate, or the mean return | deduct the risk-free rate when the task gives one and speaks of excess return; do not subtract when it says not to, when it says the risk-free rate is zero, or gives no rate |
| Annualization | `sqrt(A) · mean / std` with A periods per year; or an unannualized ratio | "annualized" → A from the task, else 252 for daily trading data, 12 monthly, 52 weekly, 365 for calendar-day or 24/7 data; silent on annualization → report the per-period ratio only when the task's numbers are per period, and say which |
| Standard deviation | sample (`ddof=1`) or population (`ddof=0`) | the task's statement; silent → `ddof=1`, the sample estimator and the pandas default; numpy's `np.std` defaults to `ddof=0`, so pass it explicitly |
| Zero volatility | undefined | the task's rule (0, null or NaN); never a division by zero written as inf |
| Sortino denominator | downside deviation `sqrt(mean(min(r − target, 0)^2))` over all periods, or the standard deviation of the negative returns only | the formula the task writes; silent → the first (all periods, target 0 or the stated minimum acceptable return) |

Calmar ratio: annualized return divided by the maximum drawdown magnitude over the same period; the annualized return follows the task's rule (arithmetic `mean · A` or geometric `(W_T / W_0)^(A / n) − 1`).

## Win rate and hit rate

| Choice | Options | Pick by |
|---|---|---|
| Unit | closed trades, or periods (days, months) | "trades" → closed round trips; "days", "periods", "hit rate of the signal" → periods |
| Zero result | a loss, excluded, or a win | the task's inequality ("> 0" makes zero a non-win); silent → only results above zero count as wins, and every trade or period stays in the denominator |
| Open position at the end | excluded, or closed at the last price | the task's rule; silent → only closed trades |

```python
r = np.array([0.010, -0.020, 0.015, -0.030, 0.005, 0.0, 0.012])
W0 = 1.0
W = np.concatenate([[W0], W0 * np.cumprod(1 + r)])          # starting capital as the first point
dd = 1 - W / np.maximum.accumulate(W)                         # positive magnitude
max_dd = dd.max()
L = np.concatenate([[0.0], np.cumsum(np.log1p(r))])
assert np.isclose(max_dd, (1 - np.exp(L - np.maximum.accumulate(L))).max())   # the same drawdown from log returns
A = 252
sharpe = np.sqrt(A) * r.mean() / r.std(ddof=1)
downside = np.sqrt(np.mean(np.minimum(r, 0.0) ** 2))
sortino = np.sqrt(A) * r.mean() / downside
win_rate = (r > 0).mean()                                     # zero is not a win; every period in the denominator
assert 0 <= max_dd < 1 and 0 <= win_rate <= 1
```

Sources: Sharpe (1994), "The Sharpe Ratio", Journal of Portfolio Management 21(1); Sortino and Price (1994), "Performance Measurement in a Downside Risk Framework", Journal of Investing 3(3); Magdon-Ismail and Atiya (2004), "Maximum Drawdown", Risk 17(10).
