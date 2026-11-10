# Fama-MacBeth (1973) cross-sectional regressions (with Newey-West, Shanken, z-scored characteristics, residual momentum)

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Setting and assumptions
- Panel of assets i over periods $t = 1\ldots T$. Each period, regress a cross-section of outcomes (usually next-period or
  future returns) on regressors known at the forecast date: firm characteristics, or betas estimated in a first pass.
- The per-period slopes are treated as a time series; their average is the estimate and their time-series variability gives
  the standard error. This handles cross-sectional correlation of returns automatically; it assumes the slopes are
  uncorrelated over time (otherwise use the Newey-West version).

## Before coding: three rules that change every number
1. One regression per model. When a task compares models with different regressor sets (nested or not), run a separate cross-sectional regression for each model each period, on the rows that are complete for that model's own target and regressors. The coefficients of a smaller model are not a subset of the coefficients of a larger model; copying them gives the wrong slopes, wrong valid-period counts and wrong forecasts.
   lam = {name: {} for name in models}
   for date, month in panel.groupby(date_col):
       for name, cols in models.items():
           sub = month.dropna(subset=[target] + cols)
           if len(sub) < min_obs:
               continue
           lam[name][date] = sm.OLS(sub[target], sm.add_constant(sub[cols], has_constant="add")).fit().params
   assert all(len(lam[m]) > 0 for m in models)   # each model keeps its own valid-period list
2. Calendar periods versus estimated periods. A start rule stated in calendar periods ("forecasts begin after the n-th month") counts the sample's calendar periods, including periods that produced no regression. Keep the full date list and test the date's position in it, not its position among estimated periods.
   all_dates = sorted(panel[date_col].unique())
   pos = {d: i for i, d in enumerate(all_dates)}
   for d in all_dates:
       if pos[d] < n:
           continue
       past = [lam[name][e] for e in lam[name] if e < d]
       avg = sum(past) / len(past)
3. The forecast uses the whole fitted model: averaged intercept plus averaged slopes times every regressor of that model, controls included, standardized exactly as in the fit. Store the full fitted coefficient vector (intercept and every regressor, controls included) for each period, even when the deliverable reports only some of the slopes; the forecast step needs all of them.
   z = month_d[cols]                            # standardized as in the fit
   pred = avg["const"] + z @ avg[cols]
   assert list(avg.index) == ["const"] + cols


## Parameters and units
| symbol | meaning |
|---|---|
| $y_{it}$ | dependent variable of asset i for period t (e.g. return from t to t+1; align dates exactly as the task says) |
| $x_{it}$ | K regressors of asset i observed at t (characteristics, or estimated betas $\hat{\beta}_{i}$) |
| $N_{t}$ | number of assets with complete data at t (must exceed K + 1) |
| $T$ | number of periods with a valid cross-sectional regression (NOT the number of stock-month observations) |
| $\lambda _{t}$ | (K+1)-vector of per-period coefficients (intercept first) |
| $L, h$ | Newey-West lag; return horizon in periods when returns overlap |

## Formulas
Pass 1, only if regressors are betas: for each asset, over the beta window,

$$
R_{it} = a_{i} + b_{i}' f_{t} + e_{it}
$$

This gives $\hat{\beta}_{i}$.
Pass 2, each $t$:

$$
X_{t} = [1, x_{.t}]
$$

The shape is $N_{t}$ by $K+1$.

