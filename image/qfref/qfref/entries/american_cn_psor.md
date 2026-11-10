# American and European options: finite differences, exercise and dividends

Use this document to choose and assemble finite-difference calculations for one-asset European or American vanilla options, including known stock-price dividend jumps. It covers grid coefficients, time stepping, exercise constraints, event-side values and numerical checks. Select the applicable blocks below.

Before writing a V(S, t) grid table with an `S` column and one column per time: each row is one stock node and each
column one time node, so a row holds V at that S across time. A solver array is often stored as V[time, space]; then
the table is its transpose. Read the file back and check it:

```python
g = pd.read_csv(path).set_index("S")                     # rows: stock nodes; columns: time values
t0 = g.columns[np.argmin(np.abs(g.columns.astype(float)))]
assert np.isclose(np.interp(S0, g.index.to_numpy(float), g[t0].to_numpy(float)), price, atol=0.05 * price)   # V(S0, t=0) is the reported price
```

A coarse / fine grid pair (for convergence or Richardson extrapolation) differs only by discretization error, a small
fraction of the price. A large gap means one run reused the other grid's state: every helper takes the grid it prices
on (its own S array, spacing and time steps), and dividend or event steps are recomputed for each grid's time step.
Each grid's step sizes ($\Delta t$, $\Delta S$) are computed inside the pricing function from that call's own step counts; a function that reads a step size defined outside it prices every grid with the same step. Identical coarse and fine values are a bug too: the coarse run read the fine grid's sizes from the session. After fixing either case, rewrite every output file that holds those values, not only the summary.

```python
assert abs(price_fine - price_coarse) < 0.01 * abs(price_fine)   # a bigger gap is a bug in the coarse run, not convergence
assert price_fine != price_coarse                                 # identical values mean both runs used the same grid
```

## Contents

1. Shared foundations and method selection
2. Time direction
3. Grid and row coefficients
4. Boundary values
5. Time stepping and exercise solver
6. Dividend events
7. Valuation and checks
8. References

## 1. Shared foundations and method selection

Read these definitions once; revisit them if the contract changes. Symbols are local. Map task inputs by definition. Explicit contract and output conventions take precedence; identify conflicting conventions rather than silently mixing them. Formula blocks are mathematical notation, not executable code.

Use this reference when one stock follows a constant-parameter Black-Scholes diffusion between any specified dividend events, and the requested method is a finite-difference valuation. S is stock price, S0 current spot, X positive strike, T remaining lifetime at valuation, t elapsed calendar time since valuation, r the continuously compounded rate, q continuous yield, and $\sigma$ positive annualized decimal volatility. Times are years. Rates r and yields q are annual decimals: 5% is 0.05. $\mathrm{S0}>0$. At expiry return the payoff. Zero volatility needs a deterministic optimal-exercise calculation or a suitable first-order discretization, not division by $\sigma$. Path dependence, stochastic volatility and multiple assets need additional state variables and are outside this one-dimensional entry.

W is standard Brownian motion under the risk-neutral measure; dt and dW are time and Brownian increments.

**Risk-neutral stock dynamics**

$$
\mathrm{d}S = (r-q)\cdot S\cdot \mathrm{d}t + \sigma \cdot S\cdot \mathrm{d}W
$$

**Call exercise payoff**

$$
g_{\mathrm{call}}(S) = \max (S-X,0)
$$

**Put exercise payoff**

$$
g_{\mathrm{put}}(S) = \max (X-S,0)
$$

There are separate decisions, not one global branch: exercise rights select the linear or constrained solve; the chosen grid selects its coefficients; dividend terms select event handling. Apply one applicable branch within each decision and combine the resulting blocks. Keep the grid and event conventions fixed throughout a solve.

## 2. Time direction

Use this block for every backward valuation from expiry. All remaining-time evolution below runs toward valuation, not toward expiry. In V(S,$\tau$), the second argument is remaining time; thus V(S,0) below is the expiry payoff, not the value at calendar $t=0$.

V is option value, g the selected payoff, and L the spatial pricing operator; $V_{S}$, $V_{\mathrm{SS}}$ and $V_{\tau}$ denote the indicated first/second partial derivatives.

**Convert calendar time to remaining time**

$$
\tau  = T-t
$$

**Terminal payoff condition**

$$
V(S,0) = g(S)
$$

**Black–Scholes pricing operator**

$$
L\cdot V = \sigma ^{2}\cdot S^{2}\cdot V_{\mathrm{SS}}/2 + (r-q)\cdot S\cdot V_{S} - r\cdot V
$$

If exercise is allowed only at expiry, evolve the European equation. If it is allowed continuously before expiry, impose the American obstacle.

**European pricing equation**

$$
\;\text{European}\;: V_{\tau} = L\cdot V
$$

**American exercise complementarity conditions**

$$
\;\text{American}\;: V_{\tau}-L\cdot V \ge  0; V-g \ge  0; (V_{\tau}-L\cdot V)\cdot (V-g) = 0
$$

The payoff layer has $\tau =0$ and calendar $t=T$; the valuation layer has $\tau =T$ and $t=0$. For coefficients changing by known time intervals, align steps with changes and use the operator of each interval. Do not reverse time labels without moving their value vectors.

