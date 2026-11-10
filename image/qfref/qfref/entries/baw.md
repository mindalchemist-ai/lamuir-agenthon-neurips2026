# American options: Barone-Adesi & Whaley (1987) quadratic approximation

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Critical prices: what to report and how to check them

| situation | critical price | option value |
|---|---|---|
| boundary equation solved, normalized residual below tol | the root ($S^{*}>X$ call, $0<S^{**}<X$ put) | BAW formula below |
| call with $r\ge0$ and $b\ge r$ | $+\infty$: no early exercise | European call |
| root finder raised, hit its cap, or returned a value on the wrong side of X | none yet: the solve is unfinished; fix the solver (seed, cap, residual-based stop) instead of returning a placeholder such as X | none yet |

Checks on any table of critical prices, before writing files:
1. Side: every call $S^{*}>X$ and every put $0<S^{**}<X$.
2. Homogeneity: for the same T, r, b and $\sigma$, $S^{*}/X$ (and $S^{**}/X$) is the same number for every strike. One row whose ratio differs from the others is a failed solve, not a feature.
3. Exercise region: where spot is at or above $S^{*}$ (call) or at or below $S^{**}$ (put) the value is exactly intrinsic; a value above intrinsic there means the reported boundary is wrong.
4. Residual: $\vert \mathrm{LHS}-\mathrm{RHS}\vert/X$ is below tolerance at every reported critical price.

## Model and assumptions
- Underlying S follows GBM under the risk-neutral measure with constant vol $\sigma$, constant rate r and constant
  cost of carry b. Option can be exercised at any time up to T. No cash dividends, no smile.
- Idea: the early-exercise premium $e(S,T) = \;\text{American}\; - \;\text{European}\;$ obeys the Black-Scholes PDE. BAW write it as
  K(T) f(S), with $K(T) = 1 - e^{-rT}$, then drop one term. That leaves an ODE with power solutions S^q.
  The result is an **approximation**, not an exact price.

At $r=0$, evaluate the root-formula ratio by its limit $M/K=2/(\sigma^2T)$; do not compute $0/0$. For small nonzero $rT$, evaluate $K=1-e^{-rT}$ with `-expm1(-r*T)`. This changes numerical evaluation, not the BAW approximation.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| $S$ | spot (or futures price F when $b = 0$) | price |
| $X$ | strike | price |
| $T$ | time to expiry (years, day count from the task) | years |
| $r$ | continuously compounded risk-free rate; 5% is `0.05` | $1/\mathrm{year}$ |
| $b$ | cost of carry, continuous: stock with dividend yield q: $b = r - q$; non-dividend stock: $b = r$; futures: $b = 0; \mathrm{FX}$: $b = r_{\mathrm{dom}} - r_{\mathrm{for}}$ | $1/\mathrm{year}$ |
| $\sigma$ | annual lognormal vol; 20% is `0.20` | $1/\sqrt{\mathrm{year}}$ |

## European pieces (generalized Black-Scholes)

$$
\begin{gathered}
\mathrm{d1}(S) = [\ln (S/X) + (b + \sigma ^{2}/2) T] / (\sigma  \sqrt{T}),   \mathrm{d2} = \mathrm{d1} - \sigma  \sqrt{T} \\
c(S) = S e^{(b-r)T} N(\mathrm{d1}) - X e^{-rT} N(\mathrm{d2}) \\
p(S) = X e^{-rT} N(-\mathrm{d2}) - S e^{(b-r)T} N(-\mathrm{d1})
\end{gathered}
$$

N = standard normal CDF, n = standard normal density.

## Coefficients

$$
\begin{gathered}
M = 2r / \sigma ^{2},   \mathrm{Nb} = 2b / \sigma ^{2},   K = 1 - e^{-rT} \\
\mathrm{q1} = [-(\mathrm{Nb} - 1) - \sqrt{(\mathrm{Nb} - 1)^{2} + 4M/K}] / 2\quad (\mathrm{q1} < 0, \;\text{put}\;) \\
\mathrm{q2} = [-(\mathrm{Nb} - 1) + \sqrt{(\mathrm{Nb} - 1)^{2} + 4M/K}] / 2\quad (\mathrm{q2} > 0, \;\text{call}\;)
\end{gathered}
$$

