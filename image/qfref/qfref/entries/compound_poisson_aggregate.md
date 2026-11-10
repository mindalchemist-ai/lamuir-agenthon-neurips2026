# Aggregate loss $S=X_1+\cdots+X_N$: severity discretization, Panjer recursion, FFT, VaR / TVaR

## Check first: wrapped mass, renormalization and the Monte Carlo cross-check

These add to the grid-span section below.

- For the FFT, 1 - g.sum() is not a tail check: the circular transform keeps total mass at one by folding the mass beyond (n - 1) h back onto the small amounts. Measure the wrap instead: rerun with twice as many grid points at the same h and compare the probabilities on the original grid; their largest difference (and the change in VaR and ES) is the wrapped mass. Double until VaR and ES stop changing at the reported precision.
- Do not divide g by g.sum() to hide missing mass. On a Panjer grid that is too short this rescales every probability upward and lowers VaR and ES; the fix is a longer grid. Renormalize only when the text asks for it, and report how much mass was missing.
- When a Monte Carlo estimate of the same ES or VaR is available, compare: a gap of more than about three Monte Carlo standard errors, with the grid result lower, points at a short grid (or at the severity discretization) before it points at noise.

```python
import numpy as np

def fft_aggregate(f, lam):                   # compound Poisson pmf on the grid of f (amounts k * h)
    return np.real(np.fft.ifft(np.exp(lam * (np.fft.fft(f) - 1.0))))

def tvar(g, h, p):
    G = np.cumsum(g); k = int(np.searchsorted(G, p)); amounts = np.arange(len(g)) * h
    return (np.sum(g[k + 1:] * amounts[k + 1:]) + (G[k] - p) * amounts[k]) / (1 - p)

h, lam, mean_sev, p = 1.0, 5.0, 40.0, 0.99
def severity(n):                             # exponential severity rounded to the grid
    edges = (np.arange(n + 1) - 0.5).clip(0) * h
    return np.diff(1 - np.exp(-edges / mean_sev))

n = 256
while True:
    t_n, t_2n = tvar(fft_aggregate(severity(n), lam), h, p), tvar(fft_aggregate(severity(2 * n), lam), h, p)
    if abs(t_2n - t_n) < 1e-6 * t_2n:
        break
    n *= 2
rng = np.random.default_rng(1)
N = rng.poisson(lam, 200_000)
S = np.array([rng.exponential(mean_sev, k).sum() for k in N])
q = np.quantile(S, p); tail = S[S >= q]
assert abs(t_2n - tail.mean()) < 3 * tail.std(ddof=1) / np.sqrt(len(tail)) + h
```

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Monte Carlo check: one random stream for counts and severities

Create the generator once, `rng = np.random.default_rng(seed)`, and draw the claim counts and then all severities from that same object. A sampler that builds a new generator inside, such as `def sev(size): return np.random.default_rng(seed).gamma(k, theta, size)`, restarts the stream on every call: each simulated year gets the first N numbers of one fixed sequence, the severities no longer vary between years, and the simulated quantiles come out well below the FFT ones for every severity law. Vectorised form with the task's seed and draw order:

```python
rng = np.random.default_rng(seed)
N = rng.poisson(lam, n_sim)
X = rng.gamma(shape, scale, N.sum())            # or lognormal / pareto: the task's severity law
S = np.zeros(n_sim); idx = np.repeat(np.arange(n_sim), N); np.add.at(S, idx, X)
```

If the task fixes another draw order (all severities of one simulation before the next count), follow it. Check: the simulated VaR and ES agree with the FFT values within sampling error at every level; a gap in the same direction for all severity laws points to the random stream, not the discretisation.

Severity samplers differ by library. `rng.pareto(a, size)` (also `np.random.pareto`) draws the Lomax (Pareto II) law on
[0, inf); a Pareto law with shape a and minimum x_m is `x_m * (1 + rng.pareto(a, size))`, the same law as
`scipy.stats.pareto(b=a, scale=x_m)`. `rng.lognormal(mean, sigma, size)` takes the mean and standard deviation of log X,
the same law as `scipy.stats.lognorm(s=sigma, scale=np.exp(mean))`. Before aggregating, compare each sampler's sample
mean with its exact mean (Pareto a x_m / (a - 1) for a > 1, lognormal exp(mean + sigma^2 / 2)):