## 3. Grid and row coefficients

Use the grid explicitly required by the task. Otherwise a uniform log-price grid is often useful; a uniform price grid starting at zero includes an exact zero-stock node. M denotes space intervals, N the nominal time intervals. Widen the domain to include S0, X and dividend shifts, and test its boundaries. Suggested domains are starting points, not accuracy guarantees.

Grid notation: i indexes nodes/rows; $S_{i}$ and $V_{i}$ are nodal stock and option values. $l_{i}$/$c_{i}$/$u_{i}$ are lower/main/upper row coefficients. Grid dS is fixed spacing, not the stock-process increment; $S_{\mathrm{max}}$ is the upper endpoint.

### Uniform log-price nodes

Use this block only when the state coordinate is $x=\ln (S)$; the lower stock node is then positive. A starting range is $\ln (\mathrm{S0})$ plus/minus $5-6 \sigma  \sqrt{T}$, expanded as needed. Place S0 on a node or interpolate consistently.

dx is log-grid spacing and $x_{\mathrm{min}}$ its lower endpoint; a multiplies $V_{\mathrm{xx}}$ in L, while $\mu$ is log-price drift. $V_{x}$/$V_{\mathrm{xx}}$ are log-price derivatives.

**Construct log-price grid nodes**

$$
x_{i} = x_{\mathrm{min}}+i\cdot \mathrm{d}x; S_{i}=\exp (x_{i})
$$

**Pricing operator in log coordinates**

$$
\begin{gathered}
L\cdot V = a\cdot V_{\mathrm{xx}} + \mu \cdot V_{x} - r\cdot V \\
a = \sigma ^{2}/2; \mu  = r-q-\sigma ^{2}/2
\end{gathered}
$$

**Lower, main and upper log-grid coefficients**

$$
\begin{gathered}
l_{i} = a/\mathrm{d}x^{2}-\mu /(2\cdot \mathrm{d}x) \\
c_{i} = -2\cdot a/\mathrm{d}x^{2}-r \\
u_{i} = a/\mathrm{d}x^{2}+\mu /(2\cdot \mathrm{d}x)
\end{gathered}
$$

### Uniform stock-price nodes

Use this block only for $S_{i}=i\cdot \mathrm{d}S$, including grid node $S_{0}=0$(distinct from current spot S0). A starting upper bound is 3-5 times X; expand for high volatility, long maturity or large S0.

**Stock-grid operator coefficients**

$$
\begin{gathered}
l_{i} = (\sigma ^{2}\cdot i^{2}-(r-q)\cdot i)/2 \\
c_{i} = -\sigma ^{2}\cdot i^{2}-r \\
u_{i} = (\sigma ^{2}\cdot i^{2}+(r-q)\cdot i)/2
\end{gathered}
$$

For a shifted uniform stock grid $S_{i}=S_{\mathrm{min}}+i\cdot \mathrm{d}S$ with $S_{\mathrm{min}}>0$, the integer i is not $S_i/\mathrm{d}S$. Use $k_{i}=S_{i}/\mathrm{d}S$ in the stock-grid formulas instead:

$S_{\mathrm{min}}$ is the lower stock endpoint; $k_{i}$ is stock measured in grid-spacing units.

**Shifted stock-grid operator coefficients**

$$
\begin{gathered}
k_{i} = S_{i}/\mathrm{d}S \\
l_{i} = (\sigma ^{2}\cdot k_{i}^{2}-(r-q)\cdot k_{i})/2 \\
c_{i} = -\sigma ^{2}\cdot k_{i}^{2}-r \\
u_{i} = (\sigma ^{2}\cdot k_{i}^{2}+(r-q)\cdot k_{i})/2
\end{gathered}
$$

These shifted-grid formulas still assume constant spacing dS; nonuniform grids need different stencils. The lower node is positive, so use the positive-boundary treatment in Section 4.

Keep the coordinate array consistent with its stencil. Do not move a single uniform-grid node to S0 while retaining uniform-grid coefficients. Either choose a uniform grid containing S0, interpolate the solution at S0, or derive the coefficients for the actual nonuniform grid. Check the actual spacings, not only the intended dS or dx.

For either grid, all coefficients below belong to row i. Do not shift a coefficient to the neighboring row merely to fit packed array lengths.

**Apply the tridiagonal pricing operator**

$$
(L\cdot V)_{i} = l_{i}\cdot V_{i-1}+c_{i}\cdot V_{i}+u_{i}\cdot V_{i+1}
$$

On a uniform stock grid only, the following polynomial checks expose row-assembly errors at interior nodes. They do not check option boundaries or exercise.

**Polynomial identities for checking operator assembly**

$$
\begin{gathered}
L(1) = -r \\
L(S) = -q\cdot S \\
L(S^{2}) = (\sigma ^{2}+r-2\cdot q)\cdot S^{2}
\end{gathered}
$$

## 4. Boundary values

Use this block after choosing the grid and exercise rights. Assume no payments directly to the option holder before exercise/expiry.

If the lower grid node is exactly zero and stock remains zero afterward, constant r gives:

**European put boundary at zero stock**

$$
\;\text{European}\; \;\text{put}\;: V(0,\tau ) = X\cdot \exp (-r\cdot \tau )
$$

