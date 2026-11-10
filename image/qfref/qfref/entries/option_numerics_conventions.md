# Option-pricing numerics: surface grids, forward quantities, identity checks, task settings, API arguments, local-volatility Monte Carlo, slice repair and implied volatility

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input, setting or convention, follow the task description.

Read the topics relevant to the task; a task usually needs several of them.

## Topic 1: Building a strike-by-maturity grid from tables

**Purpose:** Turn quote or surface tables into a matrix whose rows follow maturity and whose columns follow strike.

**When to use:** Any surface, local-volatility or Monte Carlo pipeline that works on an expiry-strike grid.

**Constraints:**

1. Order rows by numeric time to maturity, never by expiry label: labels sort as text (a day number before a month), so derivatives along maturity would be taken between the wrong neighbours.

**How to implement:**

Step 1: Before merging quotes with metadata, make the key unique on the side that should be unique and merge with `DataFrame.merge(..., validate="many_to_one")` (or the relation you expect); compare row counts before and after.

Step 2: Pivot on the numeric maturity (`DataFrame.pivot(index=maturity_in_years, columns=strike, values=...)`), then `sort_index()`; or order the expiries by maturity and align every table with `DataFrame.reindex(index=ordered_expiries, columns=sorted_strikes)` before converting to arrays.

Step 3: Keep the maturity vector, the strike vector and the value matrix together (`.index`, `.columns`, `.to_numpy()`), so that the rows of the matrix follow the maturity vector.

**Double check:**

1. Both the maturity vector and the strike vector are strictly increasing (`np.diff(...) > 0`), and the merged table has the expected row count; if not, re-sort or fix the duplicate key before computing anything along maturity.

## Topic 2: Forward quantities and finite values on a maturity grid

**Purpose:** Place interval quantities on the right rows and keep every written value finite.

**When to use:** A forward rate or forward variance between consecutive maturities, or any table written on an expiry grid.

**Constraints:**

1. The value for the interval $[T_i,T_{i+1}]$ belongs to the row of $T_i$ (it looks forward).
2. The last node has no next one: write what the task says for it, or carry the last interval's value, never a blank or NaN.

**How to implement:**

Step 1: Interval values by differences over the vector, for example forward variance $(w_{i+1}-w_i)/(T_{i+1}-T_i)$ with `np.diff(w) / np.diff(T)`.

Step 2: Append the last interval's value for the last row (`np.append(values, values[-1])`) unless the task states another rule.

Step 3: A NaN or a non-positive local variance usually sits on the shortest slice (days to expiry, almost no total variance, one-sided quotes) or outside the fitted strike range: if the task lets you choose expiries, leave that slice out and record why; otherwise apply the task's floor or cap.

**Double check:**

1. Every written value is finite (`np.isfinite(...).all()`); if not, find the slice or strike range that produces it and apply Step 3.

## Topic 3: Synthetic identity checks

**Purpose:** Test a surface pipeline on data with a known answer.

**When to use:** The task asks for a diagnostic such as "a flat implied volatility must give the same constant local volatility", or any time a new surface pipeline is built.

**Constraints:**

1. The check is only a test when the same functions that process the market data process the synthetic data; writing the expected value is not a test.

**How to implement:**

Step 1: Generate prices from the known volatility (for example Black-Scholes at a constant $\sigma$) on a moderate grid: strikes near the money and maturities from about a month up, where prices are well above floating-point resolution.

Step 2: Run the same derivative and local-volatility functions as for the main surface.

Step 3: Report the known volatility as the implied one rather than inverting the synthetic prices again.

**Double check:**

1. The recovered local volatility matches the input volatility to a small relative tolerance (for example `np.allclose(..., rtol=1e-3)`); if not, the main pipeline has the same bug.

## Topic 4: Surfaces built from fitted slices

**Purpose:** Build an output grid that a parametric fit (for example SVI per expiry) actually covers.

**When to use:** The surface comes from slices fitted per expiry.

**Constraints:**

1. A fit defines the surface only on the fitted slices and only inside each slice's fitted strike range: build the output grid from the selected expiries and a strike grid inside those ranges, not from every raw quote.

**How to implement:**

Step 1: Maturity derivative between fitted slices: hold the strike $K$ fixed, reprice each slice at $K$ with its own log-moneyness $k=\ln(K/F_T)$, and difference consecutive selected expiries.

Step 2: A negative maturity derivative is calendar arbitrage in the fit: report it; do not take its absolute value or clip it.

**Double check:**

1. Every value on the output grid is finite; a NaN means the grid asks for a point the fit does not cover: shrink the grid to the covered range.

## Topic 5: Premiums quoted in the underlying coin

**Purpose:** Convert coin-quoted option premiums and infer the forward without mixing units.