```python
a, x_m = 4.0, 200.0
x = x_m * (1 + rng.pareto(a, 400_000))
assert x.min() >= x_m and abs(x.mean() / (a * x_m / (a - 1)) - 1) < 0.01
```

## Before the FFT / Panjer run: grid span and tail checks

The grid covers 0 to n h. A span that is too short cuts the tail: Panjer loses mass and FFT wraps it to the left, and both understate VaR and TVaR. A requirement such as "n h covers a high percentile of S" is a minimum. Set the span from the distribution itself, then confirm it:

```python
pilot = simulate_aggregate(n_paths)                     # same frequency and severity as the exact method
h = 1.5 * np.quantile(pilot, 0.9999) / n_grid           # starting span; heavy or skewed severities need the pilot, not mean + z*sd
g = aggregate_pmf(h)                                     # FFT or Panjer on the grid 0, h, ..., (n_grid - 1) h
print(1 - g.sum(), (np.arange(n_grid) * h * g).sum() - exact_mean)   # tail mass left out, mean error
# enlarge h (or n_grid) and rerun until VaR and TVaR stop changing at the reported precision
```

The grid's amounts are k h; f_j and g_k are probabilities and are never multiplied by h (section "Discretizing the severity").

## Model and assumptions
- Claim count N; severities $X_{i} \ge  0$ iid with cdf F, independent of N. $S = 0$ when $N = 0$, so S has an atom at 0 of mass $\operatorname{P}(N = 0)$(keep it).
- Exact numerical methods need an arithmetic severity on the grid `0, h, 2h, ...` (span h, money units). Panjer needs N in the
  (a, b, 0) class (Poisson, negative binomial incl. geometric, binomial); FFT needs only the pgf $\operatorname{P}_{N}(z) = \operatorname{E}[z^{N}]$.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| lam | Poisson mean | claims per period |
| $r, \beta$ | negative binomial: $\operatorname{P}(N=k) = C(k+r-1, k) (1+\beta )^{-r} (\beta /(1+\beta ))^{k}$, mean $r\beta$, variance $r\beta(1+\beta)$ | none |
| $m, q$ | binomial: m trials, probability q | none |
| $h, n$ | grid span (money) and number of grid points; amounts are $s_{k} = k h$, k = 0..n-1 | money, count |
| $f_{j}, g_{k}$ | $\operatorname{P}(\mathrm{discretized} X = j h), \operatorname{P}(S = k h)$ | probabilities |
Negative binomial in success-probability form (scipy $\mathrm{nbinom}(n=r, p)$): $p = 1/(1+\beta )$, mean $r (1-p)/p$.

## Moments (exact, no discretization)

$$
\operatorname{E}[S] = \operatorname{E}[N] \operatorname{E}[X]
$$

$$
\operatorname{Var}[S] = \operatorname{E}[N] \operatorname{Var}[X] + \operatorname{Var}[N] \operatorname{E}[X]^{2}
$$

Poisson case:

$$
\operatorname{Var}[S] = \mathrm{lam} \operatorname{E}[X^{2}]
$$

Third central moment, denoted $\mathrm{k3}$:

$$
\operatorname{E}[(S - \operatorname{E} S)^{3}] = \operatorname{E}[N] \mathrm{k3}(X) + 3 \operatorname{Var}[N] \operatorname{E}[X] \operatorname{Var}[X] + \mathrm{k3}(N) \operatorname{E}[X]^{3}
$$

For $\mathrm{k3}(N)$, Poisson gives $\mathrm{lam}$, negative binomial gives $r \beta  (1+\beta )(1+2 \beta )$, and binomial gives $m q (1-q)(1-2q)$.

$$
\mathrm{Skewness} = \mathrm{k3}(S) / \operatorname{Var}[S]^{1.5}
$$

## Discretizing the severity (all f_j are probabilities: never multiply them by h)
- Rounding (= "mass dispersal"; actuar calls it "rounding", its examples "midpoint"): mass of $[jh - h/2, jh + h/2)$ goes to jh:
  $f_{0} = F(h/2)$, $f_{j} = F(jh + h/2) - F(jh - h/2)$. Mean of S is off by O(h^2); VaR is accurate to about h.
- Round down ("forward difference", actuar "upper"): $f_{j} = F((j+1)h) - F(jh)$ ($f_{0}$ includes any mass at 0). S is stochastically smaller:
  E[S] drops by about E[N] h/2 and its cdf lies ABOVE the true cdf (VaR, TVaR lower bounds). Round up ("backward", actuar "lower"):
  $f_{0} = F(0)$, $f_{j} = F(jh) - F((j-1)h)$, the matching upper bounds.
