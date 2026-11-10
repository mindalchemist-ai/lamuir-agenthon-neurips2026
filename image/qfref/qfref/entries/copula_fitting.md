# Bivariate copula fitting by pseudo-maximum likelihood: Gaussian, Student-t, Clayton, Gumbel, Frank

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

Before forming pairs, fix two things the outputs depend on: the order of the instruments and the pair label.

Order of instruments (it decides which instrument is first in each pair, and the row order):
- the order the task lists them in (a list in the text, or the column order of a wide input table as supplied): the
  default when the task lists them and says nothing about sorting; do not sort them then. A table the code builds
  itself (pivot, unstack, groupby) has sorted columns, and that order is not the task's order: take the names from
  the task's list and reindex the built table to it;
- the order of first appearance in a long table: when the instruments are only found in the data;
- alphabetical: when the task says "sorted" or "alphabetical", or its example labels are alphabetical;
- an order defined by a value (market cap, sector): when the task names it.

Pair label (key or column value):
- the task's example label or stated separator wins ("AAA-BBB", "AAA_BBB", "AAA/BBB");
- a JSON list ["AAA", "BBB"] or two columns (asset_1, asset_2) when the task asks for an unambiguous encoding or two
  fields; avoid joining with a character that can occur inside a ticker (a hyphen in "BRK-B");
- without either, "FIRST-SECOND" with the earlier instrument first; state the order used.

```python
names = list(dict.fromkeys(df["symbol"]))           # the order chosen above: first appearance here; sorted(...) when the task sorts
pairs = list(itertools.combinations(names, 2))      # (a, b) with a before b in that order
print(pairs[:3])                                    # compare with the task's list before fitting
labels = [f"{a}-{b}" for a, b in pairs]             # the task's separator or encoding
assert len(labels) == len(names) * (len(names) - 1) // 2
```

## Setting and assumptions
- n i.i.d. pairs ($x_{i}$, $y_{i}$) with continuous margins (for returns: often i.i.d. residuals after a volatility filter, if the task says so).
  $H(x, y) = C(F(x), G(y))$; the copula C carries all dependence. Margins are NOT modelled (canonical / pseudo-ML, Genest, Ghoudi & Rivest 1995).
- Pseudo-observations: $u_{i} = R_{i} / (n + 1)$, $v_{i} = S_{i} / (n + 1)$, $R_{i} = \operatorname{rank}$ of $x_{i}$ among $x_{1}$..$x_{n}$ (1 = smallest), $S_{i}$ likewise for y; ties get average ranks.
  Ranks are unchanged by strictly increasing transforms of a series (e.g. standardizing), but prices and returns are different series: rank the series the task names.
- Estimate: $\hat{\theta} = \mathrm{argmax} l(\theta )$, $l(\theta ) = \sum _{i} \log  c(u_{i}, v_{i}; \theta )$ (c = copula density).
- Variant IFM ("inference functions for margins"): fit parametric margins first and use $u_{i} = \hat{F}(x_{i})$. Use it only if the task says so.

## Parameters and units
| symbol | meaning | domain |
|---|---|---|
| $u, v$ | pseudo-observations | strictly inside (0, 1) |
| $\rho$ | Gaussian / t copula correlation parameter (not Pearson of raw data) | (-1, 1) |
| $\nu$ | t copula degrees of freedom | $\nu  > 0$(many tasks/libraries restrict to $\nu  > 2$ and cap large $\nu$) |
| $\theta$ (Clayton) | Clayton parameter; $\theta  \to  0$ is independence | $\theta  > 0$ |
| $\theta$ (Gumbel) | Gumbel parameter; $\theta  = 1$ is independence | $\theta  \ge  1$ |
| $\theta$ (Frank) | Frank parameter; $\theta  \to  0$ independence, $\theta  < 0$ negative dependence | $\mathrm{real}, \theta  \ne  0$ |
| $\hat{\tau}$ | sample Kendall's $\tau$ of (x, y) (equals that of (u, v)) | [-1, 1] |