$$
\hat{\lambda}_{t} = (X_{t}' X_{t})^{-1} X_{t}' y_{t}
$$

Estimate:

$$
\bar{\lambda} = (1/T) \sum _{t} \hat{\lambda}_{t}
$$

FM standard error:

$$
\mathrm{se}_{j} = s_{j} / \sqrt{T}
$$

$$
s_{j}^{2} = (1/(T-1)) \sum _{t} (\hat{\lambda}_{jt} - \bar{\lambda}_{j})^{2}
$$

The t-statistic (p-value from $t(T-1)$ or normal, as the task says):

$$
t_{j} = \bar{\lambda}_{j} / \mathrm{se}_{j}
$$

Covariance:

$$
V_{\mathrm{FM}} = (1/(T(T-1))) \sum _{t} (\hat{\lambda}_{t} - \bar{\lambda})(\hat{\lambda}_{t} - \bar{\lambda})'
$$

The standard error is NOT the per-period OLS standard error, not an average of per-period standard errors, and not
the standard error of one pooled regression. If asked for an average R^2, average the per-period R^2 values.

## Newey-West version (overlapping or persistent slopes)

$$
\begin{gathered}
\gamma _{l} = (1/T) \sum _{t=l+1}^{T} (\hat{\lambda}_{jt} - \bar{\lambda}_{j})(\hat{\lambda}_{j,t-l} - \bar{\lambda}_{j}) \\
\mathrm{se}_{\mathrm{NW},j} = \sqrt{[\gamma _{0} + 2 \sum _{l=1}^{L} (1 - l/(L+1)) \gamma _{l}] / T},   t_{\mathrm{NW},j} = \bar{\lambda}_{j} / \mathrm{se}_{\mathrm{NW},j}
\end{gathered}
$$

With h-period overlapping returns the slopes are serially correlated up to lag h - 1: use $L \ge  h - 1$ unless the task sets L.
$L = 0$ gives sd with divisor T, slightly smaller than the plain FM se. Same as statsmodels `OLS(lambda_j, ones).fit(cov_type='HAC', cov_kwds={'maxlags': L})` (no small-sample factor). See the Newey-West entry for lag rules.

## Shanken (1992) correction (variant; only when regressors are ESTIMATED betas)

$$
\Gamma  = (\gamma _{0}, \gamma _{a}')'
$$

$\gamma _{a}$ denotes the $K$ factor premia (per period, same frequency as returns).

$$
c = \gamma _{a}' \Sigma _{f}^{-1} \gamma _{a}
$$

$\Sigma _{f}$ is the $K$ by $K$ covariance of the factors $f_{t}$ over the pass-1 sample. $\mathrm{Sf}_{\mathrm{star}}$ is block-diagonal: 0 for the intercept, $\Sigma _{f}$ for the factors.
Practical form on top of $V_{\mathrm{FM}}$:

$$
V_{\mathrm{Shanken}} = (1 + c) \cdot  (V_{\mathrm{FM}} - \mathrm{Sf}_{\mathrm{star}} / T) + \mathrm{Sf}_{\mathrm{star}} / T
$$

Asymptotic form it comes from: $\operatorname{Cov}(\hat{\Gamma}) = (1/T) [(1 + c) A \Sigma  A' + \mathrm{Sf}_{\mathrm{star}}]$, $A = (X'X)^{-1} X'$, $X = [1, \hat{\beta}]$,
$\Sigma$ = pass-1 residual covariance. Both forms agree asymptotically, not exactly. No intercept in pass 2: drop its row/column.
Not used for observed characteristics (they are not estimated). c is not annualized when the data are monthly.

## Cross-sectional standardization of characteristics

$$
z_{it} = (x_{it} - \operatorname{mean}_{t}(x)) / \operatorname{sd}_{t}(x)
$$

Mean and standard deviation are over the $N_{t}$ assets present at date $t$.

- Population sd divides by $N_{t}$, sample sd by $N_t-1$. numpy `std` defaults to $\mathrm{ddof}=0$, pandas `.std()` to $\mathrm{ddof}=1$: set ddof
  explicitly to match the task ("population" -> 0, "sample" -> 1). The z-scores differ by the factor $\sqrt{N_{t}/(N_{t}-1)}$.
- Standardize within each date (groupby date), never over the pooled panel (look-ahead). Drop or fill missing values and
  winsorize first if the task says so, then standardize over exactly the assets used in that date's regression.
- Rank variant: replace x by its cross-sectional rank (often scaled to [0,1] or demeaned) before regressing.

## Residual momentum (variant; Blitz, Huij and Martens 2011, standardization as in Gutierrez and Prinsky 2007)
For each stock i and formation date t (ranking for the holding period that starts at t):
1. Over the W months t-W..t-1 regress excess returns on the factor model (BHM: Fama-French three factors) with an intercept:
   $r_{is} = \alpha _{i} + \beta _{i}' f_{s} + \mathrm{eps}_{is}$; keep only stocks with a complete window.
2. Residuals exclude $\alpha$: $\hat{\mathrm{eps}}_{is} = r_{is} - \hat{\alpha}_{i} - \hat{\beta}_{i}' f_{s}$ (do not add $\alpha$ back).
3. Formation months: $s = t-J\ldots t-1-S$(S = skip months; BHM use the past year and skip the most recent month).
4. Score: $\sum  \hat{\mathrm{eps}}_{is} / \operatorname{sd}(\hat{\mathrm{eps}}_{is})$ over the formation months (sd over the SAME months; ddof per task).
   mean/sd ranks identically when every stock has the same number of formation months.
5. Sort stocks on the score each date (e.g. deciles), long the top, short the bottom, weighting as the task says.
Mistakes: regressing without an intercept; including month t-1; using factor betas estimated with data after t-1;
scaling by total-return volatility or by the whole W-month residual sd (only if the task defines it that way).

## Applicability and known limits
- FM se is robust to cross-sectional correlation but not to serial correlation of $\lambda _{t}$ (persistent characteristics,
  overlapping returns); then use Newey-West. With estimated betas the slopes have errors-in-variables bias in finite T and
  the non-factor variance component receives the Shanken multiplier $1+c$; the corresponding standard-error multiplier is $\sqrt{1+c}$, not $1+c$. The full covariance also contains the separate factor component shown above.
- Unbalanced panels are fine; T counts only periods actually regressed. Small $N_{t}$ makes per-period slopes noisy.
- That T is for averaging slopes and their standard errors. A start or window rule stated in calendar periods (forecasts begin after the n-th calendar month, say) counts calendar periods of the sample, including periods that produced no regression; it is not the n-th estimated period. An expanding average of slopes at a forecast date uses every slope estimated before that date. The forecast is the averaged intercept plus the averaged slopes times every regressor of the fitted model, controls included, standardized as in the fit; leaving the controls out ranks the assets on a different model.

## Sources
Fama & MacBeth (1973) J. Political Economy 81(3):607-636; Shanken (1992) Rev. Financial Studies 5(1):1-33;
Shanken & Zhou (2007) J. Financial Economics 84(1):40-86 (eq. 9, statement of the Shanken covariance);
Newey & West (1987) Econometrica 55(3):703-708; Blitz, Huij & Martens (2011) J. Empirical Finance 18(3):506-521;
Gutierrez & Prinsky (2007) J. Financial Markets 10(1):48-75 (cited via BHM; original not read).
