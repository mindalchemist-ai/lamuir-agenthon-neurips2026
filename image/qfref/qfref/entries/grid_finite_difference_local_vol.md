# Finite-difference derivatives on a price grid and Dupire local volatility from call prices

The task description inside <task_instructions> takes priority over this card: where it names a scheme, a threshold, a floor or an output shape, follow the task description.

## Topic: Finite-difference derivatives on a grid

**Purpose:** Approximate first and second derivatives of values known only at grid nodes (prices on a strike-by-maturity grid, a curve on tenor nodes).

**When to use:** The task gives or builds a table of values on a discrete grid and asks for sensitivities, densities, local volatility or any other quantity built from derivatives of that table.

**How to implement:** Nodes $x_0<\dots<x_{n-1}$, values $f_0,\dots,f_{n-1}$.

First derivative:

1. At an interior node, the central difference $f'_i=\dfrac{f_{i+1}-f_{i-1}}{x_{i+1}-x_{i-1}}$.
2. At the first node, the forward difference $f'_0=\dfrac{f_1-f_0}{x_1-x_0}$; at the last node, the backward difference $f'_{n-1}=\dfrac{f_{n-1}-f_{n-2}}{x_{n-1}-x_{n-2}}$.
3. `np.gradient` with the coordinate array and `edge_order=1` computes exactly these three rules; with a scalar spacing it assumes a uniform grid.

Second derivative, three-point central formula, at interior nodes only:

1. Uniform spacing $h$: $f''_i=\dfrac{f_{i+1}-2f_i+f_{i-1}}{h^2}$.
2. Uneven spacing, $h_-=x_i-x_{i-1}$ and $h_+=x_{i+1}-x_i$: $f''_i=\dfrac{2\,\big(h_-f_{i+1}-(h_-+h_+)f_i+h_+f_{i-1}\big)}{h_-h_+(h_-+h_+)}$.
3. The two end nodes have no central second difference; leave them undefined and report only the interior nodes, unless the task states a rule for the ends.
4. On a two-dimensional table, apply the formula along one axis for every column of the other axis at once (array slicing along that axis), not cell by cell.

**Implementation tips:**

1. When a task asks for central differences inside the grid and one-sided ones on its end nodes, the second derivative is the three-point formula above, written out from neighbouring values.
2. Applying `np.gradient` to the output of `np.gradient` is a different, wider stencil, $\dfrac{f_{i+2}-2f_i+f_{i-2}}{(2h)^2}$, which skips the immediate neighbours. Use it only when the task names that tool for the second derivative.

**Limitations and cautions:**

1. The wide and the three-point stencils give materially different numbers where curvature changes quickly (near the money, at short maturity); they are not interchangeable.
2. A second difference amplifies noise in the values by about $1/h^2$. On noisy market quotes, smooth or fit first when the task allows it; on a smooth model-generated grid, use the values as given.
3. Sort the grid by its numeric coordinates before differencing; labels sorted as text put neighbours in the wrong order.

**Double check:**

1. On a quadratic test function $f(x)=ax^2+bx+c$, the three-point formula returns $2a$ at every interior node, on uniform and uneven grids.
2. Print the largest difference between the three-point result and the nested-gradient result; it is not zero, which confirms which stencil was used.

## Topic: Dupire local volatility from a call-price grid

**Purpose:** Compute the local volatility $\sigma_{loc}(K,T)$ implied by European call prices on a strike-by-maturity grid.

**When to use:** Call prices are given or computed (from a model or from quotes) on a grid, and the task asks for a local-volatility surface by finite differences. When a smooth implied total-variance surface is the input instead, use the total-variance (Gatheral) form.

**How to implement:** With continuous rate $r$ and dividend yield $q$,

$$\sigma_{loc}^2(K,T)=\frac{\dfrac{\partial C}{\partial T}+(r-q)K\dfrac{\partial C}{\partial K}+qC}{\tfrac12K^2\dfrac{\partial^2C}{\partial K^2}},$$

which with $q=0$ has numerator $\dfrac{\partial C}{\partial T}+rK\dfrac{\partial C}{\partial K}$.

What each part means:

1. Denominator: by the Breeden-Litzenberger identity, $\dfrac{\partial^2C}{\partial K^2}=e^{-rT}p(K)$, where $p$ is the risk-neutral density of $S_T$. It must be positive; it is close to zero far from the money, where the density is small, and that is where the ratio becomes unstable.
2. Numerator: the time value gained by extending the maturity, adjusted for the forward drift and the carry. It must be non-negative; a negative value means calendar arbitrage in the prices.

Steps:

1. Each derivative uses the scheme the task states; without one, central differences in the interior and one-sided ones on the end nodes for the first derivatives, and the three-point formula of the previous topic for $\partial^2C/\partial K^2$.
2. Evaluate the ratio at each node where $\partial^2C/\partial K^2$ exists.
3. Apply the task's rules for a near-zero denominator, for a negative or tiny variance, and for the square root, in the order the task gives them.

**Implementation tips:**

1. Keep strikes on one axis and maturities on the other throughout, and derive every derivative from the same price grid that is written to the price file.
2. Convert puts to calls with put-call parity before differencing.

**Limitations and cautions:**

1. A negative $\partial^2C/\partial K^2$ (butterfly arbitrage) or a negative numerator (calendar arbitrage) usually comes from an inaccurate price; check the prices against their no-arbitrage bounds before differencing rather than forcing the result positive.
2. At the first and last maturity the time derivative is one-sided and less accurate.
3. When noise drives the denominator toward zero or the variance negative on market data, regularize the price surface (smoothing, a Tikhonov penalty, or a parametric fit) where the task permits it.

**Double check:**

1. The reported surface has the requested orientation and only the nodes where all derivatives are defined.
2. Near the money, $\sigma_{loc}$ is of the same order as the implied volatility at that maturity; under a stochastic-volatility model the short-maturity at-the-money local volatility is close to the square root of the initial variance.
3. Every reported value is finite and positive except where the task's rule sets a missing value.
4. Print the minimum and maximum by maturity; one column far below its neighbours points to the second-difference stencil or to a bad price in that column.
