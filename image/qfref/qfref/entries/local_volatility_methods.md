# Local volatility from an implied-volatility surface

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

## Topic: Local variance from total variance (Gatheral form)

**Purpose:** Compute the local variance $\sigma_{loc}^2(k,T)$ from a smooth implied total variance surface $w(k,T)=\sigma_{imp}^2(k,T)\,T$.

**When to use:** The implied volatility surface is available as a smooth function of log-moneyness and maturity (for example a fitted parametric slice per maturity, interpolated in $T$). Use the call-price form instead when only option prices are available.

**How to implement:** With $k=\ln(K/F_T)$, $F_T$ the forward for maturity $T$, and derivatives taken with respect to $k$ at fixed $T$:

$$g(k)=\Big(1-\frac{k\,w_k}{2w}\Big)^2-\frac{w_k^2}{4}\Big(\frac1w+\frac14\Big)+\frac{w_{kk}}{2},\qquad \sigma_{loc}^2(k,T)=\frac{w_T}{g(k)}.$$

Take $w_T$ at fixed $k$. Compute $w_k$, $w_{kk}$ analytically from the parametric slice when possible, otherwise by central differences on a fine grid in $k$.

**Implementation tips:**

1. Positive local variance is not something to enforce afterwards: it follows from two no-arbitrage properties of the input surface. Check both before differentiating. Calendar: $w(k,T)$ is non-decreasing in $T$ at fixed $k$, which makes $w_T\ge0$. Butterfly: each maturity slice satisfies the convexity condition that keeps $g(k)>0$ (for a parametric slice, verify it on the fitted parameters, not only on the quoted strikes).
2. Compute $w_T$ at fixed $k$ from the fitted parametric slices, not from finite differences on a sparse maturity grid: a central difference across widely spaced maturities, or a one-sided difference at the first and last maturity, is where a spurious negative $w_T$ comes from. Extrapolate $w$ linearly in $T$ at fixed $k$ beyond the last maturity, and evaluate at small positive $T$, never $T=0$.
3. If local variance is still non-positive at a node, repair the surface (re-fit the slice under the no-arbitrage constraints, or widen the $k$ grid so the wings come from the fit rather than extrapolation) instead of clipping the result. Print the unclipped minimum of $g(k)$ and $w_T$ over the grid and report which node fails.

**Limitations and cautions:**

1. Use $k=\ln(K/F_T)$ in the formula, not the strike $K$ and not $K/S_0$.
2. Derivatives are with respect to $k$, not $K$; $w_T$ is at fixed $k$, not fixed $K$.
3. Clipping $g$ or the variance to a small positive number hides a wrong formula; look at the unclipped values first.
4. A negative $g$ or $w_T$ means arbitrage in the surface (calendar or butterfly) or a numerical derivative on a coarse grid.

**Double check:**

1. For a flat surface ($w=\sigma^2T$ with constant $\sigma$), $\sigma_{loc}=\sigma$ at every point.
2. Near the money, $\sigma_{loc}$ is of the same order as $\sigma_{imp}$; a ratio far from 1 at all points points to a formula or unit error.
3. Print the unclipped minimum of $g$ and $w_T$ before clipping.

## Topic: Local variance from call prices (Dupire form)

**Purpose:** Compute the local variance directly from call prices $C(K,T)$.

**When to use:** Option prices (or prices from a smooth pricing model) are the primary input and a total variance surface is not available.

**How to implement:** With risk-free rate $r$ and dividend yield $q$,

$$\sigma_{loc}^2(K,T)=\frac{C_T+(r-q)\,K\,C_K+q\,C}{\tfrac12 K^2\,C_{KK}}.$$

Compute $C_T$, $C_K$, $C_{KK}$ analytically from a smooth model, or by finite differences on a smooth price surface.

**Limitations and cautions:**

1. Finite differences of noisy market prices give unstable $C_{KK}$; smooth the surface first.
2. $C_{KK}$ near zero (deep in or out of the money) makes the ratio explode; restrict to the region where $C_{KK}$ is well above numerical noise.
3. The dividend and rate terms must match the convention used to build the prices.

**Double check:**

1. The result is positive wherever the prices are arbitrage-free.
2. Re-pricing a European option with the resulting local volatility surface reproduces the input prices within the numerical error.
