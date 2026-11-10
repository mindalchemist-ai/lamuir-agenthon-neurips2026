# Calibrating mean-reverting processes: lag pairs, parameter maps, half-life units, simulation

Use this note when a task fits an Ornstein-Uhlenbeck (OU) process, with or without jumps, to a time series and then simulates it. Each block gives a short skeleton and asserts that catch the common silent errors. When the task fixes a formula, implement that formula; the asserts still apply.

## 1. Build lag pairs as plain arrays

A regression of x[t+1] on x[t] needs the two shifted copies paired by position. Pandas arithmetic pairs values by index label, so subtracting two slices of one Series lines up the same dates and gives residuals near zero without any error. Convert to NumPy first.

```text
v = np.asarray(series, dtype=float)          # series.to_numpy(float) for a pandas Series
v = v[np.isfinite(v)]
x_prev, x_next, dx = v[:-1], v[1:], np.diff(v)
fit = sm.OLS(x_next, sm.add_constant(x_prev)).fit()
a, b = fit.params
resid = x_next - (a + b * x_prev)
assert len(resid) == len(v) - 1 and np.allclose(resid, fit.resid)
assert 0.3 < resid.std(ddof=1) / dx.std(ddof=1) <= 1 + 1e-9   # far below 0.3: pairs were misaligned
```

## 2. Two maps from regression coefficients to (kappa, theta, sigma)

The same data give either a levels slope b or a differences slope beta = b - 1, with the same intercept a. The exact map inverts the OU transition; the Euler (plug-in) map treats the step as small. They agree when kappa*dt is small and differ otherwise.

```text
s = resid.std(ddof=1)
kappa_exact = -np.log(b) / dt
theta_exact = a / (1 - b)
sigma_exact = s * np.sqrt(2 * kappa_exact / (1 - b**2))    # 1 - b**2 = 1 - exp(-2*kappa*dt)
beta = b - 1
kappa_euler, mu_euler, sigma_euler = -beta / dt, -a / beta, s / np.sqrt(dt)
assert 0 < b < 1 and np.isclose(theta_exact, mu_euler)
```

If a task says "sigma from the residual variance" without a formula, the two readings are sigma_exact (residual variance equals the exact transition variance) and sigma_euler (residual variance equals sigma**2 * dt). The residual degrees of freedom (ddof=1 on residuals, or n - 2 as in fit.mse_resid) is a separate choice the task may fix.

## 3. Half-life in the unit its name states

kappa carries the time unit of dt. ln 2 / kappa is in that unit (years if dt is in years). In observation periods it is ln 2 / (kappa * dt); in days multiply periods by the period length in days (1/3 for 8-hour periods).

```text
hl_time = np.log(2) / kappa
hl_periods = np.log(2) / (kappa * dt)
hl_days = hl_periods * period_length_days
rho1 = np.corrcoef(v[:-1], v[1:])[0, 1]
assert abs(np.log(hl_periods) - np.log(np.log(2) / -np.log(rho1))) < 1.0
```

A half-life far below one period while the lag-1 autocorrelation is clearly positive means kappa (per year) was divided into ln 2 without dt. The stationary standard deviation is sigma / sqrt(2 * kappa); with jumps add lambda * (mu_J**2 + sigma_J**2) to sigma**2.

## 4. Simulation

The exact transition draws one normal per path per step; Euler adds drift, diffusion and the step's jumps. Jumps per step are Poisson(lambda * dt); the sum of n normal sizes is normal with mean n * mu_J and sd sqrt(n) * sigma_J.

```text
sd_step = np.sqrt(sigma**2 * (1 - np.exp(-2 * kappa * dt)) / (2 * kappa))
x = np.full(n_paths, x0, dtype=float)
for k in range(n_steps):
    x = theta + (x - theta) * np.exp(-kappa * dt) + sd_step * rng.standard_normal(n_paths)
assert x.std() > 0
```

## 5. Comparing analytical and simulated moments

Put the analytical and simulated values for each horizon in one table with named columns, write it, and compute every
summary error from those columns in the cell that writes the summary. Pairing parallel lists with zip() depends on
argument order, and one swapped list divides a mean gap by a variance without any error. A summary value set in an
earlier cell and later recomputed differently in a diagnostic must be replaced before it is written.

```python
mom = pd.DataFrame({"tau": taus, "mean_an": e_an, "var_an": v_an, "mean_mc": e_mc, "var_mc": v_mc})
mom.to_csv(path, index=False)
back = pd.read_csv(path)                                              # summarise what was written, by column name
mean_err = ((back["mean_an"] - back["mean_mc"]).abs() / back["mean_an"].abs()).max()
var_err = ((back["var_an"] - back["var_mc"]).abs() / back["var_an"]).max()
summary = {"mean_err": float(mean_err), "var_err": float(var_err)}  # built in the cell that writes the summary
assert summary["var_err"] == float(((back["var_an"] - back["var_mc"]).abs() / back["var_an"]).max())
```

## Task wording -> API arguments

Seeding: "np.random.seed(s)" sets the legacy global generator used by np.random.normal/poisson; "default_rng(s)" creates a separate Generator. They give different streams, and the order of draws inside the loop (normals before or after Poisson counts) changes every path.

statsmodels adfuller: regression "c" constant, "ct" constant and trend, "n" none; autolag "AIC"/"BIC" searches lags up to maxlag, autolag=None uses exactly maxlag. Wording "with drift/intercept" maps to "c".

Moments: np.std defaults to ddof=0, pandas .std() to ddof=1. scipy.stats.skew and kurtosis default to bias=True; "unbiased" means bias=False, which equals pandas .skew()/.kurt(). kurtosis fisher=True is excess kurtosis.

Autocorrelation: Series.autocorr(k) is the Pearson correlation of the overlapping pairs; statsmodels acf uses the full-sample mean and variance. Both are "lag-k autocorrelation"; they differ in short or trending samples.

np.percentile default method "linear" interpolates; "lower"/"higher"/"nearest" pick order statistics.

pd.to_datetime(ms, unit="ms", utc=True) then .dt.floor("s") truncates sub-second jitter; round("s") rounds it.

## Sources

Uhlenbeck and Ornstein (1930), Phys. Rev. 36, 823. Vasicek (1977), J. Financial Economics 5, 177, sec. 2. Gillespie (1996), Phys. Rev. E 54, 2084 (exact OU update). Glasserman, Monte Carlo Methods in Financial Engineering (2004), sec. 3.3 (OU) and 3.5 (jump processes). Tsay, Analysis of Financial Time Series, 3rd ed., ch. 2 (AR(1), ACF, unit-root tests). Docs: statsmodels 0.15 adfuller and acf; SciPy 1.18 stats.skew/kurtosis; NumPy 2.5 random (legacy seeding vs Generator) and percentile.