## Log-densities (natural logs; Phi^-1 standard normal quantile; t_nu^-1 standard Student-t quantile with nu df)
- Gaussian, $x = \Phi ^{-1}(u)$, $y = \Phi ^{-1}(v)$: $\log  c = -0.5 \ln (1 - \rho ^{2}) - [\rho ^{2} (x^{2} + y^{2}) - 2 \rho  x y] / [2 (1 - \rho ^{2})]$.
- Student-t, $x = t_{\nu}^{-1}(u)$, $y = t_{\nu}^{-1}(v)$ (same $\nu$ as the copula):
  $\log  c = \mathrm{lnGamma}((\nu +2)/2) + \mathrm{lnGamma}(\nu /2) - 2 \mathrm{lnGamma}((\nu +1)/2) - 0.5 \ln (1 - \rho ^{2})$
  $- ((\nu +2)/2) \ln (1 + (x^{2} - 2 \rho  x y + y^{2}) / (\nu  (1 - \rho ^{2}))) + ((\nu +1)/2) [\ln (1 + x^{2}/\nu ) + \ln (1 + y^{2}/\nu )]$.
- Clayton, $C = (u^{-\theta}  + v^{-\theta}  - 1)^{-1/\theta}$:
  $\log  c = \ln (1 + \theta ) - (1 + \theta )(\ln  u + \ln  v) - (2 + 1/\theta ) L$, $L = \ln (u^{-\theta}  + v^{-\theta}  - 1)$.
  Stable L: $a = -\theta  \ln  u$, $b = -\theta  \ln  v$, $m = \max (a, b)$, $l = \min (a, b)$: $L = m + \mathrm{log1p}(\exp (l - m) \cdot  (-\mathrm{expm1}(-l)))$.
- Gumbel, $s = -\ln  u$, $t = -\ln  v$, $S = s^{\theta} + t^{\theta}$, $A = S^{1/\theta}$, $C = \exp (-A)$:
  $\log  c = -A + s + t + (\theta  - 1)(\ln  s + \ln  t) + (1/\theta  - 2) \ln  S + \ln (A + \theta  - 1)$;
  stable $\ln  S = \theta  \ln  \max (s, t) + \mathrm{log1p}((\min (s, t)/\max (s, t))^{\theta})$.
- Frank, $C = -(1/\theta ) \ln [1 + (e^{-\theta  u} - 1)(e^{-\theta  v} - 1) / (e^{-\theta} - 1)]$,
  $c = \theta  (1 - e^{-\theta}) e^{-\theta  (u+v)} / D^{2}$, $D = (1 - e^{-\theta}) - (1 - e^{-\theta  u})(1 - e^{-\theta  v})$.
  Stable for $\theta  > 0$: $D = e^{-\theta  u}(1 - e^{-\theta  v}) + e^{-\theta  v}(1 - e^{-\theta  (1-v)})$ (two non-negative terms):
  $\log  c = \ln  \theta  + \ln (1 - e^{-\theta}) - \theta  (u + v) - 2 \ln  D$, $\ln  D$ by log-sum-exp, $1 - e^{-z}$ as `-expm1(-z)`.
  For $\theta  < 0$ use $c(u, v; \theta ) = c(u, 1 - v; -\theta )$ (avoids overflow of e^(-$\theta$)).

## Negative dependence with Clayton / Gumbel (they only reach tau >= 0)
- Rotation: fit the base copula to transformed pseudo-observations. 90 deg: density $c(1 - u, v)$; 270 deg: $c(u, 1 - v)$
  (both give $\tau$ = -$\tau _{\mathrm{base}}$); 180 deg (survival): $c(1 - u, 1 - v)$ (same sign of $\tau$, tail moved to the other corner).
  Which of the two is called "90" vs "270" differs between libraries: follow the task's definition and state the transform.
- Restriction: keep the base domain; for $\hat{\tau} < 0$ the maximum sits on the boundary (Clayton $\theta  \to  0$, Gumbel $\theta  = 1$,
  i.e. independence, log-likelihood near 0). Report it as such; do not let $\theta$ leave the domain.
- Clayton's extension to $\theta$ in [-1, 0) has support only where $u^{-\theta}  + v^{-\theta}  - 1 > 0$; points outside give $\log  c = -\infty$. Avoid in pseudo-ML unless the task requires it.
- Gaussian, t and Frank cover both signs directly; no rotation needed.

## Starting values: Kendall's tau inversion (also an estimator in its own right, "method of moments")
- Gaussian and t: $\rho  = \sin (\pi  \hat{\tau} / 2)$. Clayton: $\theta  = 2 \hat{\tau} / (1 - \hat{\tau})$. Gumbel: $\theta  = 1 / (1 - \hat{\tau})$.
- Frank: solve $1 - 4/\theta  + 4 D_{1}(\theta )/\theta  = \hat{\tau}$ by root finding (monotone; $\operatorname{sign}(\theta ) = \operatorname{sign}(\hat{\tau})$),
  $D_{1}(x) = (1/x) \int _{0}^{x} t / (e^{t} - 1) \mathrm{d}t$.