(The paper calls Nb just "N"; it is not the normal CDF.)

## Call
- **For $r\ge0$ and $b\ge r$, the American call has no early-exercise premium and equals its European value.**
- **If $r\ge0$ and $b \ge  r$: the American call is never exercised early; price = European call c(S). Stop.** (Negative rates need their own analysis.)
- Otherwise, critical price $S^{*} > X$ solves  $S^{*} - X = c(S^{*}) + [1 - e^{(b-r)T} N(\mathrm{d1}(S^{*}))] S^{*}/\mathrm{q2}$

$$
\mathrm{A2} = (S^{*}/\mathrm{q2}) [1 - e^{(b-r)T} N(\mathrm{d1}(S^{*}))]\quad (> 0)
$$

When $S < S^{*}$:

$$
C = c(S) + \mathrm{A2} (S/S^{*})^{\mathrm{q2}}
$$

When $S \ge  S^{*}$:

$$
C = S - X
$$

Early-exercise premium:

$$
\mathrm{A2} (S/S^{*})^{\mathrm{q2}}
$$

## Put
- Critical price $S^{**} < X$ solves  $X - S^{**} = p(S^{**}) - [1 - e^{(b-r)T} N(-\mathrm{d1}(S^{**}))] S^{**}/\mathrm{q1}$

$$
\mathrm{A1} = -(S^{**}/\mathrm{q1}) [1 - e^{(b-r)T} N(-\mathrm{d1}(S^{**}))]\quad (> 0 \mathrm{because} \mathrm{q1} < 0)
$$

When $S > S^{**}$:

$$
\operatorname{P} = p(S) + \mathrm{A1} (S/S^{**})^{\mathrm{q1}}
$$

When $S \le  S^{**}$:

$$
\operatorname{P} = X - S
$$

Early-exercise premium:

$$
\mathrm{A1} (S/S^{**})^{\mathrm{q1}}
$$

## Newton iteration for the critical price (BAW Section II)

When computing either critical price → start this iteration from the seed below, cap the iterations, and check that each step stays in the price domain and the final normalized residual is small → once a version has produced a finite, checked trial value, change it locally rather than replacing it. If a Newton step leaves the domain, damp the step or switch to a bracketing method on the same residual with finite endpoints of opposite sign; never substitute an artificial residual value, never widen the bracket without bound, and keep every logarithm's argument positive.
Call, $i = 1, 2$, ...: $\mathrm{RHS}(\mathrm{Si}) = c(\mathrm{Si}) + [1 - e^{(b-r)T} N(\mathrm{d1}(\mathrm{Si}))] \mathrm{Si}/\mathrm{q2}$

$$
\begin{gathered}
\mathrm{slope} \mathrm{bi} = e^{(b-r)T} N(\mathrm{d1}(\mathrm{Si})) (1 - 1/\mathrm{q2}) + [1 - e^{(b-r)T} n(\mathrm{d1}(\mathrm{Si})) / (\sigma  \sqrt{T})] / \mathrm{q2} \\
S_{i+1} = [X + \mathrm{RHS}(\mathrm{Si}) - \mathrm{bi} \mathrm{Si}] / (1 - \mathrm{bi})
\end{gathered}
$$

Put: $\mathrm{RHS}(\mathrm{Si}) = p(\mathrm{Si}) - [1 - e^{(b-r)T} N(-\mathrm{d1}(\mathrm{Si}))] \mathrm{Si}/\mathrm{q1}$

$$
\begin{gathered}
\mathrm{slope} \mathrm{bi} = -e^{(b-r)T} N(-\mathrm{d1}(\mathrm{Si})) (1 - 1/\mathrm{q1}) - [1 + e^{(b-r)T} n(\mathrm{d1}(\mathrm{Si})) / (\sigma  \sqrt{T})] / \mathrm{q1} \\
S_{i+1} = [X - \mathrm{RHS}(\mathrm{Si}) + \mathrm{bi} \mathrm{Si}] / (1 + \mathrm{bi})
\end{gathered}
$$

