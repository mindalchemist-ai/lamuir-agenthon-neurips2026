# European option finite-difference PDE

Use this reference to assemble and check a finite-difference solver for European vanilla prices and Greeks, including specified cash-dividend events.

Before choosing the time step: backward Euler (eta = 1) has first-order error in dtau, so the discounting of the strike
alone is off by about r^2 T dtau / 2 relative to K exp(-rT), largest at long maturities; Crank-Nicolson (eta = 1/2) is
second order. Use Crank-Nicolson with a Rannacher start (two backward-Euler half steps) unless the task names the
scheme; with backward Euler, refine dtau until the check passes. Check every row of the output, not only a few:

```python
parity = C - P - (S * np.exp(-q * T) - K * np.exp(-r * T))   # one entry per (S, K, T) row of the output table
assert np.abs(parity).max() < tol                            # tol: the accuracy the task states, else about 1e-4 of the price scale
assert np.abs(C - bs_call(S, K, T, r, q, sigma)).max() < tol  # closed form on the same inputs, all maturities
```

Map task quantities to these definitions by meaning and units, not by letter, before the first calculation; recheck when inputs or conventions change.

Explicit task definitions and contract conventions take precedence. If they conflict or are incomplete, identify the ambiguity and state the convention used.

## 1. Shared foundations
Symbols are local. Use S for spot, K for strike, $\sigma$ for annualized decimal volatility, r for the rate, q for continuous yield, and $\tau =T_{\mathrm{expiry}}-t$ for remaining time in years. European payoff is $g(S); V(S,0)=g(S)$. This entry assumes constant coefficients and payment at expiry. For closed-form comparisons use Black-Scholes under identical inputs. For American exercise, impose the early-exercise constraint using an LCP solver or another justified American method; a plain European linear solve alone is insufficient. Require $K>0$ and $\sigma \ge 0$; the grid formulas describe the diffusion case $\sigma >0$. Zero volatility is a first-order transport limit and needs suitable deterministic or monotone handling.

## 2. Space operator and time stepping
In remaining time:
**European pricing PDE in remaining time**

$$
V_{\tau} = L V = \sigma ^{2}\cdot S^{2}\cdot V_{\mathrm{SS}}/2 + (r-q)\cdot S\cdot V_{S} - r\cdot V.
$$

On a uniform spot grid $S_{i}=i\cdot h$, interior row i has
**Lower-diagonal operator coefficient**

$$
\mathrm{lower}_{i} = \sigma ^{2}\cdot S_{i}^{2}/(2\cdot h^{2}) - (r-q)\cdot S_{i}/(2\cdot h)
$$

**Main-diagonal operator coefficient**

$$
\operatorname{diag}_{i} = -\sigma ^{2}\cdot S_{i}^{2}/h^{2}-r
$$

**Upper-diagonal operator coefficient**

$$
\mathrm{upper}_{i} = \sigma ^{2}\cdot S_{i}^{2}/(2\cdot h^{2}) + (r-q)\cdot S_{i}/(2\cdot h).
$$

**Apply the assembled spatial operator**

Thus $(LV)_i=\mathrm{lower}_i V_{i-1}+\operatorname{diag}_i V_i+\mathrm{upper}_i V_{i+1}$. The coefficient belongs to row i, not to the neighboring value's index.

For a step dtau and theta-method weight $\eta$:
**One theta-method time step with boundary contributions**

$$
(I-\eta \cdot \mathrm{dtau}\cdot L_{\mathrm{II}})\cdot V_{\mathrm{new}} = (I+(1-\eta )\cdot \mathrm{dtau}\cdot L_{\mathrm{II}})\cdot V_{\mathrm{old}} + \mathrm{dtau}\cdot ((1-\eta )\cdot b_{\mathrm{old}}+\eta \cdot b_{\mathrm{new}}).
$$