**When to use:** On coin-settled venues the premium is quoted in units of the underlying coin while strikes and forwards are in USD.

**How to implement:**

Step 1: Premium in USD at the forward: $\text{premium}_{USD}=\text{premium}_{coin}\cdot F$.

Step 2: Put-call parity with zero discounting, $C-P=F-K$ in USD, reads $(C_{coin}-P_{coin})F=F-K$, so

$$F=\frac{K}{1-(C_{coin}-P_{coin})}$$

**Limitations and cautions:**

1. Adding a coin-denominated difference to a USD strike mixes units.

**Double check:**

1. $(C_{coin}-P_{coin})\cdot F$ equals $F-K$ in USD for each pair used.

## Topic 6: Numerical settings stated by the task

**Purpose:** Keep the task's integration ranges, node counts, step sizes, floors, caps, thresholds and tolerances exactly as written.

**When to use:** The task text writes down any numerical setting.

**Constraints:**

1. These settings are part of the specification; keep them even when a result looks inaccurate: a comparison the task asks for (for example two quadrature settings) is meant to show the effect of exactly those settings.
2. Apply a stated floor or cap as written instead of replacing the value with NaN; use NaN only where the task says so.

**How to implement:**

Step 1: Copy every setting from the task text into one dictionary at the top and read it everywhere from there.

Step 2: Apply floors and caps with `np.maximum` / `np.minimum`, and the task's NaN rule (if any) with `np.where` on the condition it states.

**Double check:**

1. Every value outside the task's NaN condition respects the floor and cap; print the settings dictionary next to the results.

## Topic 7: Task wording to API arguments

**Purpose:** Pick the arguments that silently change results according to what the task says.

**When to use:** Before calling any of the functions below.

**How to implement:**

Step 1: Read the task's wording for each argument and choose by this table:

| Call | Argument | Meaning | Task wording that decides it |
|---|---|---|---|
| `np.gradient(f, x, axis=, edge_order=)` | `x` | coordinates (array) or one constant spacing (scalar); a scalar on an unequal grid is wrong | grid values listed, "non-uniform grid" |
| | `edge_order` | 1 (default): first-order one-sided difference at the two ends; 2: second-order one-sided three-point formula at the ends | "one-sided at the ends" -> 1; "second-order at the edges" -> 2 |
| | second derivative | applying `np.gradient` twice gives the wide stencil $(f_{i+2}-2f_i+f_{i-2})/(2h)^2$; the central three-point formula is $(f_{i+1}-2f_i+f_{i-1})/h^2$; they differ | "apply numpy.gradient twice" -> twice; "central differences" for the second derivative -> three-point |
| `scipy.integrate.quad(f, a, b, limit=)` | `a, b, limit` | finite range and maximum number of subintervals (default 50) | stated integration range / limit |
| `np.polynomial.legendre.leggauss(n)` | mapping | nodes and weights for the interval $[-1,1]$; map to $[a,b]$ with $x=\frac{b-a}{2}(t+1)+a$ and weights times $\frac{b-a}{2}$ | stated node count and range |
| `scipy.interpolate.PchipInterpolator(x, y, extrapolate=)` | `extrapolate` | None/True extrapolates from the end intervals, False returns NaN outside $[x_0,x_n]$ | "evaluate outside the quoted range", "no extrapolation" |
| `scipy.optimize.minimize(fun, x0, method=, bounds=)` | `method` | without it SciPy picks BFGS, L-BFGS-B or SLSQP depending on bounds and constraints | named solver, "bounded" |
| `scipy.optimize.brentq(f, a, b, xtol=)` | `a, b` | $f(a)$ and $f(b)$ must have opposite signs; an unbracketed root is an input problem, not a reason to widen until it works | stated volatility bounds |
| `np.random.RandomState(seed)` / `np.random.default_rng(seed)` | generator | different streams for the same seed; draw order and array shape also change the numbers | named generator, seed, "one draw per path and step" |

**Double check:**

1. Test an argument choice on a function with a known answer before using it: for example the mapped Gauss-Legendre rule integrates $x^3$ on $[a,b]$ to $(b^4-a^4)/4$, and at the first node `np.gradient` with `edge_order=1` equals the forward difference.

## Topic 8: Pipeline counters in a summary

**Purpose:** Report counts that match the objects the task's steps create.

**When to use:** A summary reports counts for a multi-stage pipeline (rows read, rows kept after cleaning, matched or paired items, nodes of a constructed grid, nodes of a derived surface).

**Constraints:**

