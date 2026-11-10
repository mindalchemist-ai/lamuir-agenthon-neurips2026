# Mean-reverting (Ornstein-Uhlenbeck) log prices, with and without compound-Poisson jumps

## Three checks before fitting

Pair lags by position, not by label. NumPy functions keep the pandas type: np.log(series) and series / 100 are still Series with the original index, so X[:-1] and X[1:] keep their labels and X[1:] - (a + b * X[:-1]) subtracts each date from itself, giving near-zero residuals without an error. An index-alignment error from a regression call is the same problem; convert, do not route around it with another solver. Convert once with np.asarray(series, dtype=float) before any slicing and run the two asserts below in the same cell as the regression. If a later step shows that an input was still a Series, rerun every estimate computed from it.

    v = np.asarray(series, dtype=float); x_prev, x_next, dx = v[:-1], v[1:], np.diff(v)
    resid = x_next - (a + b * x_prev)
    assert len(resid) == len(v) - 1
    assert 0.3 < resid.std(ddof=1) / dx.std(ddof=1) <= 1 + 1e-9

Half-life carries the unit of kappa: ln 2 / kappa is in the time unit of dt; ln 2 / (kappa * dt) is in observation periods; periods times the period length in days gives days. A half-life far below one period with a clearly positive lag-1 autocorrelation means dt was left out.

Exact and Euler maps differ: kappa = -ln(b)/dt with sigma = s*sqrt(2*kappa/(1-b**2)), or kappa = -(b-1)/dt with sigma = s/sqrt(dt). Use the one the task writes; when it names neither, compute both and state which one you report.


**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Model and assumptions
- Price $S_{t} = \exp (X_{t})$ (geometric mean reversion, e.g. Schwartz 1997 one-factor commodity model). The log price follows
  $\mathrm{dX}_{t} = \kappa  (\theta  - X_{t}) \mathrm{d}t + \sigma  \mathrm{d}W_{t} + \mathrm{dJ}_{t}$, where $J_{t} = \sum _{i \le  N_{t}} Y_{i}$ is compound Poisson:
  $N_{t}$ Poisson with intensity $\lambda$, jump sizes $Y_{i}$ i.i.d. (often normal with mean $\mu _{J}$, sd $\sigma _{J}$), independent of W.
  Without jumps set $\lambda  = 0$. Parameters constant; $\kappa  > 0$.
- Here $\theta$ is the level that the diffusion part reverts to. With jumps the long-run mean of X is NOT $\theta$ (see below).
- Arithmetic OU on the price itself ($\mathrm{d}S = \kappa  (\theta  - S) \mathrm{d}t + \sigma  \mathrm{d}W$) uses the same formulas with X replaced by S.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $X_{t} = \ln  S_{t}$ | log price | none |
| $\kappa$ | mean-reversion speed | 1/year (if t in years) |
| $\theta$ | reversion level of the diffusion part, in LOG price units (level $e^{\theta}$ in price) | none |
| $\sigma$ | diffusion vol of X; 30% is `0.30` | $1/\sqrt{\mathrm{year}}$ |
| $\lambda$ | jump intensity (expected jumps per year) | $1/\mathrm{year}$ |
| $\mu _{J}, \sigma _{J}$ | mean and sd of a log jump size; $\operatorname{E}[Y^{2}] = \mu _{J}^{2} + \sigma _{J}^{2}$ | none |
| $\tau$, dt | forecast horizon; sampling interval in the SAME time unit as $\kappa$ (daily data in years: 1/252 or 1/365, per task) | years |

## Conditional moments over a horizon tau (exact, any tau)

$$
\begin{gathered}
a(\tau ) = e^{-\kappa  \tau},   g(\tau ) = (1 - e^{-2 \kappa  \tau}) / (2 \kappa ) \\
\operatorname{E}[X_{t+\tau} \vert  X_{t}]   = \theta  + (X_{t} - \theta ) a(\tau ) + (\lambda  \mu _{J} / \kappa ) (1 - a(\tau )) \\
\operatorname{Var}[X_{t+\tau} \vert  X_{t}] = (\sigma ^{2} + \lambda  (\mu _{J}^{2} + \sigma _{J}^{2})) g(\tau )
\end{gathered}
$$

