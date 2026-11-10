# Monte Carlo sensitivities by bump-and-revalue, and AR(1)/OU fits from dated observations

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, a bump or a convention, follow the task description.

## Algorithm 1: bump-and-revalue with common random numbers

```text
Input:  pricing model with parameters theta, bump sizes, seed, number of paths and steps
1   rng <- numpy.random.default_rng(seed)
2   Z <- rng.standard_normal(shape the base price uses)        # drawn ONCE
3   function PRICE(theta, Z): simulate every path from Z only; no call to rng inside
4   base <- PRICE(theta, Z)
5   for each sensitivity:
6       h <- absolute bump; for a relative bump of p percent, h <- theta_i * p / 100
7       up <- PRICE(theta with theta_i + h, Z);  down <- PRICE(theta with theta_i - h, Z)
8       sensitivity <- (up - down) / (2 h)
9   report base and every sensitivity
```

The base price must equal PRICE(theta, Z) with the same Z, so that the base and the bumped prices share every random draw. A pricing function that keeps drawing from a shared generator gives every call different numbers; the difference of two prices is then dominated by noise and can have the wrong sign.

## Checks

1. Repeating PRICE(theta, Z) returns the identical number.
2. The sign of each sensitivity matches the payoff: for example a call on heating degree days, $\max(T_{\mathrm{base}} - T, 0)$ summed, loses value when temperatures rise, so its temperature delta is negative.
3. With a second seed (same number of paths) each sensitivity stays within a few standard errors.

## Algorithm 2: AR(1) / discretized OU fit on dated observations

```text
Input:  dated values x(date), optional group (for example year); step dt
1   sort by group, then date
2   pair (x_t, x_next) only where next date - date equals exactly one step and both rows are in the same group
3   regress dx = x_next - x_t on x_t with an intercept: dx = alpha + beta x_t + eps
4   kappa <- -beta / dt;  sigma <- std(eps, ddof = 1) / sqrt(dt)   (or the mapping the task states)
5   print the number of pairs and compare with the count expected from the calendar
```

Merging or grouping can reorder rows; sort again before forming pairs. A shift by one row is a one-step lag only after sorting and only where no date is missing.