**American put boundary at zero stock**

$$
\;\text{American}\; \;\text{put}\;: V(0,\tau ) = \max (X,X\cdot \exp (-r\cdot \tau ))
$$

**Call boundary at zero stock**

$$
\;\text{Either}\; \;\text{call}\;: V(0,\tau ) = 0
$$

If the lower stock node is positive (including a log grid), these are not its exact boundary values. Use a justified asymptote and move the boundary outward to check sensitivity.

At a sufficiently high stock boundary, for a European contract with continuous yield and no future cash dividend, use the large-stock asymptotes:

**European call far-field boundary**

$$
\;\text{Call}\;: V(S_{\mathrm{max}},\tau ) \approx  S_{\mathrm{max}}\cdot \exp (-q\cdot \tau )-X\cdot \exp (-r\cdot \tau )
$$

**European put far-field boundary**

$$
\;\text{Put}\;: V(S_{\mathrm{max}},\tau ) \approx  0
$$

American boundaries must also respect immediate exercise. The maximum of intrinsic and the European asymptote is a common truncation approximation, not an exact general American boundary. Future cash dividends and negative rates require compatible boundary treatment. In particular, an American put at zero need not equal X when $r<0$. A call/put label alone does not determine the boundary.

### High-stock boundary with future cash dividends

Use this block for positive deterministic cash drops at known dates strictly before expiry. It is a large-stock truncation approximation: the stock must be sufficiently far from zero and the strike, so the cash cap and payoff kink are negligible. Check sensitivity to the upper boundary. It does not replace the interior dividend maps.

At calendar time t, let J(t) contain dividends still to occur. Immediately before an event include its payment in J; immediately after it remove that payment. For a European call with constant r and q:

$D_{j}$/$t_{j}$ are dividend j's cash amount/calendar date. $B_{\operatorname{E},\mathrm{call}}$/$B_{\operatorname{E},\mathrm{put}}$ are European upper-domain values; $\mathrm{cash}_{\mathrm{adjustment}}$ corrects the call boundary for pending stock distributions.

**Discounted adjustment for pending cash dividends**

$$
\mathrm{cash}_{\mathrm{adjustment}}(t)=\sum_{j\in J(t)}D_j\exp(-r(t_j-t)-q(T-t_j))
$$

**European call far-field boundary with cash dividends**

$$
B_{\operatorname{E},\mathrm{call}}(t) = S_{\mathrm{max}}\cdot \exp (-q\cdot (T-t)) - X\cdot \exp (-r\cdot (T-t)) - \mathrm{cash}_{\mathrm{adjustment}}(t)
$$

**European put far-field boundary**

$$
B_{\operatorname{E},\mathrm{put}}(t) \approx  0
$$

The dividend contribution is discounted from its payment date and then carried to expiry at yield q. For $q=0$ this is the present value of remaining dividends. Recompute boundaries for each time layer and event side; do not subtract dividends already paid. If the call expression is materially negative at $S_{\mathrm{max}}$, its deep-in-the-money premise is not met; do not treat it as a valid far-field boundary.

For an American call with $q=0$ and $r\ge 0$, a more complete large-stock boundary allows exercise now, just before any pending cash dividend, or at expiry. Define U to be these candidate exercise times, interpreting each dividend-date candidate as immediately BEFORE that payment:

u is a candidate exercise time; $B_{\mathrm{call},\mathrm{at},u}$ is its discounted affine exercise value, and $B_{A,\mathrm{call}}$/$B_{A,\mathrm{put}}$ are American upper-domain values.

**Affine value of exercise at candidate time u**

$$
B_{\mathrm{call},\mathrm{at},u}(t)=S_{\max}-\sum_{\substack{j:\,\text{pending dividend}\\t_j<u}}D_j\exp(-r(t_j-t))-X\exp(-r(u-t))
$$

**American call far-field exercise envelope**

$$
B_{A,\mathrm{call}}(t) \approx  \max (0, \max _{u \in  U} B_{\mathrm{call},\mathrm{at},u}(t))
$$

**American put far-field boundary**

$$
B_{A,\mathrm{put}}(t) \approx  0
$$

The sum includes only stock cash distributions occurring before the chosen exercise horizon, not the payment being avoided by exercising immediately before it. When t itself is an ex-date, the pending set distinguishes its two sides. Between payments, with $q=0$ and $r\ge 0$, the affine exercise value increases toward the next candidate date; this explains the finite candidate set. With nonzero q or negative r, that argument no longer supplies this candidate set; use a boundary derived for those assumptions. These are far-field approximations, not exact American prices at arbitrary S.

## 5. Time stepping and exercise solver

Use this block between events, once rows and boundaries are defined. Let h be a positive remaining-time step; $\eta =1/2$ is Crank-Nicolson and $\eta =1$ backward Euler. $\eta$ is a numerical weight, not the option Greek $\Theta$. If the loop uses decreasing calendar time, $h=t_{\mathrm{old}}-t_{\mathrm{new}}>0$ is still the positive step in $\tau$; do not use a negative h in these matrices.

I is the identity matrix; L here is the discretized operator matrix, A the implicit matrix, and rhs the right-hand-side vector. Matrix indices specify row/column; old/new specify time layers.

**Implicit time-step matrix**