- Local moment matching (Gerber 1982; actuar "unbiased"), with $L(x) = \operatorname{E}[\min (X, x)]$:
  $f_{0} = 1 - L(h)/h$, $f_{j} = (2 L(jh) - L((j-1)h) - L((j+1)h)) / h$; E[discretized $X] = \operatorname{E}[X$] exactly.
- Midpoint pitfall: the mass of a bin $[jh, (j+1)h)$ belongs to its midpoint $(j + 1/2) h$, which is NOT on the grid. Reading it as amount jh is
  the round-down method; keeping amounts at (j + 1/2)h breaks the recursion (a sum of k claims sits at $(i + k/2) h$). Always put mass on multiples of h from 0.
- $\operatorname{pdf}(jh) \cdot  h$ is only a Riemann approximation (does not sum to 1, fails when the density is infinite at 0); prefer cdf differences.
- Mass beyond the last point `(n-1)h` is either dropped or added to the last point: check it is negligible, and say which.

## Panjer recursion for the (a, b, 0) class: P(N=k) = (a + b/k) P(N=k-1), k >= 1
| $N$ | $a$ | $b$ | $\operatorname{P}(N=0)$ | $\operatorname{P}_{N}$(z) |
|---|---|---|---|---|
| Poisson(lam) | 0 | lam | $\exp ( -\mathrm{lam} )$ | $\exp (\mathrm{lam} (z - 1))$ |
| negative binomial $(r,\beta)$ | $\beta/(1+\beta)$ | $(r-1)\beta/(1+\beta)$ | $(1+\beta)^{-r}$ | $(1-\beta(z-1))^{-r}$ |
| binomial(m, q) | -q/(1-q) | (m+1) q/(1-q) | (1-q)^m | (1 + q (z - 1))^m |

$$
g_{0} = \operatorname{P}_{N}(f_{0})
$$

This is NOT $\operatorname{P}(N=0)$ unless $f_{0} = 0$.

$$
g_{k} = [1 / (1 - a f_{0})] \cdot  \sum _{j=1}^{k} (a + b j / k) f_{j} g_{k-j}
$$

For $k = 1, 2, \ldots , n-1$. Poisson case:

$$
g_{k} = (\mathrm{lam}/k) \sum _{j} j f_{j} g_{k-j}
$$

- O(n^2) operations; exact on the truncated grid (no wrap-around), only mass beyond (n-1)h is missing.
- Underflow: if $\operatorname{P}_N(f_0)$ underflows to 0 (large $\mathrm{lam}(1-f_0)$), every $g_{k}$ is 0. Run Panjer with lam / 2^k (neg. binomial: r / 2^k)
  so the start value is representable, then replace g by g * g (self-convolution, truncated to the grid) k times in a row; each step doubles lam (or r). Or use the FFT.

## FFT method
Pad $f$ with zeros to length $n$ (a power of 2 is fastest).

$$
\phi  = \mathrm{DFT}(f)
$$

Complex transform:

$$
\psi _{k} = \operatorname{P}_{N}(\phi _{k})
$$

$$
g = \mathrm{Re}(\mathrm{IDFT}(\psi ))
$$

- With numpy: $g = \mathrm{real}(\mathrm{ifft}(\operatorname{P}_{N}(\mathrm{fft}(f))))$. The circular DFT puts any mass of S beyond (n-1)h back at index `k mod n` (aliasing),
  inflating the LEFT part of g (including $g_{0}$). Choose n h so that $\operatorname{P}(S > n h)$ is negligible (check against E[S], Var[S]; heavy tails need
  much more room than mean + a few sd); compare with a run at 2n.
- Exponential tilting (Grubel & Hermesmeier 1999): use $f_{j} \exp (-\theta  j)$, apply the same steps, then multiply $g_{k}$ by $\exp (\theta  k)$.
  Wrapped mass is damped by $\exp (-\theta  n)$ but round-off is amplified by $\exp (\theta  k)$: pick $\theta$ n so that both $\exp (-\theta  n)$ and
  $\exp (\theta  n) \cdot  1e-16$ are below the tolerance (roughly 10 to 20 in double precision; too large blows up the right tail).
- $O(n \log  n)$. Works for any N with a pgf (also mixtures); Panjer and FFT give the same g up to round-off when the grid is long enough.

## VaR and TVaR from the discrete distribution