The jump contribution to the variance uses the SAME factor $g(\tau)$ as the diffusion, with $\lambda  \operatorname{E}[Y^{2}]$ in place of $\sigma^{2}$.
Without jumps $X_{t+\tau}\mid X_t$ is normal; with jumps it is not normal (only mean and variance are as above).
Price moments without jumps: $\operatorname{E}[S_{t+\tau}] = \exp (m + v/2)$, $\operatorname{Var}[S_{t+\tau}] = \exp (2m + v)(e^{v} - 1)$ with m, v the mean and variance above.

## Stationary distribution (tau -> infinity)

$$
\operatorname{mean} = \theta  + \lambda  \mu _{J} / \kappa ,     \mathrm{variance} = (\sigma ^{2} + \lambda  (\mu _{J}^{2} + \sigma _{J}^{2})) / (2 \kappa )
$$

Half-life of a deviation from the long-run mean: $\ln  2 / \kappa$, in the time unit of $\kappa$ (years if $\kappa$ is per year;
multiply by 252 (or 365) for trading (or calendar) days). In observations: $\ln  2 / (-\ln  b)$ with b the AR(1) slope below.

Unit check before reporting a half-life: when κ comes from a regression on differences, $\kappa = -\beta/\Delta t$, then $\kappa\,\Delta t = -\beta$ is unit-free, so the half-life is $\ln 2/(\kappa\,\Delta t) = \ln 2/(-\beta)$ observation periods, and $\ln 2/\kappa$ is in the unit of $\Delta t$ (years when $\Delta t$ is in years), not in periods. Convert periods to days with the period length in days. A half-life in periods far below one for a slope of moderate size means the units were mixed.

## Exact discretization (simulation on a grid of step dt)

$$
X_{i+1} = \theta  + (X_{i} - \theta ) e^{-\kappa  \mathrm{d}t} + \sigma  \sqrt{g(\mathrm{d}t)} Z_{i} + \sum _{k=1}^{n_{i}} Y_{k} e^{-\kappa  (\mathrm{d}t - u_{k})}
$$

$Z_{i}$ standard normal, $n_i\sim\operatorname{Poisson}(\lambda\mathrm{d}t)$, $u_{k}$ i.i.d. uniform on (0, dt) (jump times inside the step). The diffusion
part is exact for any dt; Euler $X + \kappa  (\theta  - X) \mathrm{d}t + \sigma  \sqrt{\mathrm{d}t} Z$ is only accurate when $\kappa\mathrm{d}t$ is small.
Adding jumps undecayed at the step end ($+ \sum  Y_{k}$) is a common shortcut; it overstates the jump variance when $\kappa\mathrm{d}t$ is not small.

## AR(1) estimation from data sampled every dt
OLS regression $X_{i+1} = a + b X_{i} + \mathrm{eps}_{i}$ (or equivalently $X_{i+1} - X_{i} = a + (b - 1) X_{i} + \mathrm{eps}_{i}$), then

$$
\kappa  = -\ln (b) / \mathrm{d}t,     \theta  = a / (1 - b),     \sigma  = s_{\mathrm{eps}} \sqrt{2 \kappa  / (1 - b^{2})} = s_{\mathrm{eps}} \sqrt{-2 \ln  b / (\mathrm{d}t (1 - b^{2}))}
$$

