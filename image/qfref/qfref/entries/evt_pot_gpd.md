# Extreme value theory: peaks-over-threshold (GPD), Hill estimator, and VaR backtests (Kupiec, Christoffersen)

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Setting and assumptions
- Work with LOSSES, large = bad: $x_{t} = -r_{t}$ (or `-(P&L)`). Fit the right tail of x. A task that keeps returns must flip the sign; VaR/ES are then reported as positive loss numbers.
- Pickands-Balkema-de Haan: above a high threshold u, the excess $Y = X - u \vert  X > u$ is approximately generalized Pareto (GPD).
  Data are treated as i.i.d. (or as GARCH-standardized residuals, McNeil & Frey 2000; then scale back with the forecast mean and $\sigma$).
- Threshold u: given by the task, or an empirical quantile, or "the k largest losses" (then u = the (k+1)-th largest loss and $N_{u} = k$).
  Diagnostics: mean-excess plot $e(v) = \operatorname{mean}(x_{i} - v \vert  x_{i} > v)$ approximately linear for $v\ge u$ (slope $\xi/(1-\xi)$); fitted $\xi$ stable when u is moved.
  Exceedances use strict $x_{i} > u$; ties at u are not exceedances unless the task says otherwise.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $n$ | number of loss observations | count |
| $u, N_{u}$ | threshold, number of $x_{i} > u; y_{i} = x_{i} - u$ for those i | loss units, count |
| $\xi$ | shape (tail index $1/\xi$ when $\xi>0$); $\xi>0$ heavy tail, $\xi  = 0$ exponential, $\xi  < 0$ bounded tail | none |
| $\beta$ | $\mathrm{GPD} \mathrm{scale}, \beta  > 0$ | loss units |
| $p$ | VaR/ES confidence level (99% is 0.99); tail probability is 1 - p | none |

## GPD (exceedance y >= 0)
When $\xi  \ne  0$:

$$
G(y) = 1 - (1 + \xi  y / \beta )^{-1/\xi}
$$

$$
g(y) = (1/\beta ) (1 + \xi  y / \beta )^{-1/\xi  - 1}
$$

When $\xi  = 0$:

$$
G(y) = 1 - \exp (-y / \beta )
$$

$$
g(y) = (1/\beta ) \exp (-y / \beta )
$$

Support: $y \ge  0$ if $\xi  \ge  0$; $0 \le  y \le  -\beta /\xi$ if $\xi  < 0$.Log-likelihood of the $N_{u}$ exceedances:

$$
\begin{gathered}
\xi  \ne  0:  l(\xi , \beta ) = -N_{u} \ln (\beta ) - (1 + 1/\xi ) \cdot  \sum _{i} \ln (1 + \xi  y_{i} / \beta ) \\
\xi   = 0:  l(\beta )     = -N_{u} \ln (\beta ) - \sum _{i} y_{i} / \beta
\end{gathered}
$$

MLE constraints: $\beta  > 0$ and $1 + \xi  y_{i} / \beta  > 0$ for every i (return -inf otherwise; this matters for $\xi  < 0$).
Maximize numerically (e.g. Nelder-Mead on -l from a method-of-moments start $\mathrm{xi0} = (1 - m^{2}/s^{2})/2$, $\mathrm{beta0} = m (1 + m^{2}/s^{2})/2$, $m, s^{2} = \operatorname{mean}$, variance of y).
Use the $\xi  = 0$ branch (or |$\xi$| tiny) to avoid dividing by zero. MLE is regular for $\xi  > -1/2$; for $\xi  \le  -1$ the likelihood is unbounded (Smith 1985).
Library check: `scipy.stats.genpareto` uses the same sign of $\xi$ ($c = \xi$), fit with $\mathrm{floc}=0$ on the $y_{i}$.

## Tail estimator, VaR and ES (McNeil & Frey 2000)
For $x > u$: $\hat{F}(x) = 1 - (N_{u} / n) (1 + \xi  (x - u) / \beta )^{-1/\xi}$. Inverting at level p:

When $\xi  \ne  0$:

$$
\operatorname{VaR}_{p} = u + (\beta  / \xi ) \cdot  ( ((n / N_{u}) (1 - p))^{-\xi} - 1 )
$$

When $\xi  = 0$:

$$
\operatorname{VaR}_{p} = u - \beta  \cdot  \ln ( (n / N_{u}) (1 - p) )
$$

Valid only for $\xi  < 1$ (ES is infinite for $\xi  \ge  1$):

$$
\operatorname{ES}_{p} = \operatorname{VaR}_{p} / (1 - \xi ) + (\beta  - \xi  u) / (1 - \xi )
$$

Valid only when $1 - p < N_{u} / n$ ($\operatorname{VaR}_{p}$ above u); otherwise use the empirical quantile. Mean excess over $v \ge  u$: $(\beta  + \xi  (v - u)) / (1 - \xi )$.

## Variant: Hill estimator (xi > 0, positive losses only)
Sort descending $X_{1} \ge  \ldots  \ge  X_{n}$; with k upper order statistics (all $X_{i} > 0$):

$$
\xi _{H} = (1/k) \cdot  \sum _{i=1}^{k} \ln  X_{i} - \ln  X_{k+1}
$$

Tail index:

$$
\alpha _{H} = 1 / \xi _{H}
$$

Weissman quantile:

$$
\operatorname{VaR}_{p} = X_{k+1} \cdot  ( (n / k) (1 - p) )^{-\xi _{H}}
$$

For $\xi _{H} < 1$:

$$
\operatorname{ES}_{p} = \operatorname{VaR}_{p} / (1 - \xi _{H})
$$

Some texts use $X_{(k)}$ as the threshold with divisor k - 1 or k; follow the task. Hill assumes a Pareto-type tail and is biased when the tail is not exactly Pareto.

## VaR backtests (hit sequence $I_t=1$ if $\mathrm{loss}_t>\operatorname{VaR}_t$, else 0; $t=1,\ldots,T$)
p0 = expected violation probability = 1 - (VaR confidence). $x = \sum  I_{t}, \hat{\pi} = x / T$. Convention: $0 \cdot  \ln (0) = 0$.

Kupiec POF:

$$
\mathrm{LR}_{\mathrm{POF}} = -2 [ (T - x) \ln (1 - \mathrm{p0}) + x \ln (\mathrm{p0}) ] + 2 [ (T - x) \ln (1 - \hat{\pi}) + x \ln (\hat{\pi}) ] \sim \mathrm{chi2}(1)
$$

For $x = 0$:

$$
\mathrm{LR}_{\mathrm{POF}} = -2 T \ln (1 - \mathrm{p0})
$$

For $x = T$:

$$
\mathrm{LR}_{\mathrm{POF}} = -2 T \ln (\mathrm{p0})
$$

Christoffersen independence: count transitions over $t = 2\ldots T$, $n_{ij}$ = #$\{I_{t-1} = i, I_{t} = j\}$:

$$
\pi _{01} = \mathrm{n01} / (\mathrm{n00} + \mathrm{n01})
$$

$$
\pi _{11} = \mathrm{n11} / (\mathrm{n10} + \mathrm{n11})
$$

$$
\pi  = (\mathrm{n01} + \mathrm{n11}) / (\mathrm{n00} + \mathrm{n01} + \mathrm{n10} + \mathrm{n11})
$$

Null: no clustering.

$$
\ln  \mathrm{L0} = (\mathrm{n00} + \mathrm{n10}) \ln (1 - \pi ) + (\mathrm{n01} + \mathrm{n11}) \ln (\pi )
$$

Alternative: first-order Markov.

$$
\ln  \mathrm{L1} = \mathrm{n00} \ln (1 - \pi _{01}) + \mathrm{n01} \ln (\pi _{01}) + \mathrm{n10} \ln (1 - \pi _{11}) + \mathrm{n11} \ln (\pi _{11})
$$

$$
\mathrm{LR}_{\mathrm{ind}} = -2 (\ln  \mathrm{L0} - \ln  \mathrm{L1}) \sim \mathrm{chi2}(1)
$$