$$
G_{k} = \sum _{i\le k} g_{i}
$$

Use the smallest index $k$ such that $G_{k} \ge  p$ (allow a tiny floating-point tolerance):

$$
\operatorname{VaR}_{p} = s_{k}
$$

Coherent TVaR (Acerbi–Tasche):

$$
\mathrm{TVaR}_{p} = \operatorname{VaR}_{p} + (1/(1-p)) \sum _{k} \max (s_{k} - \operatorname{VaR}_{p}, 0) g_{k}
$$

- Variants a task may define instead: $\operatorname{E}[S \vert  S > \operatorname{VaR}_{p}]$ (sum over $s_{k} > \operatorname{VaR}_{p}$ divided by $1-G(\operatorname{VaR}_p)$) or $\operatorname{E}[S \vert  S \ge  \operatorname{VaR}_{p}]$; on a grid they
  differ from the coherent value by O(h). Interpolate between grid points only if the task says so. Report amounts k h, not indices.

## Common mistakes
- Multiplying by h twice: $f_{j}$ and $g_{k}$ are already probabilities; amounts are `k h` ($\operatorname{E}[S] = \sum _{k} k h g_{k}$). Do not scale lam, r, $\beta$ by h.
- Grid too short: Panjer silently loses tail mass ($\sum  g < 1$) and understates TVaR even when the missing mass is tiny; FFT wraps it
  to the left tail. Check $1 - \sum  g$ and $\operatorname{E}[S] - \sum  s_{k} g_{k}$ against the exact moments.
- Grid span: the representable range is n h. When n is fixed, the span is set by h. A requirement such as "n h covers a high percentile of S" is a minimum: estimate that percentile from the discrete distribution itself (a pilot FFT with a generous span) or from a simulation, not from mean + z * sd, which badly understates lognormal or Pareto tails. Then increase h (or n, when it is free) until VaR and TVaR at every requested level stop changing within the reporting precision, and the discrete mean $\sum s_{k} g_{k}$ agrees with the exact $\operatorname{E}[S]$. TVaR at level p divides the tail sum by $1-p$, so a relative shortfall of the mean of order $10^{-3}$ can become several percent in TVaR at 0.995.
- Hiding a short grid: moving the severity mass beyond the grid into the last bin, or renormalizing $f$ or $g$ to sum to 1, makes $1 - \sum g$ look clean while the tail is still cut off.
- Using $\operatorname{P}(N=0)$ as $g_{0}$ when $f_{0} > 0$; mixing up negative-binomial parametrizations ($\beta$ vs $p = 1/(1+\beta )$); severity and h in different units.
- When a Monte Carlo check disagrees by more than its own sampling error at the high levels → check in turn the grid span against the simulated high quantile and the tail mass left beyond n·h, the severity discretization, the parameters and the risk-measure definition → enlarge the span and confirm that VaR and ES no longer move before reporting.
- When choosing the grid span for heavy or skewed severities → take the starting high quantile from a pilot simulation, not from mean + z·sd, then run the mean, tail-mass and span checks of this entry and enlarge the span until VaR and ES stop moving:

```text
pilot = simulate_aggregate(n_paths)                    # same frequency and severity as the FFT
span_needed = np.quantile(pilot, 0.9999)
h = 1.5 * span_needed / n_grid                         # a starting span only
```


## Applicability and known limits
- Requires N independent of iid X. Panjer covers only (a, b, 0); zero-modified (a, b, 1) counts need a different start (Sundt & Jewell 1981),
  FFT just uses the right pgf. Discretization error shrinks as h falls (O(h) for VaR, O(h^2) for moments with rounding).
  Monte Carlo needs large samples for far-tail VaR / TVaR, especially for heavy-tailed (lognormal) severities.

## Sources
Panjer (1981) ASTIN Bulletin 12(1):22-26; Sundt & Jewell (1981) ASTIN Bulletin 12(1):27-39; Gerber (1982) Insurance: Mathematics and Economics
1(1):13-18; Grubel & Hermesmeier (1999) ASTIN Bulletin 29(2):197-214; Embrechts & Frei (2009) Math. Methods of Operations Research 69(3):497-508;
Klugman, Panjer & Willmot, Loss Models: From Data to Decisions (Wiley, 4th ed. 2012); Acerbi & Tasche (2002) J. Banking & Finance 26(7):1487-1503;
R package actuar, `discretize` documentation (Dutang, Goulet & Pigeon).