- t: $\nu$ has no $\tau$ relation; start from a profile likelihood over a $\nu$ grid. A common two-step variant fixes $\rho$ by $\tau$ inversion and maximizes over $\nu$ only.
- If the task says "estimate by inversion of Kendall's $\tau$", report these values, not the MLE.

## Information criteria
$\mathrm{AIC} = 2k - 2 \hat{l}$, $\mathrm{BIC} = k \ln (n) - 2 \hat{l}$, n = number of pairs, $\hat{l}$ = maximized copula log-likelihood. Lower is better.
$k = 1$ for Gaussian, Clayton, Gumbel, Frank (rotated or not: rotation is a discrete choice, not a parameter); k = 2 for t ($\rho$, $\nu$);
independence $k = 0, l = 0$. Marginal parameters are not counted under pseudo-ML. Some tasks report AIC/n or -AIC; follow the task.

## Numerical practice and common mistakes
- Write each log-density as a per-observation array `logc` (constants broadcast to every row) and take `loglik = logc.sum()` once; a constant added once instead of n times shifts the likelihood and can reverse the model ranking. The t copula nests the Gaussian: at very large $\nu$ with the same $\rho$ the two log-likelihoods agree, so a fitted t log-likelihood far below the Gaussian one is a bug.
```python
assert abs(loglik_t(u, v, rho, 1e6) - loglik_gauss(u, v, rho)) < 1e-3 * max(1.0, abs(loglik_gauss(u, v, rho)))
```
- Optimize on unconstrained variables: $\rho  = \tanh (z)$, Clayton $\theta  = e^{z}$, Gumbel $\theta  = 1 + e^{z}$, $\nu  = \nu _{\mathrm{min}} + e^{z}$;
  for Frank avoid $\theta  = 0$ exactly (formula 0/0; density is 1 there). $\nu$: likelihood is flat for large $\nu$ (t tends to Gaussian); report if at the cap.
- Raw data instead of pseudo-observations: $\Phi^{-1}(x)$ is nan outside (0, 1); with data inside (0, 1) the fit is silently wrong.
- $\operatorname{rank} / n$ instead of $\operatorname{rank} / (n + 1)$: the largest point gets $u = 1$; Gaussian / t / Gumbel log-likelihoods become nan or inf,
  while Clayton and Frank stay finite but biased (no error is raised, so the mistake is silent there).
- Parameter outside the domain ($\rho  = \pm 1$, Clayton $\theta  \le  0$, Gumbel $\theta  < 1$) gives nan/-inf or meaningless numbers;
  enforce the domain in the parametrization instead of relying on the formula to fail.
- t copula: the quantiles use the copula $\nu$, not a marginal df; counting $k = 1$ for t is wrong.
- Naive overflow: u^-$\theta$ (large Clayton $\theta$), e^(-$\theta$) (Frank $\theta  < 0), s^{\theta} ($large Gumbel $\theta$). Use the stable forms above.
- Tail dependence (helps choose a family): Clayton lower $2^{-1/\theta}$, upper 0; Gumbel upper $2 - 2^{1/\theta}$, lower 0;
  t both tails $2 t_{\nu +1}(-\sqrt{(\nu +1)(1-\rho )/(1+\rho )})$; Gaussian and Frank 0. Survival rotation swaps lower and upper.

## Applicability and known limits
- Pseudo-ML is consistent and asymptotically normal but its standard errors are not the inverse Hessian of l (rank effect); use the task's method or a bootstrap.
- Assumes i.i.d. pairs and continuous margins; heavy ties (discrete data, stale prices) break the rank argument.
- AIC/BIC compare families with the same pseudo-observations only; a fitted family can still fail a goodness-of-fit test.

## Sources
Genest, Ghoudi & Rivest (1995) Biometrika 82(3):543-552; Nelsen (2006) An Introduction to Copulas, 2nd ed., Springer;
Joe (2014) Dependence Modeling with Copulas, Chapman & Hall/CRC; Demarta & McNeil (2005) Int. Statist. Rev. 73(1):111-129;
Clayton (1978) Biometrika 65(1):141-151; Frank (1979) Aequationes Math. 19:194-226; Genest (1987) Biometrika 74:549-555;
McNeil, Frey & Embrechts (2015) Quantitative Risk Management, rev. ed., Princeton UP; Akaike (1974) IEEE TAC 19(6):716-723;
Schwarz (1978) Ann. Statist. 6(2):461-464. Stable forms of the densities derived here and checked numerically.
