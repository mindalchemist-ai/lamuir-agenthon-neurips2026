# Factor regressions and covariance attribution

Use this reference to interpret linear factor exposures and additive variance contributions. It distinguishes fitted return components from risk contributions and robust inference from changing the fitted model. It does not identify causal risk premia from correlated proxies.

## Definitions and conventions

Map return frequency, units, information dates and the intercept convention to the task. A stock excess return subtracts its matching-period risk-free return; an already excess or zero-investment factor is not reduced by that rate again. Percentage-point spreads and decimal returns are different units. Explicit definitions govern annualization, missing observations and covariance divisors.

Let y contain T observations, F contain K factor columns, X include the intercept and F, b contain regression coefficients, and e denote residuals. A prime denotes transpose. These identities concern an unweighted, unpenalized OLS fit with an intercept, full column rank and a common sample.

**Fitted regression and residual**

$$
\begin{gathered}
b = (X'X)^{-1}\cdot X'\cdot y \\
\hat{y} = X\cdot b \\
e = y-\hat{y}
\end{gathered}
$$

The inverse expresses the mathematical solution; near collinearity makes coefficients unstable. Singular designs do not identify unique individual exposures. Robust standard errors cannot remedy identification failure.

## Components of a fitted observation

For intercept $\alpha$ and slope $\beta _{j}$, the component attributed to factor j is its fitted exposure times the observed factor, not the factor's standalone variance.

**Level decomposition at observation t**

$$
\begin{gathered}
c_{j,t} = \beta _{j}\cdot f_{j,t} \\
y_{t} = \alpha  + \sum _{j} c_{j,t} + e_{t}
\end{gathered}
$$

The intercept must be retained when reconstructing levels. It is constant within a fitted window and contributes no within-window variance.

## Covariance allocation of variance

Use sample covariances over exactly the fitted observations and one shared divisor. Assume $\operatorname{Var}(y)>0$. Covariance allocation shares correlated contributions; it is not a decomposition into independent factor variances.

**Fraction of total variance assigned to a fitted component**

$$
a_{j} = \operatorname{Cov}(c_{j},y)/\operatorname{Var}(y)
$$

OLS orthogonality makes the residual contribution equal to its variance fraction on that same sample.

**Residual variance share and coefficient of determination**

$$
\begin{gathered}a_e=\frac{\operatorname{Var}(e)}{\operatorname{Var}(y)}\\ R_{\mathrm{squared}}=1-\frac{\sum_t e_t^2}{\sum_t(y_t-\operatorname{mean}(y))^2}\\ a_e=1-R_{\mathrm{squared}}\end{gathered}
$$

**Exhaustiveness of the allocation**

$$
\sum _{j} a_{j} + a_{e} = 1
$$

To see why, center the level identity, take covariance with y, and use $X'e=0$. Shares can be negative or exceed one; replacing them with absolute values or clipping changes this allocation. With no intercept, shrinkage, out-of-sample residuals or unequal covariance samples, the identity need not hold. A zero total variance gives an undefined fraction.

## Inference versus estimation

HAC inference retains the OLS coefficients but estimates their sampling covariance allowing serial dependence and heteroskedasticity. It does not whiten the data or eliminate serial dependence. Lag bandwidth, finite-sample correction and t versus asymptotic-normal reference distributions are distinct choices. Fixed observation spacing is the usual HAC assumption; deleting an internal month and treating the neighboring rows as adjacent changes the meaning of a lag. It is not necessary for trading-day observations to be adjacent calendar days.

Multiplying y by a positive constant multiplies coefficients and their standard errors by that constant; t-statistics and R-squared remain unchanged. Rescaling a factor instead rescales its coefficient inversely, leaving fitted components unchanged. An annualized $\alpha$ based on arithmetic scaling is not a compounded investment return.

For overlapping windows the estimates share observations; consecutive estimates are not independent. A low rolling R-squared is a descriptive signal, not by itself a statistical test of structural change. Carrying a discontinued proxy forward is an explicit imputation convention, not new information about the underlying risk.

## Checks and scope

Check reconstruction including the intercept, residual orthogonality, allocation totals before rounding, and invariance to consistent unit changes. Risk contribution does not establish causality or tradability of a proxy. This reference supplements rather than replaces the HAC and GRS definitions; their distributional assumptions differ.

## Sources

Newey and West (1987), [A Simple, Positive Semi-Definite, Heteroskedasticity and Autocorrelation Consistent Covariance Matrix](https://www.nber.org/papers/t0055), for robust covariance estimation. [Statsmodels HAC documentation](https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html), for the single-series, ordered-observation assumption. The reconstruction, covariance allocation and unit-invariance identities above follow directly from the OLS normal equations; they are algebraic derivations, not empirical error guarantees.