$L_{\mathrm{II}}$ contains interior-to-interior coefficients. The first component of b is $\mathrm{lower}_1V_0$ and the last is $\mathrm{upper}_{M-1}V_M$; other components are zero (add both terms if only one interior node exists). Weight old and new boundary contributions by $(1-\eta)$ and $\eta$ respectively; for backward Euler the old contribution is zero. $\eta =1$ gives backward Euler; $\eta =1/2$ gives Crank-Nicolson. Solve the tridiagonal system rather than explicitly inverting it. Nonsmooth payoffs can cause CN oscillations: two backward-Euler half steps for the first full step are a common Rannacher startup; document the schedule. Central differencing can lose monotonicity when drift dominates diffusion; refine or use a justified monotone discretization.

## 3. Boundaries and Greeks
Boundaries use remaining time $\tau$.
**Call boundary values**

$$
\;\text{Call}\;: V(0,\tau )=0; V(S_{\mathrm{max}},\tau ) \approx  S_{\mathrm{max}}\cdot \exp (-q\cdot \tau )-K\cdot \exp (-r\cdot \tau ).
$$

**Put boundary values**

$$
\;\text{Put}\;: V(0,\tau )=K\cdot \exp (-r\cdot \tau ); V(S_{\mathrm{max}},\tau ) \approx  0.
$$

The large-spot approximations require a sufficiently distant boundary; enlarge $S_{\mathrm{max}}$ to test truncation error. Negative rates are allowed and can make the put's left boundary exceed K.

**$\Delta$ and $\Gamma$ on the stock grid**

At interior nodes $\Delta\approx(V_{i+1}-V_{i-1})/(2h)$, $\Gamma\approx(V_{i+1}-2V_i+V_{i-1})/h^2$. Calendar $\Theta =-V_{\tau}$, and may be computed from the PDE operator or a time difference with the correct sign. Using the same operator for Theta and the PDE residual makes that residual a consistency check, not independent validation.

Vega/Rho from bumped PDE solves require identical domains, grids and interpolation conventions. If reporting values off-grid, state the interpolation; differentiating a piecewise-linear interpolant twice does not give a useful Gamma.

## 4. Events and convergence
Between discrete dividend events use the PDE above; do not also include those same dividends in q. For a deterministic cash dividend $D_{\mathrm{cash}}$, assumed ex-dividend and paid at calendar time $t_{d}$, the backward event map is $V_{\mathrm{before}}(S)=V_{\mathrm{after}}(\max (S-D_{\mathrm{cash}},0))$ under this specified stock-jump convention. Interpolate from the post-event grid; do not reverse the sign. This convention needs explicit treatment near zero and is not the continuous-yield model. Align time steps with events; do not smooth a discrete dividend across time.

Refine space and time separately and enlarge the domain. Compare prices AND Greeks with an independent closed form when applicable. Test puts, calls, nonzero q, non-ATM inputs, and expiry kinks. A residual near zero alone does not establish accuracy. Calendar t and remaining $\tau$ are different coordinates; their relation is $\tau =T_{\mathrm{expiry}}-t$.

## Efficient linear time stepping

A one-dimensional nearest-neighbor spatial stencil gives a tridiagonal interior system. Store three diagonals and form the right-hand side using adjacent vector slices, including the appropriate boundary terms. Dense construction and dense factorization discard this structure.

For row coefficients $a_i,d_i,c_i$, SciPy's three-row band storage places the upper entry $c_i$ in column $i+1$, the diagonal $d_i$ in column $i$, and the lower entry $a_i$ in column $i-1$. The two unused corners are zero. A small-system comparison to a dense solve tests this packing.

When the operator, grid, step length and scheme weight are unchanged, the left matrix can be factored once and used for multiple right-hand sides. A new coefficient regime or a different step length may require new factors. Repeated calls to `solve_banded` do not promise cached factors. Thomas elimination needs safe pivots; it does not justify ignoring a near-zero pivot. These are linear European solves, not an obstacle solver.

Source: [SciPy solve_banded](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html).

## 5. References
Crank and Nicolson (1947), A practical method for numerical evaluation of solutions of partial differential equations of the heat-conduction type. Black and Scholes (1973). The operator above follows directly by central differencing the stated PDE.
