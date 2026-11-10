# Method: trend-following signals with volatility-targeted sizing, decided at each day's close

When to use: the task instructions build moving-average crossover signals, size positions to a volatility target (EWMA
or GARCH volatility, optionally scaled by a volatility regime) and trade the next day.

## 1. Dates and signals

```python
if "date" in prices.columns:                      # every table on the trading dates, never a 0..n-1 index
    prices = prices.set_index(pd.to_datetime(prices.pop("date")))
assert isinstance(prices.index, pd.DatetimeIndex)
def sma_seeded_ema(s, span):                      # one of three initializations, see the table below
    seeded = s.astype(float).copy()
    seeded.iloc[:span - 1] = np.nan
    seeded.iloc[span - 1] = s.iloc[:span].mean()
    return seeded.ewm(adjust=False, span=span).mean()
ema = {"sma_seed": sma_seeded_ema,
       "first_price": lambda s, span: s.astype(float).ewm(adjust=False, span=span).mean(),
       "weighted": lambda s, span: s.astype(float).ewm(adjust=True, span=span).mean()}[EMA_INIT]
fast = prices[cols].apply(ema, span=fast_span)
slow = prices[cols].apply(ema, span=slow_span)
```

| EMA initialization | What it does | Task wording that selects it |
|---|---|---|
| `sma_seed` | first value = average of the opening `span` prices, recursion from there | "seeded with / started from the simple moving average" |
| `first_price` | recursion from the first price (`adjust=False`) | "recursive EMA from the first observation", or a stated recursion with no seed |
| `weighted` | pandas `adjust=True`, normalized weights over all past prices | "exponentially weighted average" written as a weighted sum, or pandas defaults |

The three differ mainly in the opening rows; after a few spans they converge.

- Crossover signals compare moving averages of price levels (or of the series the task names); moving averages of returns hover around zero and their crossings carry no trend information. Returns feed the volatility estimate, prices feed the signal:

```python
assert (fast.dropna() > 0).all().all() and fast.dropna().mean().mean() > 10 * returns.abs().mean().mean()   # EMAs are on prices, not returns
```

- Compute each EMA on the full price history; mask the warm-up rows (arch conventions entry, section 6).
- Put every day-t input on the return row of the same date by label (`signal.loc[returns.index]`); do not cut a
  price-dated table by position and relabel the rows; relabeling by position moves every row by one day.

## 2. Volatility for day t's sizing

- EWMA: annualize before dividing an annual target, `ewma_vol = np.sqrt(periods_per_year * ewma_var)`, with the periods per year the task uses (252 trading days is common; 365 for markets that trade every day).
- GARCH: a strategy decided at day t's close sizes with the volatility known once day t has closed, `sigma_close` (arch
  conventions entry, section 2, use case 2), one series per asset. Where the task instructions write the day-t GARCH
  volatility as `sigma[t]` or `conditional_volatility[t]` next to day-t signals, read the day-t GARCH volatility as `sigma_close`.

```python
sigma_close, long_run_var = {}, {}
for col in cols:                                  # one fit per asset on that asset's daily decimal returns
    r_i = returns[col].dropna()
    res = arch_model(100 * r_i, vol="GARCH", p=1, o=0, q=1, mean="Zero", dist="normal", rescale=False).fit(disp="off")
    sigma_close[col] = np.sqrt(res.forecast(horizon=1, start=0, align="origin").variance["h.1"]) / 100   # row t: known at day t's close
    omega, alpha, beta = res.params["omega"] / 100**2, res.params["alpha[1]"], res.params["beta[1]"]   # omega: / 100**2
    long_run_var[col] = omega / (1 - alpha - beta)                                                     # decimal daily variance
sigma_close = pd.DataFrame(sigma_close).reindex(returns.index)   # not res.conditional_volatility, which is one day earlier
avg_long_run_var = float(np.mean(list(long_run_var.values())))
assert avg_long_run_var < 1e-2, "long-run variance still in percent units"
```
- A composite across assets is built from the per-asset `sigma_close` series in the units the task instructions define; when the
  composite is annualized, the percentile thresholds and regime labels of the composite use the annualized composite.
- One long-run figure across assets has three readings: the arithmetic mean of the per-asset long-run variances, the square of the mean long-run volatility, or a weighted mean. Use the one the task describes; the code above computes the first.

## 3. Weights and returns

- Day t's weight uses day t's signal and volatility; the whole weight row is lagged once: `port = (weights.shift(1) * r).sum(axis=1)`,
  with no position (zero return) before the first weight.