With N observations $X_{1},\ldots ,X_{N}$ the regression uses the N - 1 adjacent pairs $(X_{i}, X_{i+1})$: the fit's sample size, residual count and degrees of freedom are based on N - 1, so a reported fit sample size is N - 1, while the series length stays N. Each sub-sample fit (split by date, regime or window) uses its own $N_s - 1$ adjacent pairs inside that sub-sample, and a fit-size field reported for it is that $N_s - 1$, the same quantity as the full-sample fit size, not the sub-sample's point count; a pair across the split boundary is not part of either fit unless the task says so. $s_{\mathrm{eps}}$ = residual standard deviation. Requires $0 < b < 1$(b >= 1: no mean reversion detected; $b \le  0$: model does not fit).
Small-sample approximation $\kappa  \approx (1 - b)/\mathrm{d}t$, $\sigma  \approx s_{\mathrm{eps}} / \sqrt{\mathrm{d}t}$ is only valid when $\kappa  \mathrm{d}t << 1$.
With jumps present but ignored, the same regression returns the stationary mean $\theta  + \lambda  \mu _{J}/\kappa$ as "$\theta$"
and $\sqrt{\sigma ^{2} + \lambda  \operatorname{E}[Y^{2}]}$ as "$\sigma$"; $\kappa$ stays consistent. Separating jumps needs extra steps (e.g. flag
returns beyond a threshold as jumps, then refit), which the task must specify.

Half-life: with $\kappa$ per unit of time (for example per year), the half-life is $\ln 2/\kappa$ in that unit; with observations every $\mathrm{d}t$ of that unit, it is $\ln 2/(\kappa\,\mathrm{d}t)$ observation periods. Report each in the unit its name states, and convert periods to days with the period length in days.
When an AR(1) or OU fit's diagnostics are reported, for the full sample and for each sub-period → build each fit's regression arrays and take its count from them (a sub-period of N observations also gives N − 1 pairs):

```text
x = np.asarray(x, dtype=float)
y, x_lag = x[1:] - x[:-1], x[:-1]        # N observations give N - 1 pairs
keep = np.isfinite(y) & np.isfinite(x_lag)   # plus any pairing rule the task states (same day, same regime)
y, x_lag = y[keep], x_lag[keep]
num_observations = len(y)                # the pairs actually regressed, not len(x); the same for every sub-period fit
```

The fit's R² compares the residual sum of squares with the total sum of squares of the regressand actually fitted: the differences Δx when Δx is regressed on $x_{t-1}$. The R² of the levels regression of $x_t$ on $x_{t-1}$ is a different, much larger number.

When many OU paths are simulated with the exact transition → carry one state per path and draw one normal per path at each step:

```python
x = np.full(n_paths, x0, dtype=float)
paths = np.empty((n_paths, n_steps))
for k in range(n_steps):
    x = theta + (x - theta) * np.exp(-kappa * dt) + sd_step * rng.standard_normal(n_paths)
    paths[:, k] = x
assert paths[:, -1].std() > 0          # a scalar state with one draw per step gives identical paths
```

## Risk-neutral forward / futures price
With constant rates futures = forward = $\operatorname{E}^{Q}[S_{T}]$, and all parameters below are risk-neutral ($\lambda$, $\mu _{J}$, $\sigma _{J}$ under Q).
A constant risk premium $\pi$ in the drift of X ($\pi  = \lambda _{\mathrm{mpr}} \sigma$ if the task gives a market price of risk per unit vol)
moves the level: drift $\kappa  (\theta  - X) - \pi  = \kappa  (\theta ^{*} - X)$ with $\theta ^{*} = \theta  - \pi  / \kappa$. Then

$$
\ln  F(t, T) = \theta ^{*} + (X_{t} - \theta ^{*}) e^{-\kappa  \tau} + (\sigma ^{2} / 2) g(\tau ) + \lambda  \int _{0}^{\tau} (M(e^{-\kappa  s}) - 1) \mathrm{d}s
$$

with $\tau  = T - t$ and $M(c) = \operatorname{E}[e^{c Y}] = \exp (\mu _{J} c + \sigma _{J}^{2} c^{2} / 2)$ for normal jumps (do the integral numerically).
Without jumps: $\ln  F = e^{-\kappa  \tau} \ln  S_{t} + (1 - e^{-\kappa  \tau}) \theta ^{*} + \sigma ^{2} (1 - e^{-2 \kappa  \tau}) / (4 \kappa )$.
F is not $\exp ( \operatorname{E}[X_{T}] )$: the variance term (and the jump term) must be included.