$$
\mathrm{LR}_{\mathrm{cc}} = \mathrm{LR}_{\mathrm{POF}} + \mathrm{LR}_{\mathrm{ind}} \sim \mathrm{chi2}(2)
$$

Edge cases: no hits $\to  \mathrm{LR}_{\mathrm{ind}} = 0; \mathrm{n10} + \mathrm{n11} = 0$(only hit is the last observation) -> $\pi _{11}$ terms drop out; n11 = 0 -> $\mathrm{n11} \ln (\pi _{11}) = 0$ and $\mathrm{n10} \ln (1) = 0$.
p-value = $1 - \mathrm{chi2}.\operatorname{cdf}(\mathrm{LR}, \mathrm{df})$; reject at level a if p-value < a. $\mathrm{LR}_{\mathrm{ind}}$ equals the G-test of independence on the 2x2 table [[n00, n01], [n10, n11]].
$\mathrm{LR}_{\mathrm{cc}}$ variants: (a) $\mathrm{LR}_{\mathrm{POF}}$ on all T plus $\mathrm{LR}_{\mathrm{ind}}$ (common), (b) $-2 (\ln  L(\mathrm{p0}) - \ln  \mathrm{L1})$ on the T-1 transitions, which equals $\mathrm{LR}_{\mathrm{POF}}$ on $I_2,\ldots,I_T$ plus $\mathrm{LR}_{\mathrm{ind}}$ exactly. Results differ slightly; follow the task.

## Common variants and mistakes
- Several models in one session: the GPD scale $\beta$, a normal or GARCH volatility $\sigma$ and a t scale are different parameters. Keep each under its own name (for example `gpd_beta`, `normal_sigma`), pass the intended one to each formula, and when a fitted parameter changes, recompute every VaR, ES and derived result that uses it before writing outputs.
- Level labels built from a confidence level p: take the digits after the decimal point (0.99 → "99", 0.995 → "995", 0.999 → "999"), for example `format(p, "g").split(".")[1]` or the string the task lists. A fixed multiplier fails for one of them: `int(p * 100)` turns 0.995 into "99", `int(p * 1000)` turns 0.99 into "990", and floating point can make `int(0.29 * 100)` 28.
- Sign: fitting the GPD to returns (left tail as negative numbers) or forgetting $y = x - u$ (fitting x itself) gives nonsense $\beta$.
- $N_{u}$ / n vs (1 - threshold quantile): use the actual count $N_{u}$ when u is an empirical quantile.
- Violation as $\ge$ vs $>$, and `return < -VaR` vs $\mathrm{loss} > \operatorname{VaR}$: same thing if VaR is positive; follow the task.
- Basel traffic light (BCBS 1996): with T daily 99% VaR hits, yellow zone starts at the smallest x with $\mathrm{BinomCDF}(x; T, 0.01) \ge  0.95$, red at $\ge  0.9999$.
- Kupiec has low power in small samples, and its exact size differs from nominal because x is discrete; $\mathrm{LR}_{\mathrm{ind}}$ is oversized when few hits are expected.

## Applicability and known limits
- GPD needs enough exceedances and a high enough u; too low u biases $\xi$ (e.g. a Student-t tail fitted at a moderate quantile gives $\xi$ below $1/\nu$), too high u inflates variance.
- ES formula requires $\xi  < 1$; second moments need $\xi  < 1/2$. Clustered (non-i.i.d.) losses: filter first (GARCH) or decluster.

## Sources
Balkema & de Haan (1974) Ann. Probab. 2(5):792-804; Pickands (1975) Ann. Statist. 3(1):119-131; Hill (1975) Ann. Statist. 3(5):1163-1174;
Weissman (1978) JASA 73:812-815; Smith (1985) Biometrika 72:67-90; McNeil & Frey (2000) J. Empirical Finance 7(3-4):271-300;
Coles (2001) An Introduction to Statistical Modeling of Extreme Values, Springer; McNeil, Frey & Embrechts (2015) Quantitative Risk Management, rev. ed., Princeton UP;
Kupiec (1995) J. Derivatives 3(2):73-84; Christoffersen (1998) Int. Econ. Rev. 39(4):841-862; BCBS (1996) Supervisory framework for the use of backtesting.
