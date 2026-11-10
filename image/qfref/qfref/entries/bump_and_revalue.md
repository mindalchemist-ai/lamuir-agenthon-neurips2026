# Bump-and-revalue sensitivities with Monte Carlo: common random numbers

Use this when a sensitivity is computed by repricing a simulated value with a parameter moved up and down.

## Common random numbers

- Draw every random number once (for example a fixed array `Z` of shape (paths, steps), generated from the stated seed before any pricing) and reuse the same array for the base, up and down valuations. Only the parameter changes between them.
- A pricing function that draws fresh numbers on each call (calling a generator inside the function, or advancing one global generator) gives the up and down prices independent noise. The difference quotient then carries noise of order $\sqrt{2}\,\mathrm{SE}_{\mathrm{price}}/h$, which for a small bump $h$ is far larger than the sensitivity itself.
- Recompute every quantity that depends on the bumped parameter inside the revaluation (simulated paths, drift or mean-reversion terms, seasonal levels, discounting); keep everything else, including the random draws, identical.
- Two layouts of the random numbers (array shape, draw order, one scalar draw per step versus one array) give different paths, so prices from two layouts agree only within sampling error, never digit for digit. Do not assert that a revalued base price equals an earlier figure exactly: price the base, up and down with one function and one array, and let that base replace the earlier figure.

## Difference quotient and its error

Central difference: $(V(p+h) - V(p-h)) / (2h)$ with the bump and denominator exactly as the task states them. For a relative bump of $x\%$ the parameter moves by $h = (x/100)\,p$. Compute the quotient path by path from the paired payoffs, $d_i = (\text{payoff}_i(p+h) - \text{payoff}_i(p-h)) / (2h)$; the sensitivity is the mean of $d_i$ and its standard error is `np.std(d, ddof=1) / np.sqrt(N)`.

When an output field records a bump size → write it in the unit its definition or the stated input gives: a relative change as a fraction (0.01 for one percent) where the input is a fraction, percentage points where the field is defined in percent, an absolute parameter increment where the bump is absolute → check that the written value, applied through the stated formula, reproduces the parameter change used in the calculation.

## Check

Rerun the sensitivity with a second seed (same number of paths): with common random numbers the two values agree within a few standard errors; with independent draws they can differ in sign. Halving $h$ should change a smooth sensitivity only slightly.
