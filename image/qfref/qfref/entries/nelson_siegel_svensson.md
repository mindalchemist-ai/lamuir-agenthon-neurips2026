# Nelson-Siegel (1987), Svensson (1994) and Diebold-Li (2006) yield-curve parameterizations

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Model and assumptions
- A smooth parametric curve for the zero-coupon (spot) rate z(m) and the instantaneous forward rate f(m) at time to maturity m,
  for ONE trade date. Nelson-Siegel (NS) has 3 betas + 1 decay; Svensson (NSS) adds a second hump: 4 betas + 2 decays.
- In both papers the rates are CONTINUOUSLY compounded: discount factor $\mathrm{DF}(m) = \exp (-z(m) \cdot  m)$, and
  $z(m) = (1/m) \cdot  \int _{0}^{m} f(u) \mathrm{d}u$, i.e. $f(m) = d[m z(m)]/\mathrm{d}m$. Not arbitrage-free; a fitting device, not a dynamic model.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $m$ | time to maturity (years unless the task says months) | years |
| beta0 | long-run level: z and f tend to beta0 as $m \to  \infty$(either sign is allowed; positivity is an optional fitting restriction) | rate, decimal (5% = 0.05) |
| beta1 | $\mathrm{slope}: z(0) = f(0) = \mathrm{beta0} + \mathrm{beta1}$ | rate |
| beta2 | first hump/trough, decay tau1 | rate |
| beta3 | second hump/trough, decay tau2 (Svensson only) | rate |
| tau1, tau2 | decay times (> 0), same time unit as m | years |
| $\lambda$ | an ambiguous name: Diebold-Li use it for the decay RATE $1/\tau$ (loadings in $\lambda m$); other texts and tasks use it for the decay TIME $\tau$ itself (loadings in $m/\lambda$). See "Which parameterization" below | depends |

## Formulas (x1 = m/tau1, x2 = m/tau2)
Loadings (write them once and reuse):

$$
\begin{gathered}
S(x) = (1 - \exp (-x)) / x\quad (\mathrm{slope} \mathrm{loading}; S(0) = 1) \\
C(x) = S(x) - \exp (-x)\quad (\mathrm{curvature}/\mathrm{hump} \mathrm{loading}; C(0) = 0, C(\infty ) = 0)
\end{gathered}
$$

Svensson zero rate and forward rate:

$$
\begin{gathered}
z(m) = \mathrm{beta0} + \mathrm{beta1} \cdot  S(\mathrm{x1}) + \mathrm{beta2} \cdot  C(\mathrm{x1}) + \mathrm{beta3} \cdot  C(\mathrm{x2}) \\
f(m) = \mathrm{beta0} + \mathrm{beta1} \cdot  \exp (-\mathrm{x1}) + \mathrm{beta2} \cdot  \mathrm{x1} \cdot  \exp (-\mathrm{x1}) + \mathrm{beta3} \cdot  \mathrm{x2} \cdot  \exp (-\mathrm{x2})
\end{gathered}
$$

- beta1 AND beta2 both use tau1; ONLY beta3 uses tau2. Nelson-Siegel = the same formulas with $\mathrm{beta3} = 0$(no tau2).
- Limits: $m \to  0$: $z = f = \mathrm{beta0} + \mathrm{beta1}$(the "instantaneous short rate"); m -> infinity: $z = f = \mathrm{beta0}$.
  z approaches beta0 slowly (like 1/m); f approaches it exponentially. At $m = 0$ use $S = 1, C = 0$(no 0/0).
- Discount factor $\mathrm{DF}(m) = \exp (-z(m) m)$; $\mathrm{bond\ price}=\sum_j\mathrm{CF}_j\mathrm{DF}(t_j)$; forward between $\mathrm{m1} < \mathrm{m2}$:
  $F(\mathrm{m1}, \mathrm{m2}) = [z(\mathrm{m2}) \mathrm{m2} - z(\mathrm{m1}) \mathrm{m1}] / (\mathrm{m2} - \mathrm{m1})$ (continuous).
- Original NS (1987) zero form: $z = \mathrm{beta0} + (\mathrm{beta1} + \mathrm{beta2}) \cdot  S(x) - \mathrm{beta2} \cdot  \exp (-x)$ is algebraically identical to the above.
- Diebold-Li (2006) form: $y(m) = \mathrm{L1} + \mathrm{L2} \cdot  S(\lambda  m) + \mathrm{L3} \cdot  C(\lambda  m)$ = NS with $\tau  = 1/\lambda$,
  L1 = level, L2 = slope, L3 = curvature. DL measure m in MONTHS and fix $\lambda$ for all dates at the value they say puts the
  peak of C at 30 months. Use the $\lambda$ value the task gives: solving dC/dm = 0 at exactly 30 months gives a value slightly
  below the one DL print. A $\lambda$ per month becomes per year by multiplying by 12. With $\lambda$ fixed the model is linear in
  L1..L3, so fit by ordinary least squares on each date.

