# Estimator variants: ddof, recursion seeds, rounding to whole units, Student-t scale

Use this when a task computes standard deviations or z-scores, runs an exponential average or a variance recursion, sizes positions in whole units, or uses a Student-t distribution. A choice the task states always wins.

## Decisions

| Decision | Options | How the task text selects | When the text is silent |
|---|---|---|---|
| Divisor of a standard deviation | ddof=1 (sample, unbiased variance) or ddof=0 (population, maximum likelihood) | "sample", "unbiased", "ddof=1", or an inference statistic (t-statistic, standard error) mean ddof=1; "population", "ddof=0", or a normal maximum-likelihood fit mean ddof=0. | Defaults differ by library: pandas Series.std / DataFrame.std / cov use ddof=1, numpy std / var and scipy.stats.zscore use ddof=0, sklearn StandardScaler uses ddof=0. Pick one deliberately, pass ddof explicitly, and use the same value for every series the task treats alike. |
| Start of an exponential average (EMA) | first observation, `ewm(span, adjust=False)`; the simple mean of the first span values, starting at position span - 1; the weighted average with `adjust=True` | "seeded with the simple moving average" or "SMA seed" means the second; "recursive" or a formula with the previous value means the first; "pandas ewm" with defaults means the third. | The first-observation recursion, stated, with the warm-up values kept or dropped as the text says. |
| Start of a variance recursion (EWMA, GARCH) | sample variance of the whole series or of a first block; first squared return; backcast; zero | The text names it; a fitted GARCH from a library uses that library's backcast. | Sample variance of the estimation series, stated; the effect fades with the decay factor. |
| Start of a running quantity | a stated date's value (a signal day, an entry day), initial capital, or the first observation | The text says where a running peak, running total or high-water mark starts. | The first observation of the series the quantity is defined on. |
| Whole units | floor, round, or keep fractional | Buying with a cash budget uses floor (never exceed the budget); a count of names floor(q * n) differs from round(q * n); "round" means round. | Floor for shares or contracts bought with cash, then recompute the cash left; fractional only when the text allows fractional holdings. |
| Student-t scale | scipy `t(df, loc, scale)` has standard deviation scale * sqrt(df / (df - 2)); a standardized (unit-variance) t uses scale = sd * sqrt((df - 2) / df) | When the text gives a volatility for t innovations, decide whether it is the scale or the standard deviation; "standardized t" means unit variance. | Treat a stated volatility as the standard deviation and convert to scale, stated. |

## Check

```python
import numpy as np, pandas as pd
from scipy import stats

x = pd.Series([0.01, -0.02, 0.015, 0.003, -0.007])
assert np.isclose(x.std(), np.std(x.values, ddof=1)) and not np.isclose(x.std(), np.std(x.values))
assert np.allclose(stats.zscore(x.values), (x - x.mean()) / x.std(ddof=0))

k = 3
span = k
p = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
alpha = 2 / (span + 1)
rec = p.ewm(span=k, adjust=False).mean()                          # starts at the first observation
sma_seed = [np.nan] * (span - 1) + [p.iloc[:span].mean()]
for v in p.iloc[span:]:
    sma_seed.append(alpha * v + (1 - alpha) * sma_seed[-1])
assert rec.iloc[0] == 10.0 and np.isnan(sma_seed[0]) and sma_seed[span - 1] == 11.0

cash, price, fee = 10_000.0, 123.45, 1.0
shares = int(np.floor((cash - fee) / price))
assert shares * price + fee <= cash < (shares + 1) * price + fee

df, sd = 5.0, 0.02
scale = sd * np.sqrt((df - 2) / df)
assert np.isclose(stats.t(df, scale=scale).std(), sd)
```
