# Compound Poisson aggregate loss by FFT: grid, discretization and tail measures

The task description inside <task_instructions> takes priority over this card: where it gives a different formula, a grid rule or a risk measure, follow the task description.

## Algorithm

```text
Input: Poisson intensity lambda, severity distribution F, grid size n, confidence levels
1   choose an initial range top >= the percentile the task names; h <- top / n
2   discretize the severity by rounding: f_0 = F(h/2), f_j = F((j + 1/2) h) - F((j - 1/2) h)
3   g <- real(ifft(exp(lambda (fft(f) - 1))))       # aggregate pmf on the grid 0, h, ..., (n - 1) h
4   compute VaR and ES on the grid
5   double top (h doubles, n fixed) and repeat 2-4 until VaR and ES change by less than a relative 1e-3
        between two doublings; keep the last result
6   report h, top, the probability mass in the top 1% of the grid, and the mass lost by the severity
        beyond the grid
```

The FFT is circular: aggregate probability beyond $n h$ wraps around and lands at small losses. A range that only just covers a high percentile is enough for VaR but not for ES with a heavy-tailed severity (lognormal, Pareto): the wrapped tail lowers ES. Step 5 is the check; the mass left in the top of the grid should be negligible.

## VaR and ES on a discrete grid

With grid points $x_i = i h$, pmf $g_i$, cdf $c_i$ and level $p$: $\mathrm{VaR}_p = x_k$ with $k$ the first index where $c_k \ge p$, and
$$\mathrm{ES}_p = \frac{1}{1-p}\left[\sum_{i>k} g_i x_i + (c_k - p)\, x_k\right]$$
If <task_instructions> defines ES as $E[S \mid S > \mathrm{VaR}_p]$, use $\sum_{i>k} g_i x_i / (1 - c_k)$ instead and say so.

## Checks

1. The aggregate mean $\sum_i g_i x_i$ is close to $\lambda E[X]$ when the severity mean is finite.
2. VaR and ES are stable when the range is doubled.
3. Monte Carlo values agree within their sampling error; heavy tails make the Monte Carlo ES noisy, so compare against its standard error rather than a fixed percentage.