## Which parameterization the task uses
- The same curve can be written with decay times ($x = m / \tau$) or decay rates ($x = \lambda  m, \lambda  = 1/\tau$). The name of a
  parameter does not decide which: some texts and tasks write the decay TIME as $\lambda$.
- Decide from the task's formula for the loadings, or from units the task states explicitly. If the task gives neither, report
  the parameter in the form you fitted and say which form it is; do not take a reciprocal only because an output field is named $\lambda$.
- Before writing the outputs, plug the parameters you will report into the formula you used and check that they reproduce your
  fitted curve and the fit error you report.

## Fitting (estimate the betas and taus)
- Yield errors: minimize $\sum _{i} (z_{\mathrm{model}}(m_{i}) - z_{\mathrm{obs}}(m_{i}))^{2}$ over zero yields, or over model-implied vs observed YTMs of coupon bonds.
- Price errors: model price $\operatorname{P}_{i} = \sum _{j} \mathrm{CF}_{ij} \exp (-z(t_{ij}) t_{ij})$, minimize $\sum _{i} w_{i} (\operatorname{P}_{i} - \operatorname{P}_{\mathrm{obs},i})^{2}$. Unweighted price errors
  have a different scale from yield errors. Locally, $\Delta P_i \approx -P_i D_i \Delta y_i$ with $D_i$ the modified duration under the yield compounding convention, so weights proportional to $1/(P_iD_i)^2$ approximate squared yield errors for currency price residuals; for relative price residuals, use $1/D_i^2$.
  Use full (dirty) prices for cash flows; if clean prices are given add accrued interest.
- Nonlinear least squares (e.g. bounded trust-region) requires positive decay times $\tau_1,\tau_2$. Positive short- and long-end limits do not guarantee positive yields or forwards between them. Decay times need not lie inside the observed maturity range; additional bounds are fitting restrictions, not model identities. The objective is non-convex with local minima (Gilli et al. 2010):
  use several starting points (e.g. beta0 from the longest yield, beta1 from shortest minus longest, $\mathrm{betas2}/3 = 0$, a few $\tau$ pairs)
  and keep the lowest objective; or profile: grid over (tau1, tau2), OLS for the betas at each grid point, keep the best.
- Near-equal decay times can make hump loadings nearly collinear and parameter estimates unstable. A decay ordering or minimum gap is an additional constraint and must not silently replace an unconstrained specification. Similar fitted curves need not identify individual parameters.

## Compounding conversions (apply to OUTPUTS only if the task asks)
- Annual: $R_{a} = \exp (z) - 1$, $z = \ln (1 + R_{a})$. Periodic k per year: $R_{k} = k (\exp (z/k) - 1)$, $z = k \ln (1 + R_{k}/k)$.
- If the observed yields are annual / semi-annual (e.g. bond-equivalent) convert them to continuous BEFORE fitting, or fit in
  their convention and say so; never mix. Percent vs decimal: keep one unit throughout.

## Common mistakes
- Pairing beta3 with tau1, or giving beta2 its own tau2: wrong curve (the error can be hundreds of basis points).
- Using forward loadings ($\exp (-x), x \exp (-x)$) in the zero-rate formula or vice versa.
- Switching between decay time and decay rate (taking 1/x) when the task's parameter is already in the form you fitted;
  reporting parameters that do not reproduce your own fitted curve; using a $\lambda$ calibrated for months with maturities in years.
- Evaluating S(0) as 0/0 (NaN) at $m = 0$.
- Reporting fitted parameters from one local optimum without checking the fit residuals.

## Applicability and limits
- Good for smoothing and interpolation inside the observed maturity range; extrapolation is governed by beta0.
- Does not reprice every bond exactly (a least-squares fit); if exact repricing is required, bootstrap instead.
- Parameters are unstable when the problem is ill-conditioned (Gilli et al. 2010); compare fitted curves, not parameters.

## Sources
Nelson & Siegel (1987) "Parsimonious Modeling of Yield Curves", Journal of Business 60:473-489;
Svensson (1994) "Estimating and Interpreting Forward Interest Rates: Sweden 1992-1994", NBER WP 4871 / IMF WP 94/114;
Diebold & Li (2006) "Forecasting the Term Structure of Government Bond Yields", Journal of Econometrics 130:337-364;
Gilli, Grosse & Schumann (2010) "Calibrating the Nelson-Siegel-Svensson Model", COMISEF Working Paper 31.