1. A counter named after a surface, grid or curve counts the nodes of the object the task constructs under that name (for example the grid restricted to the task's target set), not the rows of an intermediate file whose name shares a word.

**How to implement:**

Step 1: For each counter, find in the task text the step that builds the object it names and count that object.

Step 2: Several counters may count the same object, and consecutive stages may have equal sizes; do not force each counter onto a different stage.

Step 3: A counter whose name matches an output file is not automatically that file's row count: decide from the step that builds the object, not from the file name.

**Double check:**

1. Print, next to each counter, the object, the task sentence that builds it and the filters it reflects, before writing the summary; check that the change between related counters is explained by what the step does. A counter without a quoted step is not settled.

## Topic 9: Naming output fields

**Purpose:** Name fields consistently with the task.

**When to use:** The task describes a field in words instead of giving its exact name.

**How to implement:**

Step 1: When the task gives exact key or column names, use them unchanged.

Step 2: Otherwise name the field the way the task names the same quantity elsewhere: reuse an abbreviation or prefix that another required file or schema of the task already uses. One quantity gets one name across all files of one task.

## Topic 10: Local-volatility Monte Carlo

**Purpose:** Simulate under a local-volatility surface quickly and judge the result correctly.

**When to use:** Paths are simulated with $\sigma_{loc}(T,K)$ from a surface, for vanillas, barriers or other exotics.

**Constraints:**

1. Along a path, at elapsed time $t$ since valuation and current price $S$, the diffusion coefficient is $\sigma_{loc}(t,S)$: elapsed time, not the time remaining to the contract.
2. Path count, steps, seed and variance reduction stated by the task are part of the specification: make the lookup faster, never the path count smaller.

**How to implement:**

Step 1: Build the interpolator once, outside the time loop (`scipy.interpolate.RegularGridInterpolator((T_nodes, K_nodes), sigma_nodes, bounds_error=False, fill_value=None)`), and hold it flat outside the nodes by clipping the query points to the node range (`np.clip`); `fill_value=None` alone extrapolates linearly and can go to zero or below.

Step 2: Loop over time steps only; at each step evaluate the interpolator once on the whole vector of path prices (query points stacked with `np.column_stack`), never per path.

Step 3: Log-Euler step with each sub-step's actual length $\Delta t_i$:

$$\ln S\mathrel{+}=\left(\mu-\tfrac12\sigma^2\right)\Delta t_i+\sigma\sqrt{\Delta t_i}\,Z$$

and monitor a discrete barrier only at the monitoring times.

Step 4: Time the first few steps on the full path count (`time.perf_counter`) and print the estimate for all steps; if it exceeds the time left, speed up the lookup (precomputed slices, `np.interp`).

Step 5: Price the vanilla on the same paths before the exotic.

Step 6: Barrier sanity reference: for a down barrier $B<S_0$, with $\nu=\mu-\sigma^2/2$, $b=\ln(B/S_0)$ and a representative local volatility $\sigma$, the continuous-monitoring hit probability is

$$p=N\!\left(\frac{b-\nu T}{\sigma\sqrt T}\right)+e^{2\nu b/\sigma^2}N\!\left(\frac{b+\nu T}{\sigma\sqrt T}\right)$$

Discrete monitoring gives a somewhat lower value of the same order.

Step 7: Closeness of the simulated vanilla to the surface price, by situation:

| Situation | Criterion for "close" |
|---|---|
| The task states a tolerance | Use it as written |
| Local volatility is known exactly (a parametric model or a fine, smooth grid) | A few standard errors |
| Local volatility built from a handful of quoted expiries and strikes, no tolerance stated | A few standard errors plus a structural allowance. The structural part (finite-difference derivatives across widely spaced quotes, interpolation, flat extrapolation, variance floors, time stepping) does not shrink with more paths; for a correct coarse-grid construction it is commonly a few percent and can approach ten percent of the price, while bugs give gaps of tens of percent. Use a threshold between the two regimes (around ten percent of the surface price plus a few standard errors) and write the measured parts, the threshold and why |
| Gap of tens of percent | Not discretisation: check time units in the lookup (years versus days), volatility versus variance, the orientation of the expiry-strike matrix, the drift, the antithetic pairing, and that the stated path count was used |

**Limitations and cautions:**

1. A threshold inside the structural range (2 standard errors, 1 %, 5 %) reports a correct coarse-grid construction as failed. A criterion is not widened because a check failed: if the gap stays outside it after the bug checks, the flag is False and the numbers are reported.

**Double check:**

1. The volatilities looked up are finite and positive at every step; the simulated barrier hit probability is of the same order as Step 6 (a value near zero or one with the barrier a few volatilities away means the monitoring indices or the comparison sign are wrong).

## Topic 11: Repairing a call-price slice

**Purpose:** Turn observed call prices into a call slice on the target strikes whose price falls as the strike rises, whose slopes between neighbouring strikes never decrease, and which never drops below the intrinsic value.

**When to use:** A call surface on a given grid of expiries and strikes must be free of static arbitrage across strikes, for example before Dupire local volatility is extracted from it.

**Constraints:**

1. Interpolate first, repair second. The observed quotes are interpolated onto the target strikes with the interpolator the task names (for example `scipy.interpolate.PchipInterpolator`); the repair then works only on those target-strike values. The repair is not an interpolator: its linear filling between hull points must never replace the task's interpolator.

**How to implement:**

Step 1: For each expiry, take the observed strikes and call prices, sorted by strike, and evaluate the task's interpolator at the target strikes. Print the number of target strikes outside the observed range and handle them as the task states.

Step 2: Lower convex hull of the target-strike points $(K_i,C_i)$: scan the points in strike order and drop the previous hull point whenever it lies on or above the segment joining its neighbours, so the slopes $(C_{i+1}-C_i)/(K_{i+1}-K_i)$ of the kept points are non-decreasing. Evaluate the hull at every target strike with `np.interp` (linear between kept hull points).

Step 3: Running minimum along strike, `np.minimum.accumulate`, so the slice is non-increasing.

Step 4: Intrinsic floor, `np.maximum(slice, np.maximum(F - K, 0))` with the discounting the task uses; each step keeps the properties of the earlier ones (the maximum of convex functions is convex).

**Limitations and cautions:**

1. Interpolation, PCHIP included, does not by itself make a slice convex; that is why Steps 2 to 4 follow.

**Double check:**

1. On the target strikes: slopes $\Delta C/\Delta K\le0$, slopes non-decreasing (on an unequal grid test slopes, not raw second differences), and $C\ge$ intrinsic. Also compare a few target nodes with the Step 1 interpolated values: a large change means the repair replaced the interpolation; redo Step 1 with the task's interpolator.

## Topic 12: Implied volatility over a strike-by-maturity grid

**Purpose:** Invert a whole grid of option prices to Black-Scholes implied volatilities in seconds rather than one root search per cell.

**When to use:** Implied volatilities are needed for many strikes and maturities at once (a surface, a smile per maturity). For a single quote, one bracketed root search is enough.

**Constraints:**

1. Do not loop over cells calling a scalar root finder: the number of cells times the iterations per cell, each with its own pricing call, is what makes a cell run for minutes. Work on whole matrices (Step 3).

**How to implement:**

Step 1: Price the model surface first, as an array over all strikes for each maturity (reuse the per-maturity work, see the model's card), and keep it; the inversion never calls the model again.

Step 2: Bounds as arrays: lower $\max(S e^{-qT}-K e^{-rT},0)$ and upper $S e^{-qT}$ for calls. Cells outside them have no implied volatility: mark them and record why.

Step 3: Invert in matrix form. Hold strikes and maturities as matrices $\mathbf K,\mathbf T$ of the grid's shape (`np.meshgrid`), the target prices as $\mathbf C$, and the bracket as matrices $\boldsymbol\sigma_{lo}=10^{-4}$, $\boldsymbol\sigma_{hi}=5$. Every operation below is elementwise on whole matrices:

1. Midpoint: $\boldsymbol\sigma=(\boldsymbol\sigma_{lo}+\boldsymbol\sigma_{hi})/2$
2. $\mathbf d_1=\left[\ln(S/\mathbf K)+(r-q+\boldsymbol\sigma^2/2)\mathbf T\right]/(\boldsymbol\sigma\sqrt{\mathbf T})$, and $\mathbf d_2=\mathbf d_1-\boldsymbol\sigma\sqrt{\mathbf T}$
3. Model price: $\mathbf P=S e^{-q\mathbf T}N(\mathbf d_1)-\mathbf K e^{-r\mathbf T}N(\mathbf d_2)$ (`scipy.stats.norm.cdf` on the matrices)
4. Update the bracket with a mask: where $\mathbf P<\mathbf C$ set $\boldsymbol\sigma_{lo}=\boldsymbol\sigma$, elsewhere set $\boldsymbol\sigma_{hi}=\boldsymbol\sigma$ (`np.where`)

Applying these four lines 60 times to the whole grid halves every cell's bracket to below $10^{-15}$ of its width; the grid is never traversed cell by cell. Newton steps can follow in the same matrix form with the vega matrix $S e^{-q\mathbf T}\sqrt{\mathbf T}\,n(\mathbf d_1)$, guarded with `np.clip` to stay inside the bracket.

Step 4: Before running the full grid, time the inversion on one maturity and print the estimate for the whole grid; keep the full run within a few seconds.

**Limitations and cautions:**

1. Deep out-of-the-money cells have tiny vega, so a price error there moves the implied volatility a lot; report them, but do not tighten tolerances by looping.

**Double check:**

1. Reprice every inverted cell at its implied volatility and assert the largest absolute price difference is below the pricing tolerance; where it fails, the cell was outside the bounds or the bracket: mark it rather than widening the bracket.
