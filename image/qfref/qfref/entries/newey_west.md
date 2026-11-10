# Newey-West (1987) HAC standard errors (OLS and sample mean) and the Gibbons-Ross-Shanken (1989) test

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Setting and assumptions
- Linear regression $y_{t} = x_{t}' b + u_{t}$, $t = 1\ldots T, k$ regressors (constant included in k). The errors may be heteroskedastic and
  serially correlated; correlation is assumed to die out with the lag. OLS point estimates are unchanged; only the covariance changes.
- A sample mean is the special case $x_{t} = 1$ ($k = 1$): use it for the mean of a return series, of Fama-MacBeth slopes, of a strategy P&L.
- Time order matters: rows must be sorted by time with no gaps; HAC is not for a pure cross-section.

## Parameters and units
| symbol | meaning |
|---|---|
| $T, k$ | number of time observations; number of regressors including the constant |
| $L$ | maximum lag ("maxlags", "truncation lag"); integer >= 0; L = 0 means White (no autocorrelation) |
| $w_{l}$ | Bartlett weight of lag l |
| $\hat{u}_{t}$ | OLS residual; for a mean, $y_{t} - \bar{y}$ |
The covariance is in squared units of the coefficient per the data frequency; do not annualize unless the task says so.

## Formulas (OLS)