$$
A = I-\eta \cdot h\cdot L
$$

**Known right-hand side for one time step**

$$
\begin{gathered}
\mathrm{rhs}_{i} = (1+(1-\eta )\cdot h\cdot c_{i})\cdot V_{i,\mathrm{old}} \\
+(1-\eta )\cdot h\cdot l_{i}\cdot V_{i-1,\mathrm{old}} \\
+(1-\eta )\cdot h\cdot u_{i}\cdot V_{i+1,\mathrm{old}}
\end{gathered}
$$

**Lower, main and upper entries of the implicit matrix**

$$
\begin{gathered}
A_{i,i-1} = -\eta \cdot h\cdot l_{i} \\
A_{i,i} = 1-\eta \cdot h\cdot c_{i} \\
A_{i,i+1} = -\eta \cdot h\cdot u_{i}
\end{gathered}
$$

Old boundary values are already included in this full-row rhs. If solving only interior unknowns, add the following new boundary terms. If instead retaining boundary unknowns with identity rows, do not add them again.

$\mathrm{rhs}_{\mathrm{first}}$/$\mathrm{rhs}_{\mathrm{last}}$ are the first/last interior entries; $V_{0,\mathrm{new}}$/$V_{M,\mathrm{new}}$ are new-time endpoint values.

**Insert the new lower-boundary contribution**

$$
\mathrm{rhs}_{\mathrm{first}} += \eta \cdot h\cdot l_{1}\cdot V_{0,\mathrm{new}}
$$

**Insert the new upper-boundary contribution**

$$
\mathrm{rhs}_{\mathrm{last}}  += \eta \cdot h\cdot u_{M-1}\cdot V_{M,\mathrm{new}}
$$

To check a European time step, solve the same small interior system with a dense solver and with the tridiagonal solver, using identical rhs and boundary contributions. Check both agreement and the residual A*V-rhs. This isolates packing/elimination errors from the PDE stencil; polynomial operator checks alone do not test the solver.

### European exercise rights

Use a tridiagonal linear solver for $A\cdot V=\mathrm{rhs}$; do not impose an early-exercise projection. Thomas elimination is appropriate when its pivots are well behaved; avoid explicit matrix inversion.

### Banded storage and repeated time steps

Let the interior system have $n$ unknowns indexed from $0$ to $n-1$. Write its main, lower and upper row coefficients as $d_i$, $\ell_i$ and $u_i$. Here $d_i$ is the main diagonal of the left-hand matrix $A$, not the PDE operator coefficient $c_i$; absent endpoint neighbors have zero coefficients. Its action needs only adjacent slices:

$$
(Ax)_i=\ell_i x_{i-1}+d_i x_i+u_i x_{i+1}.
$$

This is an $O(n)$ operation and storage requirement. A dense matrix uses $O(n^2)$ storage without adding information. Build coefficient arrays over all interior node indices, rather than filling a dense matrix with nested scalar loops. Boundary values belong in the right-hand side under the interior-system convention above.

For SciPy's `solve_banded((1, 1), ab, rhs)`, the three-row packing is indexed by columns, not by the PDE row:

$$
\mathrm{ab}_{0,j}=u_{j-1}\ (j\ge1),\qquad
\mathrm{ab}_{1,j}=d_j,\qquad
\mathrm{ab}_{2,j}=\ell_{j+1}\ (j<n-1).
$$

The two unused corners can be zero. In particular, the first upper coefficient is stored in column $1$, not column $0$. Use the small dense-versus-banded comparison above to test packing separately from the PDE.

If grid, operator coefficients, step length and time-stepping weight stay fixed, the left matrix stays fixed even when payoff data or boundary contributions change. Coefficient arrays and a valid linear factorization can then be reused. Ordinary repeated `solve_banded` calls solve each supplied system; do not assume they cache a factorization. An explicit reusable factorization must handle its own pivots and any overwritten working arrays. A Thomas factorization is suitable only with well-behaved pivots. A changed step length, coefficient interval or left-boundary discretization can require a new matrix; different matrices require their own factors.

For an unconstrained European step, reusable linear factors solve new right-hand sides in $O(n)$. For an American step, the obstacle remains an LCP: a linear factorization followed by one projection is not PSOR. Warm starts and three-array storage reduce work without changing the LCP. A sequential PSOR sweep uses newly updated neighbors; simultaneous updates of every node define a different iteration. Red-black ordering updates one color together and then the other, but changes the ordering and needs its own convergence check. Each sweep is $O(n)$; total work also depends on the iteration count. No storage choice guarantees a particular runtime.