## Variants and how to tell which applies
- Parameterization of the drift: Schwartz writes $\mathrm{d}S = \kappa  (\mu  - \ln  S) S \mathrm{d}t + \sigma  S \mathrm{d}W$; then
  $\mathrm{dX} = \kappa  (\alpha  - X) \mathrm{d}t + \sigma  \mathrm{d}W$ with $\alpha  = \mu  - \sigma ^{2} / (2 \kappa )$. Do not use $\mu$ as the log-level.
- Level in price vs log units: if the task gives a long-run PRICE level P, the log level is `ln P` only if the task says so;
  `E[S]` in the stationary state is $\exp (\operatorname{mean} + \mathrm{variance}/2)$, not $e^{\theta}$.
- Deterministic seasonal mean (e.g. electricity): $X_{t} = f(t) + Y_{t}$ with Y the OU above; apply the formulas to Y.
- Jump-size laws other than normal: only `E[Y]`, $\operatorname{E}[Y^{2}]$ and $\operatorname{E}[e^{\mathrm{cY}}]$ change.
- Common mistakes: variance factor $(1 - e^{-\kappa  \tau})/\kappa$ or $\sigma ^{2} \tau$ instead of $(1 - e^{-2 \kappa  \tau})/(2 \kappa )$;
  dropping the jump mean from the conditional mean; regressing returns on returns; mixing dt in days with $\kappa$ per year;
  reporting half-life in observations when the task asks for days/years (or vice versa).

## Applicability and known limits
- AR(1) estimates of $\kappa$ are biased upward and noisy in short samples (our simulation check with ten years of daily
  data: median half-life estimate about 9% too short, sd of the $\kappa$ estimate about 28% of its value). Report what the task asks; do not "correct".
- Exact formulas assume constant parameters and Poisson jumps independent of the diffusion; spikes that revert faster
  than the diffusion need a second, faster-reverting factor (regime or two-factor models).

## Sources
Uhlenbeck & Ornstein (1930) Physical Review 36:823-841; Vasicek (1977) J. Financial Economics 5(2):177-188;
Schwartz (1997) J. Finance 52(3):923-973; Gillespie (1996) Physical Review E 54:2084-2091 (exact OU simulation);
Merton (1976) J. Financial Economics 3:125-144 (compound-Poisson jumps). Jump-OU moments derived here and checked by Monte Carlo.

## AR(1) slope outside (0, 1): mapping to OU and model comparison

This section applies when an OU process is estimated from an AR(1) regression x_t = a + b * x_(t-1) + e_t and mapped to mean reversion with kappa = -ln(b) / dt (or theta = -ln(b) per period), mu = a / (1 - b), half-life = ln 2 / kappa.

The mapping exists only for 0 < b < 1. A fitted b <= 0 describes an oscillating series and b >= 1 a non-stationary one; -ln(b) is then undefined or negative, and the stationary standard deviation sigma / sqrt(1 - b^2) does not exist. Two treatments are used; pick by the situation and state which:

| situation | treatment |
|---|---|
| OU is one candidate among several models compared by likelihood or AIC, and the task gives the OU mapping formulas | clip b into a small positive floor and a ceiling just below 1 (for example [1e-4, 0.999]) before mapping, and evaluate the OU likelihood with the clipped b; OU then fits badly on series that do not mean revert and loses the comparison on its own |
| the task asks whether the series mean-reverts, or reports OU parameters only when they exist | mark OU as not applicable for that window (no parameters, infinite information criterion) and report why |

Do not evaluate an "OU" likelihood with a negative b: that is an AR(1) with oscillation, not an OU process. When the likelihood includes the first observation under the stationary law, use the same (clipped) b there.

Reminder: map AR(1) to OU only with 0 < b < 1; outside that range clip b (model comparison) or mark OU not applicable, and say which.
