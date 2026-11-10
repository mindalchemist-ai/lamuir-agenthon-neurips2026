# Method: tail VaR and ES by extreme value theory (peaks over threshold)

When to use: the task instructions estimate tail VaR or ES from losses with a generalized Pareto fit above a threshold
(POT), a Hill tail index, or GARCH-filtered EVT.

When the task instructions point to a formula file, read the formula file first; it fixes the choices below. Where neither names a choice, use the library default and state it.

Losses `L = -r` (log returns `r`). Levels are confidence levels `level` (for example 0.99).

Choices that change the numbers, and how to pick each:

| Choice | Options | How to pick |
|---|---|---|
| Empirical quantile | `np.quantile(..., method=...)`: `"linear"` (numpy default, interpolates), `"lower"` / `"higher"` (an order statistic), `"nearest"`, Hyndman–Fan types | the method or order statistic the task or formula file names; they differ by one order statistic in small samples |
| Sample standard deviation | `ddof=1` (sample) or `ddof=0` (population) | "sample standard deviation" is `ddof=1`; numpy's `std` defaults to 0, pandas' to 1 |
| Historical ES | mean of losses `>= VaR`, mean of losses `> VaR`, or the Acerbi–Tasche weighted tail mean | the definition the task writes; they differ only when losses tie at the VaR |
| Normal VaR / ES | with the sample mean (`m + sd z`) or zero mean (`sd z`) | include the mean unless the task says zero mean or short-horizon |
| Hill estimator | k from a rule the task gives (`floor(sqrt(N))`, a fixed tail fraction, the POT exceedance count, a stable region of the Hill plot); threshold order statistic `L_(k+1)` or `L_(k)` | k and the threshold convention as the task writes them; xi changes with both |
| GARCH-EVT volatility | the last in-sample conditional volatility (a figure about the last observed day) or the one-step-ahead forecast (a figure for the next day) | the day the task's VaR refers to; see the arch conventions entry, section 2 |

```python
q = lambda x, a: np.quantile(x, a, method=QUANTILE_METHOD)          # QUANTILE_METHOD from the table above
def pot(x, uq):                                   # threshold u, GPD fit on excesses (location fixed at 0)
    u = q(x, uq); ex = x[x > u] - u
    xi, _, s = genpareto.fit(ex, floc=0)
    return u, xi, s, len(ex), len(x)
def pot_var_es(u, xi, s, nu, n, level):
    v = u + s / xi * ((n / nu * (1 - level)) ** (-xi) - 1)
    return v, v / (1 - xi) + (s - xi * u) / (1 - xi)
def hist(x, level):   v = q(x, level); return v, x[x >= v].mean()           # ES form per the table
def normal(x, level): m, sd = x.mean(), x.std(ddof=DDOF); z = norm.ppf(level); return m + sd * z, m + sd * norm.pdf(z) / (1 - level)
```

GARCH-EVT: fit GARCH (arch conventions entry, section 1); standardised losses `zl = -np.asarray(res.std_resid)`; POT on
`zl` with a threshold quantile chosen for `zl`; VaR and ES are the chosen volatility (table above) times the standardised values.

Hill tail index: sort losses in descending order, take k and the threshold order statistic as chosen above, `xi_hill = mean(log(L_(1..k))) - log(L_threshold)`.

Checks before writing:
- Every GPD fit uses excesses `x[x > u] - u`, never the exceedances themselves.
- In `pot_var_es` the ratio is `n / nu` (all observations over exceedances, greater than 1); `nu / n` inflates VaR
  several-fold.
- A full-sample POT VaR far from the historical VaR at the same level points first to the `n / nu` ratio and to excesses versus exceedances.
- The standardised GARCH-EVT VaR at 99% is usually between 2 and 4 (the standard normal value is 2.33).
- Print the choices made (quantile method, ddof, ES form, Hill k and threshold, GARCH-EVT volatility) with the words of the task or formula file that fixed each.
- Result keys that drop the leading "0." of a level are built from the text of the number, `str(level)[2:]`
  (0.99 -> "99", 0.995 -> "995"), not from `int(level * 1000)`.
- Method names inside result keys are written in full, exactly as the output section of the task instructions lists the method names.

Rolling backtests and coverage tests: the VaR backtest entry.
