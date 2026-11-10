# arch 8.0.0: conventions and calls, as code

How to use this entry:
- Use a line here only where the task instructions give no formula for that quantity; a formula in the task
  instructions replaces the line here.
- `r`: daily decimal returns (Series).
- `res`: an arch fit on `100 * r`.
- `B`: periods per year for annualizing, a task parameter (252 trading days is common; 260 and 365 also occur).
- The official description of each function is attached separately.

## 1. Fit a GARCH(1,1)

There are two cases, set by whether the task instructions fix the fitting units.

### Case 1 (default): the task instructions do not fix the fitting units

Fit percentage returns, `100 * r`, for numerical stability; then divide every output back to the units of `r`.

```python
res = arch_model(100 * r, vol="GARCH", p=1, o=0, q=1, mean="Zero", dist="normal", rescale=False).fit(disp="off")
omega = res.params["omega"] / 100**2                        # every variance and omega: / 100**2 (decimal units)
alpha, beta = res.params["alpha[1]"], res.params["beta[1]"] # unchanged by the scaling
cond_vol = res.conditional_volatility / 100                 # every volatility and mean: / 100
assert omega < 1e-3 and float(cond_vol.mean()) < 0.1, "still in percent units"
```

### Case 2: the task instructions fix the fitting units

For example "fit the raw returns, do not rescale": fit `r` as stated. Every output is already in the units of `r`;
no conversion.

```python
res = arch_model(r, vol="GARCH", p=1, o=0, q=1, mean="Zero", dist="normal", rescale=False).fit(disp="off")
omega = res.params["omega"]
alpha, beta = res.params["alpha[1]"], res.params["beta[1]"]
cond_vol = res.conditional_volatility
```

### Check either fit: did the optimizer move?

A fit can report `convergence_flag == 0` and still return the starting values unchanged; a case 2 fit on raw decimal
returns often does.

```python
start = res.model.volatility.starting_values(np.asarray(res.resid))   # where the optimizer began
assert not np.allclose(res.params.values[-len(start):], start), "fit did not move from the starting values"
```

Sections 2 and 3 write the case 1 conversions (`/ 100`, `/ 100**2`); in case 2 leave out the `/ 100` and `/ 100**2` conversions.

## 2. Pick the volatility the task instructions mean

There are two use cases. Match the task instructions to use case 1 or use case 2, then use the call listed under the matching use case.

### Use case 1: the volatility of a day inside the sample: `res.conditional_volatility`

Task instructions that ask for the "conditional volatility" of an in-sample day, or of the final in-sample day.
The value on day t is the volatility of day t's return, forecast on day t-1, so the value on day t does not use day t's return.

```python
sigma_for_t = res.conditional_volatility / 100              # day t: volatility of r[t], forecast on day t-1
sigma_last_fit = res.conditional_volatility.iloc[-1] / 100  # the final in-sample day
```

### Use case 2: a volatility forecast from a chosen day forward: `res.forecast(...)`

Task instructions that ask for a one-step-ahead forecast, the volatility of the next day, a volatility known at a
day's close, or a variance over the next H days. A forecast made on an origin day uses every return up to and
including that day.

```python
sigma_next = np.sqrt(res.forecast(horizon=1).variance.iloc[-1, 0]) / 100   # first day after the sample
sigma_close = np.sqrt(res.forecast(horizon=1, start=0, align="origin").variance["h.1"]) / 100   # day t: known once day t has closed
var_h_days = res.forecast(horizon=H).variance.iloc[-1].sum() / 100**2      # variance of the next H days, from the last day
```

Notes:
- `sigma_close` on day t equals `sigma_for_t` on day t+1: the same number, labeled one day apart.
- When the task instructions mention both the final observation and a one-step-ahead forecast, the words
  "one-step-ahead forecast" decide: use case 2, `sigma_next`.
- A rolling estimate refits on each window `r.iloc[end - W:end]` for `end in range(W, len(r) + 1)` and uses the
  `sigma_next` of each window's fit.

## 3. Long-run variance and annualized values

Turns the daily parameters and volatilities into the long-run and annual figures that task instructions usually ask for.

```python
assert alpha + beta < 1
long_run_var = omega / (1 - alpha - beta)                   # decimal daily variance
long_run_vol_ann = np.sqrt(B * long_run_var)                # an "unconditional / long-run volatility, annualized"
vol_ann = vol_daily * np.sqrt(B); var_ann = var_daily * B; mean_ann = mean_daily_log_return * B
assert 0.03 < long_run_vol_ann < 1.5 and 0.03 < float(np.nanmean(vol_ann)) < 1.5
```
- "Annualized" applies to every quantity labeled annualized: composite, portfolio and long-run volatilities alike.

## 4. Standardised residuals

The unit-free shocks used by EVT on GARCH residuals, filtered simulation and correlation models.

```python
z = res.std_resid                                           # residual / conditional volatility of the same day; the percent scaling cancels
assert abs(float(z.std()) - 1) < 0.2
```

## 5. VaR and ES as positive losses

Parametric normal VaR and ES at a tail probability, reported as positive numbers.

```python
tail = 1 - level                                            # tail probability; "1% VaR" and "99% VaR" both mean tail = 0.01
z_q = norm.ppf(tail)                                        # -2.326
var_t = -(mu + sigma * z_q)                                 # mu: the conditional mean, or 0 for a zero-mean VaR (common at short horizons); use the task's choice and state it
es_t = -mu + sigma * norm.pdf(z_q) / tail                   # divide by the tail probability, not by the confidence level
assert es_t > var_t > 0
```
- If the task instructions define their own ES or VaR formula, that formula replaces the `var_t` and `es_t` lines; otherwise these are the standard normal VaR and ES.

## 6. Warm-up of indicator signals

Rows where an indicator does not exist yet must carry no position.

```python
valid = fast.notna() & slow.notna()                         # np.where on NaN would return the else value (a full short)
signal = pd.DataFrame(np.where(fast > slow, 1.0, -1.0), index=fast.index, columns=fast.columns).where(valid)
```

## 7. Two consistency rules

- Every later step uses the return series the task instructions defined first (log or simple); do not rebuild returns from prices with
  the other definition, backtests included.
- `StationaryBootstrap` draws random numbers in the internal order of `StationaryBootstrap`; when the task instructions prescribe the random
  draws, write the prescribed draws directly instead of using `StationaryBootstrap`.

Sources: Bollerslev (1986) and Engle (2001) for GARCH variance; McNeil, Frey and Embrechts, Quantitative Risk
Management (VaR, ES, standardised residuals); arch 8.0.0 API reference.