Source: [SciPy banded solver](https://docs.scipy.org/doc/scipy/reference/generated/scipy.linalg.solve_banded.html) for array layout. Complexity and reuse conditions follow from the stated tridiagonal system; the PSOR conditions above remain unchanged.

### American exercise rights with PSOR

Solve the interior discrete LCP, keeping new-time boundary values fixed. In the following iteration and residual, A is the interior matrix and rhs already includes the new-boundary contributions above. Neighbor terms refer only to interior unknowns: omit the left term in the first interior row and the right term in the last. Do not add a boundary neighbor again after moving it into rhs. Initialize with the previous layer or another warm start. Sweep in increasing row order; use the updated left neighbor and previous-iterate right neighbor.

$y_{i}$ is the unrelaxed Gauss-Seidel update; $\omega$ is relaxation and $g_{i}$ nodal payoff. $\mathrm{old}_{\mathrm{iter}}$/$\mathrm{new}_{\mathrm{iter}}$ denote within-step iterations. $a_{\mathrm{gap}}$ is the payoff gap; $b_{\mathrm{gap}}$ is the LCP equation residual.

**Unrelaxed Gauss–Seidel update**

$$
y_{i} = (\mathrm{rhs}_{i}-A_{i,i-1}\cdot V_{i-1,\mathrm{latest}}-A_{i,i+1}\cdot V_{i+1,\mathrm{old},\mathrm{iter}})/A_{i,i}
$$

**Relax and project onto the exercise payoff**

$$
V_{i,\mathrm{new},\mathrm{iter}} = \max (g_{i}, V_{i,\mathrm{old},\mathrm{iter}}+\omega \cdot (y_{i}-V_{i,\mathrm{old},\mathrm{iter}}))
$$

**Payoff and equation gaps for the LCP check**

$$
\begin{gathered}
a_{\mathrm{gap}} = V-g \\
b_{\mathrm{gap}} = A\cdot V-\mathrm{rhs}
\end{gathered}
$$

Project the current value iterate inside each row update, not the right-hand side rhs. Projecting once after an unconstrained solve is a different method, not PSOR. Typical relaxation starts with $1\le \omega <2$, often 1.2-1.6; convergence depends on the matrix and parameter choice. Use scaled iterate-change tolerance AND check $a_{\mathrm{gap}}\ge 0, b_{\mathrm{gap}}\ge 0, \min (a_{\mathrm{gap}},b_{\mathrm{gap}})$ approximately zero componentwise, with an iteration cap. A small iterate change is not proof of a solved LCP. Report nonconvergence. Once converged to the same LCP solution, $\omega$ affects speed rather than value. Brennan-Schwartz elimination is an alternative under its single-exercise-region conditions, not a replacement if PSOR is specifically required.

### Nonsmooth payoff or post-dividend layer

For a kinked payoff, the Rannacher variant used here replaces one or two full CN steps with twice as many backward-Euler half steps, then resumes CN. Restart this damping after each dividend map. This specifies the chosen variant; it is not a claim that every contract requires damping or that undamped CN must fail. Apply the same exercise rights during startup. Damping does not eliminate the need to check convergence.

### Compact solver template

When a task asks for American and European prices on a uniform stock grid with Crank–Nicolson, PSOR and cash dividends → start from this short solver and change only what the task states differently (grid, damping, event timing). It keeps cells short, which matters under a per-reply output limit; define it in one cell and call it in the next. Pass the edge values the task defines, by option type, exercise style and remaining time; when the task gives none, the usual choice is:

```python
def put_edge(S_edge, tau, american):            # S = 0: K (American) or K e^(-r tau) (European); far edge: 0
    return (K if american else K*np.exp(-r*tau)) if S_edge == 0 else 0.0
def call_edge(S_edge, tau, american):           # S = 0: 0; far edge: S e^(-q tau) - K e^(-r tau), at least S - K if American
    if S_edge == 0:
        return 0.0
    eu = S_edge*np.exp(-q*tau) - K*np.exp(-r*tau)
    return max(eu, S_edge - K) if american else eu
```

```python
import numpy as np
from scipy.linalg import solve_banded
def cn_psor(payoff_fn, boundary, S_max, K, T, r, q, sigma, NS, NT, american=True, omega=1.2, tol=1e-8, rannacher=2, events=()):
    """Price on a uniform S grid with Crank-Nicolson (Rannacher start) and PSOR; returns S, t, V[time, stock] (t ascending).
    boundary(S_edge, tau, american) gives the edge value at remaining time tau, as the task defines it."""
    S = np.linspace(0.0, S_max, NS + 1)
    dt = T / NT                                                     # this call's own time step; never a dt defined outside
    i = np.arange(1, NS)
    a = 0.5 * (sigma**2 * i**2 - (r - q) * i); b = -(sigma**2 * i**2 + r); c = 0.5 * (sigma**2 * i**2 + (r - q) * i)
    payoff = payoff_fn(S); V = payoff.copy(); out = np.empty((NT + 1, NS + 1)); out[NT] = V
    for n in range(NT - 1, -1, -1):
        theta = 1.0 if (NT - 1 - n) < rannacher else 0.5          # damped first steps
        rhs = V[1:-1] + (1 - theta) * dt * (a * V[:-2] + b * V[1:-1] + c * V[2:])
        tau = T - n * dt                                            # remaining time at the new layer
        lo, hi = boundary(0.0, tau, american), boundary(S_max, tau, american)
        V_new = V.copy(); V_new[0], V_new[-1] = lo, hi
        rhs[0] += theta * dt * a[0] * lo; rhs[-1] += theta * dt * c[-1] * hi
        diag, low, up = 1 - theta * dt * b, -theta * dt * a, -theta * dt * c
        x = V[1:-1].copy()
        if american:
            for _ in range(10000):
                err = 0.0
                for k in range(NS - 1):
                    y = (rhs[k] - (low[k] * x[k - 1] if k > 0 else 0.0) - (up[k] * x[k + 1] if k < NS - 2 else 0.0)) / diag[k]
                    new = max(payoff[k + 1], x[k] + omega * (y - x[k])); err = max(err, abs(new - x[k])); x[k] = new
                if err < tol: break
        else:
            ab = np.zeros((3, NS - 1)); ab[0, 1:] = up[:-1]; ab[1] = diag; ab[2, :-1] = low[1:]
            x = solve_banded((1, 1), ab, rhs)
        V_new[1:-1] = x; V = V_new
        for t_ev, D in events:                                      # cash dividend at this layer: V(S) <- V(S - D)
            if abs(n * dt - t_ev) < 0.5 * dt:
                V = np.interp(np.maximum(S - D, 0.0), S, V)
                if american:
                    V = np.maximum(V, payoff)
        out[n] = V
    return S, np.linspace(0.0, T, NT + 1), out
```

Checks before writing outputs: European prices without dividends agree with Black–Scholes to the grid's discretization error; with no dividends the American call equals the European call to solver precision; American values are at least the European values and the payoff; the row of `V` for t = 0 is today's price surface (rows run in ascending t). Verified on a 300 × 600 grid (K = 100, T = 1, r = 5%, σ = 20%) with the edges above: European put 5.5711 and call 10.4481 against Black–Scholes 5.5735 and 10.4506; American put 6.0874; American and European calls equal to 1e-12.

### Solved layers, output sampling and runtime

Generate each reported price, Greek, exercise boundary and table from the corresponding solved time layer and exercise rights. Build the full numeric time and stock arrays before selecting requested output rows or columns; sampling must not replace the PDE calculation. When correcting a solution, recompute its dependent diagnostics and outputs from that solution. A put exercise boundary must come from the positive-intrinsic exercise region, not a distant zero-value truncation boundary. A solution stored as [time layer, stock node] is transposed before writing a table whose rows are stock nodes and whose columns are times; when the sampled counts are equal no shape error appears, so check one known cell after writing (the row nearest S0 in the t=0 column equals the reported price).

Use the previous layer as the PSOR warm start and verify the stated LCP tolerance. If a runtime requirement applies to a self-contained program, run the complete program in a fresh process and measure its full execution, including requested calculations and outputs. Timing an isolated kernel or reusing an already-populated interactive session does not measure that program. Preserve the required numerical method and performance requirement.

## 6. Dividend events

Use this block only when the contract model specifies dividends. For continuous yield, q is already in the drift; no cash jump is added. For a futures-style driftless underlying, $q=r$ is a modeling substitution. If continuous and discrete dividends both exist, include only distinct income streams, not the same dividend twice.

### Deterministic cash drop at an ex-date

Let $V_{\mathrm{plus}}$ be the post-event value and $V_{\mathrm{minus}}$ the pre-event value at the SAME calendar time $t_{d}$. With a specified cash drop $D_{\mathrm{cash}}$ and $S_{\mathrm{minus}}>D_{\mathrm{cash}}$:

$S_{\mathrm{minus}}$/$S_{\mathrm{plus}}$ are pre/post-jump stock prices; for the current event, $D_{\mathrm{cash}}$/$t_{d}$ denote $D_{j}$/$t_{j}$.

**Stock jump at the cash-dividend event**

$$
S_{\mathrm{plus}} = S_{\mathrm{minus}}-D_{\mathrm{cash}}
$$

**European value matching across the event**

$$
\;\text{European}\;: V_{\mathrm{minus}}(S_{\mathrm{minus}}) = V_{\mathrm{plus}}(S_{\mathrm{minus}}-D_{\mathrm{cash}})
$$

**American exercise comparison across the event**

$$
\;\text{American}\;: V_{\mathrm{minus}}(S_{\mathrm{minus}}) = \max (g(S_{\mathrm{minus}}), V_{\mathrm{plus}}(S_{\mathrm{minus}}-D_{\mathrm{cash}}))
$$

Read the post-event vector at a smaller stock coordinate; do not use $S_{\mathrm{minus}}$+$D_{\mathrm{cash}}$. For $S_{\mathrm{minus}}\le D_{\mathrm{cash}}$ use the specified nonnegative-stock convention. A capped jump to zero and an uncapped cash subtraction are different models.

Use one clock consistently: either calendar t decreases from T to 0 with event coordinate $t_{d}$, or remaining time $\tau$ increases from 0 to T with event coordinate $T-t_d$. Never compare a calendar clock with a remaining-time event coordinate.

For each interior event, carry out this sequence:

$V_{\mathrm{after}}$/$V_{\mathrm{plus}}$ mean post-event values; $V_{\mathrm{before}}$/$V_{\mathrm{minus}}$ mean pre-event values. continuation is the interpolated holding value across the event.

**Backward processing of one dividend event**

Evolve from later calendar times to the event, splitting a step if needed.
$V_{\mathrm{after}}$ is the value vector reached before applying this event's stock map.

$$
V_{\mathrm{plus}} = V_{\mathrm{after}}
$$

$\mathrm{continuation}(S)$ interpolates $V_{\mathrm{after}}$ at the prescribed post-jump stock coordinate.
European:

$$
V_{\mathrm{before}}(S) = \mathrm{continuation}(S)
$$

American:

$$
V_{\mathrm{before}}(S) = \max (g(S), \mathrm{continuation}(S))
$$

$$
V_{\mathrm{minus}} = V_{\mathrm{before}}
$$

Continue backward from $V_{\mathrm{before}}$ through every remaining interval to valuation.

Each applicable event map occurs exactly once, including when its date coincides with a time node. Events at valuation or expiry require the contract's specified event/payoff order. The jump consumes zero time: it neither replaces a PDE interval nor ends the valuation. Check that positive PDE step lengths sum to T and that each applicable event was processed once.

$V_{\mathrm{minus}}$ and $V_{\mathrm{plus}}$ are pre-event and post-event value functions. Comparing them at a common stock coordinate is different from following a stock price through its jump. The continuation map instead compares $V_{\mathrm{minus}}$($S_{\mathrm{minus}}$) with $V_{\mathrm{plus}}$($S_{\mathrm{plus}}$). An increasing post-event test function decreases under a downward query shift; a decreasing one increases, away from truncation boundaries. This tests mapping direction, not full option value.

### Proportional drop at an ex-date

If the stock drops by fraction $\delta _{\mathrm{div}}$ instead of a cash amount, use $S_{\mathrm{plus}}=S_{\mathrm{minus}}\cdot (1-\delta _{\mathrm{div}})$ in the same event logic. For a combined event use its explicitly stated stock map; do not invent an order. Escrowed-dividend pricing based on S0 minus dividend PV is a different model.

## 7. Valuation and checks

Use this block after a converged evolution. Read the valuation layer at S0, on-node or with a stated interpolation (for example, quadratic/cubic interpolation in log-price). Check interpolation stability; it is not an extra pricing model.

For an interior node on a uniform stock-price grid, use values from the same contract, time layer and event side:

$\Delta$/$\Gamma$ are first/second stock derivatives.

**$\Delta$ from stock-grid values**

$$
\Delta _{i} = (V_{i+1}-V_{i-1})/(2\cdot \mathrm{d}S)
$$

**$\Gamma$ from stock-grid values**

$$
\Gamma _{i} = (V_{i+1}-2\cdot V_{i}+V_{i-1})/(\mathrm{d}S^{2})
$$

If S0 is a node, use its centered stencil. Otherwise differentiate a consistent interpolant or interpolate computed grid derivatives, stating the convention; do not move the node. A stock-grid stencil uses dS, not log spacing dx. It is not centered at a domain endpoint.

**$\Delta$ from log-grid derivatives**

$$
\Delta  = V_{x}/S
$$

**$\Gamma$ from log-grid derivatives**

$$
\Gamma  = (V_{\mathrm{xx}}-V_{x})/S^{2}
$$

Calendar time and remaining time satisfy $t=T-\tau$. The price at S0 and the valuation-layer interpolant at S0 must agree when the same interpolation is used.

To detect an economic exercise region, require positive intrinsic value and a small V-g gap with scale-aware tolerance. For a vanilla put boundary take the largest qualifying stock; for a vanilla call take the smallest. Deep OTM nodes with V approximately g approximately zero do not establish exercise. If none qualify, the grid has not identified a finite exercise boundary; a domain endpoint is not a substitute. Resolution is about a grid spacing; interpolation may refine an estimate. Align boundary times and event-side labels. If the requested diagnostic convention differs, label it separately from the economic exercise boundary. At expiry use the specified expiry convention, not an inferred continuation boundary.

### Extracting the exercise boundary from a solved grid

Equality $V(S_i) = \mathrm{payoff}(S_i)$ marks exercise only where the payoff is positive. For a put, every node with $S_i \ge X$ has payoff 0, and far from the strike the solved value is also numerically 0, so "V equals payoff" holds there without any exercise; the same happens at every node of the expiry layer. Scanning all nodes from high $S$ downward for $|V - \mathrm{payoff}| \le$ tol therefore returns the upper truncation node or another out-of-the-money node.

Restrict the scan to nodes with positive intrinsic value (put: $S_i < X$; call: $S_i > X$). For a put, $S^{*}(t_n)$ is the largest such node where $V - \mathrm{payoff} \le$ tol, taken from the exercise region that starts at the low end of the grid; for a call, the smallest such node on the high side. At the expiry layer this gives the node next to the strike, not the edge of the grid. When no node qualifies, report "no exercise boundary" as the task defines it.

Check the extracted series: for $t < T$ a put boundary lies below $X$ (a call boundary above $X$), it moves monotonically towards the strike as expiry approaches in an interval without dividend events, and the continuation-side delta just above a put boundary is close to $-1$. Write the boundary file and every summary value from the same extracted series.

### Boundary diagnostics near expiry and between events

Use these limits only for positive volatility, $r>0$ and $q\ge 0$, in a final interval without cash-dividend events (and no event at expiry). Here T- means calendar time approaching expiry from below, not the expiry payoff layer:

$S_{\mathrm{star}}$ is the economic exercise threshold in stock-price units.

**Put exercise-boundary limit as expiry approaches**

Put, when $q \le  r$:

$$
S_{\mathrm{star}}(T-) = X
$$

Put, when $q > r$:

$$
S_{\mathrm{star}}(T-) = X\cdot r/q
$$

**Call exercise-boundary limit as expiry approaches**

Call, when $q > 0$:

$$
S_{\mathrm{star}}(T-) = \max (X,X\cdot r/q)
$$

For $q=0$ and no remaining cash dividends, the call has no finite early-exercise boundary. Check approach to these limits under refinement; do not overwrite computed boundaries with them. At T itself, positive-payoff scanning selects a node next to X, which need not equal the T- limit when that limit differs from X.

At a regular finite boundary for $t<T$, away from dividend events, smooth fit requires the continuation-side $\Delta$ to approach -1 for a put and +1 for a call. Check this under space/time refinement with consistent event sides. Do not impose it at the expiry kink or across a dividend jump. A coarse stencil can deviate; $\Delta =-1$ inside the put exercise region alone does not locate its boundary. Combine value matching, positive payoff, the adjacent continuation region and derivative convergence.

Refine stock/time resolution, domain and iterative tolerance sufficiently separately to identify the error source. Stability alone does not establish positivity, monotonicity or accuracy. Central drift differences, payoff kinks, the obstacle and event interpolation can lower observed order; do not promise a universal fourfold improvement.

If a European check disagrees with its benchmark, first compare the same small linear time step against a dense solve; then check actual grid spacing and row coefficients, old/new boundary terms, and the time coordinate. Refine a consistent grid before interpreting the remaining discretization error. A fixed premium added to an analytic price is not a finite-difference solution, and an assumed boundary curve is not a boundary recovered from the obstacle problem.

Check European prices against BS only under matching assumptions. For $q=0$, no cash dividends and $r\ge 0$, the American call equals the European call. Do not extend that identity unchanged to negative rates. When the identity applies → compute this pair after pricing → if the American call exceeds the European one by more than the discretization error measured on a refined grid (not just the PSOR tolerance), check boundary terms, row coefficients, the time direction and, for a kinked payoff under Crank–Nicolson, the damped start above. When the solver steps in remaining time τ and an output is defined in calendar time t → convert its rows or columns to t = T − τ in the order the output defines (ascending t unless stated otherwise) → check that the row labelled t = 0 holds today's values and the row labelled t = T the expiry values. An output defined in τ keeps τ. With identical contracts American value is at least intrinsic and at least European value, within numerical tolerance. Missing projection, wrong $\tau$ direction, r instead of r-q, European call payoff at a distant boundary, narrow domains and poorly resolved S0/X are distinct errors; choose a check that isolates the suspected one.

### Coarse/fine estimates and convergence

Use the prescribed fine/coarse grids and event schedule. Changing grid resolution must not change the contract or event-side convention. If the leading error is proportional to h^p and coarse spacing is R times fine spacing, Richardson gives:

$\operatorname{P}_{\mathrm{fine}}$/$\operatorname{P}_{\mathrm{coarse}}$ are fine/coarse-grid prices; $\operatorname{P}_{\mathrm{extrapolated}}$ is the extrapolated price.

**Richardson price extrapolation**

$$
\operatorname{P}_{\mathrm{extrapolated}} = (R^{p}\cdot \operatorname{P}_{\mathrm{fine}}-\operatorname{P}_{\mathrm{coarse}})/(R^{p}-1)
$$

If p or the extrapolation formula is prescribed, report that estimate while checking its reliability; do not claim the observed order is proved by CN's nominal order. The ratio $|P_{\mathrm{coarse}}-P_{\mathrm{extrapolated}}|/|P_{\mathrm{fine}}-P_{\mathrm{extrapolated}}|$ equals $R^p$ algebraically when $\operatorname{P}_{\mathrm{fine}}$ differs from $\operatorname{P}_{\mathrm{coarse}}$. It is not an independent convergence test; equality of the two prices gives an undefined 0/0 ratio. Actual order assessment requires further refinement or an independent benchmark.

Re-pricing without dividend payments is a separate contract calculation, not a manual price adjustment. On identical model and exercise conventions, nonnegative cash drops under a monotone nonnegative-stock map weakly increase put values and weakly decrease call values; do not hard-code strict inequalities when effects may vanish.

At expiry every node satisfies $V=g$: a literal equality scan and an economic exercise threshold are different diagnostics. If the task leaves this distinction or an event-side output unspecified, state the chosen interpretation rather than silently inventing a boundary value.

## 8. References

Crank and Nicolson (1947), Proceedings of the Cambridge Philosophical Society 43(1), 50-67. Cryer (1971), The Solution of a Quadratic Programming Problem Using Systematic Overrelaxation, SIAM Journal on Control 9(3), 385-392. Rannacher (1984), Finite element solution of diffusion problems with irregular data, Numerische Mathematik 43, 309-327. Brennan and Schwartz (1977), The Valuation of American Put Options, Journal of Finance 32, 449-462.

Boundary diagnostics: Evans, Kuske and Keller (2002), [American options on assets with dividends near expiry](https://doi.org/10.1111/1467-9965.02008), for expiry-side limits; Jourdain and Vellekoop (2012), [Regularity of the American Put option in the Black–Scholes model with general discrete dividends](https://www.sciencedirect.com/science/article/pii/S0304414912001032), for regularity and smooth contact away from dividend dates.
