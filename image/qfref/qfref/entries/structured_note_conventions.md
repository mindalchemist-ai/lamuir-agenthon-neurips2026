# Principal-protected note on a down-and-out call: conventions and formulas

When to use: a task values a note that repays principal at maturity and adds participation in a down-and-out call, then reports Greeks, delta-based VaR / ES or the issuer's premium.

Several quantities in such a report have more than one accepted definition. The table lists each choice point with its readings. Take the reading the task's text defines; when the text does not define it, pick one, and write the choice and the reason in a code comment next to the line that uses it.

## 1. Choice points

| Choice point | Readings | Situation -> what to do |
|---|---|---|
| Expected shortfall formula | textbook normal ES: `es = sd * pdf(z) / (1 - c)`, with `sd` the P&L standard deviation and `z = norm.ppf(c)` (McNeil, Frey and Embrechts; equivalently `var * pdf(z) / (z * (1 - c))` when `var = z * sd`) | the task writes an ES formula -> use it exactly; otherwise use this form and check `es / var = pdf(z) / (z * (1 - c))`, about 1.15 at 99% |
| GARCH mean equation | zero mean (`mean="Zero"`), constant mean (`mean="Constant"`, the `arch` default), or another mean model | the task names the mean -> use it; returns were demeaned in the task, or it says zero mean -> zero; nothing said -> pick one and comment; the fitted omega, alpha, beta move slightly between the two |
| Return scaling for the fit | fit on returns times 100 (percent) and divide omega by 100**2 afterwards, or fit on raw decimals | the task fixes the fitting units -> use them; otherwise fit percent returns. On raw daily decimals the optimizer can stop at its starting values and still report `convergence_flag == 0`; check that alpha and beta moved, for example by refitting on percent returns and comparing after the conversion |
| Variance and volatility units | daily variance (decimal squared), annualized variance (daily times periods per year), daily or annualized volatility | the task's field name or text says which -> use it; a volatility that is the pricing input, or that is reported beside a breakeven or implied volatility, is reported in the pricing units (annualized when maturity is in years), the same number that enters the option formula; per-period figures such as `omega / (1 - alpha - beta)` stay per period unless labeled annualized |
| Volatility used for pricing | (a) final in-sample value of `conditional_volatility` (the variance for the last observed day, built from information up to the day before); (b) one-step-ahead forecast `res.forecast(horizon=1).variance` (includes the last return); (c) the long-run volatility `sqrt(omega / (1 - alpha - beta))`; (d) a given implied volatility | the task names one -> use it; annualize a daily figure by `sqrt(periods_per_year)` (252 for daily trading data) and say so |
| Issue price | stated offer price, or par (`issue_price = N`) | a stated price -> use it; none -> par, commented |
| Premium / markup denominator | over fair value: `(issue - fair) / fair`; over issue price: `(issue - fair) / issue`; investor view `fair - issue` | the wording decides: "over fair value", "relative to theoretical value" -> fair; "margin on the issue price", "as a share of what the investor pays" -> issue; state the sign convention |
| Number of options | `N * p / S0` (participation in the percentage return of the underlying), `N * p / K`, or a stated count | follow the payoff the task writes: `p * N * max(S_T / S0 - 1, 0)` gives `N * p / S0` |
| Delta bump | relative (`dS = h * S0`) or absolute (`dS` in price units); central `(f(S+dS) - f(S-dS)) / (2 dS)` or one-sided; or the analytic delta | the task gives the bump -> use it; none -> central difference with a small relative bump, and confirm the delta does not change when the bump is halved |
| Exposure inside VaR | (a) equity delta only: `note_delta * S0 * sigma_daily`; (b) whole note: equity delta plus the bond's rate exposure (PV01 times a rate volatility); (c) full revaluation of bond and option | the task names the risk factors -> include those; it names only the underlying's returns -> (a), and comment that the bond's rate risk is left out |
| Volatility inside VaR | the annual pricing volatility divided by `sqrt(periods_per_year)`, or a daily estimate such as the GARCH one-step forecast | the volatility the task names for risk; it may differ from the pricing one |
| Horizon and confidence | one day, ten days (square root of time), or the stated horizon; the stated confidence level `c` | always from the task; no default |