Stop when $\vert \mathrm{LHS}(\mathrm{Si}) - \mathrm{RHS}(\mathrm{Si})\vert  / X < \mathrm{tol}$(paper: 1e-5; a tighter tol such as 1e-8 costs nothing). $\mathrm{LHS} = \mathrm{Si} - X$(call), X - Si (put).
Seeds (or simply $S_i=X$): with q2inf, q1inf = the q2, q1 formulas with 4M in place of 4M/K. If a seed denominator is zero or numerically singular, use $S_i=X$ instead of evaluating that seed; this includes a zero infinite-horizon root at $r=0$. Otherwise:

$$
\begin{gathered}
\;\text{call}\;: \mathrm{Sinf} = X / (1 - 1/\mathrm{q2inf}),  \mathrm{h2} = -(bT + 2 \sigma  \sqrt{T}) X / (\mathrm{Sinf} - X),  \mathrm{S1} = X + (\mathrm{Sinf} - X)(1 - e^{\mathrm{h2}}) \\
\;\text{put}\;:  \mathrm{Sinf} = X / (1 - 1/\mathrm{q1inf}),  \mathrm{h1} = (bT - 2 \sigma  \sqrt{T}) X / (X - \mathrm{Sinf}),  \mathrm{S1} = \mathrm{Sinf} + (X - \mathrm{Sinf}) e^{\mathrm{h1}}
\end{gathered}
$$

$S^{*}$ scales with X: $S^{*}(\mathrm{X2}) = S^{*}(\mathrm{X1}) \mathrm{X2}/\mathrm{X1}$.

## Variants and common mistakes
- Futures options (Black-76 world): use F for S and $b = 0$. Non-dividend stock: $b=r$ (call equals European for nonnegative rates; put approximation follows MacMillan 1986).
  Stock index / dividend yield q: $b = r - q$. FX: $b = r_{d} - r_{f}$. Do not put q where b belongs.
- The q1, q2 used in the price and the iteration must use **$4M/K$ with $K=1-e^{-rT}$**; the 4M-without-K versions
  belong to the seed only (a bad seed only costs iterations; the wrong q changes the price).
- d1 inside A1, A2 and the iteration is evaluated at the critical price, not at spot.
- Below $S^{**}$ (put) / above $S^{*}$ (call) return intrinsic value; do not add the premium there.
- At $r=0$, $M/K$ tends to $2/(\sigma^2T)$. With nonnegative continuous dividend yield, the American put has no early-exercise premium at zero interest. Do not extend this conclusion to arbitrary negative carry or dividend assumptions.
- BAW does not satisfy the American put-call symmetry $C(S,X,r,b) = \operatorname{P}(X,S,r-b,-b)$ exactly
  (the approximation errors can differ): if the task asks for BAW put, apply the put formulas, not symmetry.
- Other American approximations (e.g. Bjerksund-Stensland) are different formulas; use them only if the task names them.
- When $b \ge r$ the American call is never exercised early: return the European call and skip the critical-price
  iteration, whose Newton step divides by a vanishing slope there.

## Applicability and known limits
- Sanity: result >= $\max ( \;\text{European}\;, \mathrm{intrinsic} )$. Value matching and smooth pasting hold at $S^{*}$ by construction.
- BAW is an approximation, not an exact American value or boundary. Accuracy depends on maturity, volatility, rates and carry; matching its own boundary equations does not establish agreement with a converged obstacle solver. No universal numerical-error bound is asserted here.
- The usual positive-rate BAW branches and no-exercise shortcuts require their carry assumptions. Negative rates or negative dividend yields require a separate domain analysis; a non-dividend call equals its European value under the usual nonnegative-rate assumptions.
- Cash dividends, time-varying $r$ or $\sigma$, barriers or Bermudan exercise are outside the model.

## Sources
G. Barone-Adesi and R. E. Whaley (1987), "Efficient Analytic Approximation of American Option Values",
Journal of Finance 42(2), 301-320 (eqs. 13, 19-20, 24-25, 26-33). L. W. MacMillan (1986), "Analytic Approximation for the
American Put Option", Advances in Futures and Options Research 1, 119-139 (as cited by BAW).