$$
\hat{b} = (X'X)^{-1} X'y
$$

The score vector has $k$ components:

$$
g_{t} = x_{t} \cdot  \hat{u}_{t}
$$

A $k$ by $k$ SUM, not divided by $T - l$:

$$
\Gamma _{l} = \sum _{t=l+1}^{T} g_{t} g_{t-l}'
$$

$$
w_{l} = 1 - l / (L + 1)
$$

For $l = 0\ldots L$.

$$
S = \Gamma _{0} + \sum _{l=1}^{L} w_{l} (\Gamma _{l} + \Gamma _{l}')
$$

Sandwich covariance:

$$
V_{\mathrm{NW}} = (X'X)^{-1} S (X'X)^{-1}
$$

$$
\mathrm{se}_{j} = \sqrt{V_{\mathrm{NW}}[j,j]}
$$

$$
t_{j} = (\hat{b}_{j} - \mathrm{b0}_{j}) / \mathrm{se}_{j}
$$

With the small-sample scaling, $V_{\mathrm{NW},\mathrm{adj}} = T/(T-k) \cdot  V_{\mathrm{NW}}$ (Stata `newey` applies this factor; see below for statsmodels).

## Formulas (sample mean)
Divisor $T$ for every $l$:

$$
\gamma _{l} = (1/T) \sum _{t=l+1}^{T} (y_{t} - \bar{y})(y_{t-l} - \bar{y})
$$

Long-run variance:

$$
\Omega  = \gamma _{0} + 2 \sum _{l=1}^{L} (1 - l/(L+1)) \gamma _{l}
$$

$$
\mathrm{se}(\bar{y}) = \sqrt{\Omega  / T}
$$

Optionally multiply by $\sqrt{T/(T-1)}$.

$$
t = (\bar{y} - \mathrm{mu0}) / \mathrm{se}(\bar{y})
$$

Note $\gamma _{0}$ uses divisor T, so with $L = 0$ this is $\operatorname{sd}_{\mathrm{pop}} / \sqrt{T}$, not the usual `sd(ddof=1) / sqrt(T)`.

## Choosing L
- If the task gives L, use it. For overlapping h-period returns ($h > 1$ periods summed each observation) use at least $L = h - 1$.
- Rule of thumb: $L = \operatorname{floor}(4 (T/100)^{2/9})$ (statsmodels' default when no lag is given to $\mathrm{cov}_{\mathrm{hac}}$).
- Newey-West (1994) automatic lag (Bartlett): with a scalar series $v_{t}$ (the demeaned series for a mean) and
  $n = 4 (T/100)^{2/9}$ rounded to an integer (implementations differ: floor or ceil),
  $\sigma _{j} = (1/T) \sum _{t=j+1}^{T} v_{t} v_{t-j}$, $\mathrm{s0} = \sigma _{0} + 2 \sum _{j=1}^{n} \sigma _{j}$, $\mathrm{s1} = 2 \sum _{j=1}^{n} j \sigma _{j}$,
  $\gamma  = 1.1447 (\mathrm{s1}/\mathrm{s0})^{2/3}$, bandwidth $m = \gamma  T^{1/3}$, then $L = \operatorname{floor}(m)$(R sandwich) or ceil(m) (arch); weights 1 - l/(L+1).
  For a vector $g_{t}$ the series is a weighted sum of its components; the weighting is implementation-specific.

## statsmodels mapping (checked on statsmodels 0.15)
- `sm.OLS(y, X).fit(cov_type='HAC', cov_kwds={'maxlags': L})` = $V_{\mathrm{NW}}$ above with Bartlett weights, **no** T/(T-k) factor
  (`use_correction` defaults to False in `fit`), p-values from the **normal** distribution (`use_t=False` by default).
- `cov_kwds={'maxlags': L, 'use_correction': True}` multiplies by T/(T-k). `kernel='uniform'` gives equal weights (not Newey-West).
- `statsmodels.stats.sandwich_covariance.cov_hac(results, nlags=None)` defaults differ: **`use_correction=True`** and
  nlags = floor(4(T/100)^(2/9)).
- HAC standard error of a mean = `sm.OLS(y, np.ones(T)).fit(cov_type='HAC', cov_kwds={'maxlags': L}).bse[0]`.

## Gibbons-Ross-Shanken (1989) test of joint zero alphas
Time-series regressions $R_{it} = \alpha _{i} + \beta _{i}' f_{t} + e_{it}$ for N test assets (excess returns) on L' traded factors (excess returns),
$t = 1\ldots T$, errors iid normal over time with covariance $\Sigma$. H0: all $\alpha _{i} = 0$.

Unbiased residual covariance, $N$ by $N$:

$$
\hat{\Sigma} = (1/(T - L' - 1)) \sum _{t} e_{t} e_{t}'
$$

$\hat{\mu}$ denotes the factor sample means. Divisor $T$:

$$
\hat{\Omega} = (1/T) \sum _{t} (f_{t} - \hat{\mu})(f_{t} - \hat{\mu})'
$$

$$
\mathrm{GRS} = (T/N) \cdot  ((T - N - L')/(T - L' - 1)) \cdot  \hat{\alpha}' \hat{\Sigma}^{-1} \hat{\alpha} / (1 + \hat{\mu}' \hat{\Omega}^{-1} \hat{\mu})
$$

Under $\mathrm{H0}$:

$$
\mathrm{GRS} \sim F(N, T - N - L')
$$

The p-value is $1 - F_{\mathrm{cdf}}(\mathrm{GRS}; N, T - N - L')$.Equivalent form: $((T - N - L')/N) \cdot  \alpha ' \Sigma _{\mathrm{mle}}^{-1} \alpha  / (1 + \mu ' \hat{\Omega}^{-1} \mu )$ with $\Sigma _{\mathrm{mle}}$ = residual
cross-products / T. Do not mix the two ($\Sigma _{\mathrm{mle}}$ with the T/(T-L'-1) factor over-rejects). One factor: the denominator is
$1+(\mathrm{factor\ Sharpe})^2$, with mean and standard deviation at the data frequency and the standard deviation computed with divisor $T$ (`ddof=0`), consistent with $\hat\Omega$. Requires $T>N+L'$ and full rank of the design, factor covariance and residual covariance. The sample-size inequality alone does not ensure invertibility.

## Common variants and mistakes
- Divisor of $\gamma _{l}$: T (Newey-West, PSD) vs T - l (not guaranteed PSD); weights 1 - l/(L+1), not 1 - l/L.
- Lag definition: L counts lags beyond 0; "L lags" includes lags 1..L. Some software instead takes a bandwidth b with weights 1 - l/b; then $b = L + 1$.
- Not demeaning the series for a mean, or forgetting the factor 2 on the autocovariances.
- Reporting statsmodels HAC p-values (normal) when the task asks for t(T - k) p-values, or vice versa.
- Asymptotic Wald alternative to GRS: $T \alpha ' \Sigma _{\mathrm{mle}}^{-1} \alpha  / (1 + \mu ' \hat{\Omega}^{-1} \mu ) \sim \mathrm{chi2}(N)$; use only if the task asks.

## Applicability and known limits
- NW is consistent as T grows with L growing slowly; in small samples with persistent series it understates the variance
  (our AR(1) simulations: coverage of nominal 95% intervals well below 95% when autocorrelation is strong and L is small).
- GRS is exact only under iid normal errors and traded factors; with non-normal or autocorrelated errors use a GMM/HAC Wald test.

## Sources
Newey & West (1987) Econometrica 55(3):703-708; Newey & West (1994) Rev. Econ. Studies 61(4):631-653;
Gibbons, Ross & Shanken (1989) Econometrica 57(5):1121-1152; Kamstra & Shi (2021) "A Note on the GRS Test", UC Riverside WP 202111;
statsmodels 0.15 source (`sandwich_covariance.py`, `linear_model.py`); Stata [TS] newey manual (Methods and formulas).