## 2. Formulas

Bond leg, rate `rate` with continuous compounding, `T` years:

```python
bond_pv = N * np.exp(-rate * T)        # annually compounded quote instead: N / (1 + rate)**T
```

Down-and-out call, barrier `B` at or below strike `K`, continuous monitoring, no rebate, no dividends: vanilla call minus down-and-in call (Reiner and Rubinstein, Risk 4(8), 1991; Hull, Options, Futures, and Other Derivatives, barrier options section of the exotic options chapter). With a dividend yield `q`, use `rate - q` in `lam` and in `d1`, and multiply each spot term by `exp(-q T)`. A barrier above the strike, a rebate, or discrete monitoring needs other formulas (Broadie, Glasserman and Kou shift a down barrier by `exp(-0.5826 * sig * sqrt(dt))` for discrete monitoring).

```python
def doc(S, sig):
    if S <= B: return 0.0
    st = sig * np.sqrt(T); d1 = (np.log(S / K) + (rate + sig**2 / 2) * T) / st; d2 = d1 - st
    call = S * norm.cdf(d1) - K * np.exp(-rate * T) * norm.cdf(d2)
    lam = (rate + sig**2 / 2) / sig**2; y = np.log(B**2 / (S * K)) / st + lam * st
    cdi = S * (B / S)**(2 * lam) * norm.cdf(y) - K * np.exp(-rate * T) * (B / S)**(2 * lam - 2) * norm.cdf(y - st)
    return max(call - cdi, 0.0)
```

Sanity checks: `0 <= doc(S, sig) <= vanilla call`; `doc(B, sig) == 0`; `doc + down-and-in == vanilla`; `sig` is annual.

Note value and premium:

```python
n_options = N * p / S0                              # see the table for other readings
fair = bond_pv + n_options * doc(S0, sigma_ann)
premium = (issue_price - fair) / fair               # or / issue_price, per the table
```

Implied (breakeven) volatility: the `s` with `bond_pv + n_options * doc(S0, s) == issue_price`. A down-and-out call is not always increasing in volatility (a higher volatility also raises the knock-out probability, so vega can turn negative when the barrier is near spot), so there may be no root or two roots. Scan a grid first and bracket only where the sign changes; `brentq` raises `ValueError` when the two ends have the same sign.

```python
f = lambda s: bond_pv + n_options * doc(S0, s) - issue_price
grid = np.linspace(0.01, 2.0, 400); fv = np.array([f(s) for s in grid])
idx = np.where(np.sign(fv[:-1]) != np.sign(fv[1:]))[0]
roots = [brentq(f, grid[i], grid[i + 1]) for i in idx]   # empty: no volatility reprices the note; report that
```

Delta and delta-normal risk for one period:

```python
dS = h * S0                                          # bump per the table
option_delta = (doc(S0 + dS, sigma_ann) - doc(S0 - dS, sigma_ann)) / (2 * dS)
note_delta = n_options * option_delta
z = norm.ppf(c)                                      # c: confidence level from the task
sd = abs(note_delta) * S0 * sigma_period             # P&L standard deviation for the horizon
var = z * sd
es = sd * norm.pdf(z) / (1 - c)                      # textbook normal ES
assert abs(es / var - norm.pdf(z) / (z * (1 - c))) < 1e-12
```

GARCH fit with the `arch` package and the two volatility readings:

```python
res = arch_model(100 * r, vol="GARCH", mean=mean_spec, rescale=False).fit(disp="off")
omega = res.params["omega"] / 100**2; alpha = res.params["alpha[1]"]; beta = res.params["beta[1]"]
persistence = alpha + beta; long_run_var = omega / (1 - persistence)          # per period
sig_last = np.asarray(res.conditional_volatility)[-1] / 100                    # reading (a), daily
sigma_ann = sig_last * np.sqrt(periods_per_year)                              # the pricing input; report a pricing volatility in these units
sig_next = np.sqrt(res.forecast(horizon=1).variance.values[-1, 0]) / 100       # reading (b)
```
