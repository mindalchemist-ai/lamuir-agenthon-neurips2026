# First-passage time of drifted Brownian motion and GBM; running maximum / minimum with the terminal value

## Check first: reading "increases with the barrier", and Monte Carlo monitoring bias

**Monotonicity wording.** "P increases with the barrier" (or "decreases") means: as the barrier level rises in numeric value, with every other input fixed. It does not mean "as the barrier moves away from the start" or "in the order the levels are listed". For a running maximum, P(max >= H) cannot increase as H rises; for a running minimum, P(min <= L) cannot decrease as L rises (a higher lower barrier is closer to the start from below); both hitting probabilities cannot decrease as the horizon T grows. Compute any monotonicity flag on levels sorted in increasing numeric order, and allow ties: probabilities equal to rounding, or zero and one at extreme levels, still satisfy "does not decrease".

**Monte Carlo against the formula.** A path simulated on a time grid and checked only at grid dates misses crossings between dates, so discrete monitoring gives hitting probabilities that are too low and first-passage times that are too long, by an amount that shrinks roughly with the square root of the step. Before reporting a Monte Carlo comparison, either use a fine step, or add the Brownian-bridge crossing probability between grid points, exp(-2 (b - x_i)(b - x_{i+1}) / (sigma^2 dt)) for a barrier b above both points, and check that the remaining gap to the closed form is within a few Monte Carlo standard errors.

```python
import numpy as np
from scipy.stats import norm

def p_max_ge(m, x0, mu, sig, T):             # P(max_{t<=T} X_t >= m) for X_t = x0 + mu t + sig W_t, m > x0
    a = m - x0
    return norm.cdf((-a + mu * T) / (sig * np.sqrt(T))) + np.exp(2 * mu * a / sig**2) * norm.cdf((-a - mu * T) / (sig * np.sqrt(T)))

def p_min_le(l, x0, mu, sig, T):             # by symmetry: the minimum of X is minus the maximum of -X
    return p_max_ge(-l, -x0, -mu, sig, T)

def nondecreasing(levels, probs, tol=1e-12):
    order = np.argsort(levels)
    return bool(np.all(np.diff(np.asarray(probs)[order]) >= -tol))

x0, mu, sig, T = 0.0, 0.05, 0.2, 1.0
ups, downs = [0.3, 0.1, 0.2], [-0.3, -0.1, -0.2]          # listed in no particular order
assert nondecreasing([-m for m in ups], [p_max_ge(m, x0, mu, sig, T) for m in ups])   # P(max >= H) falls as H rises
assert nondecreasing(downs, [p_min_le(l, x0, mu, sig, T) for l in downs])            # P(min <= L) rises as L rises

rng = np.random.default_rng(0); n, steps, b = 100_000, 250, 0.2
dt = T / steps; X = np.cumsum(mu * dt + sig * np.sqrt(dt) * rng.standard_normal((n, steps)), axis=1)
prev = np.hstack([np.zeros((n, 1)), X[:, :-1]])
hit_grid = (X >= b).any(axis=1)
bridge = np.exp(-2 * np.clip(b - prev, 0, None) * np.clip(b - X, 0, None) / (sig**2 * dt))
hit_bridge = 1 - np.prod(1 - np.where((prev < b) & (X < b), bridge, 1.0), axis=1)
exact = p_max_ge(b, x0, mu, sig, T)
assert hit_grid.mean() < exact                                       # grid monitoring misses crossings
assert abs(hit_bridge.mean() - exact) < 4 * np.sqrt(exact * (1 - exact) / n)
```

**If the task text defines the formula, inputs or conventions differently, the task text wins.**

## Model and assumptions
- Arithmetic Brownian motion $X_{t} = \mathrm{x0} + \mu  t + \sigma  W_{t}$, constant $\mu , \sigma  > 0$. Level b (upper if $b > \mathrm{x0}$, lower if $b < \mathrm{x0}$).
  $\tau  = \inf \{t \ge  0 : X_{t} = b\}$; for continuous paths "reaches", "touches" and "crosses" are the same event. If x0 is at or beyond $b, \tau  = 0$.
- GBM $S_{t} = \mathrm{S0} \exp (\nu  t + \sigma  W_{t})$ with $\nu  = m - \sigma ^{2}/2$, where m is the drift of dS/S (risk-neutral: $m = r - q$; real-world: expected return).
  Then $X = \ln  S$ is the model above with $\mathrm{x0} = \ln  \mathrm{S0}$, $\mu  = \nu$, $b = \ln  H$.
- One level, continuous monitoring, constant coefficients. Exit from a corridor (two levels) is NOT covered by these formulas.

## Parameters and units
| symbol | meaning | units |
|---|---|---|
| x0, b | start value and level of X (for GBM: $\ln  \mathrm{S0}, \ln  H$) | units of X |
| $\mu$, $\sigma$ | drift and volatility of X; $\sigma$ of 30% is `0.30` | per year, per $\sqrt{\mathrm{year}}$ |
| $a$ | distance to the level, $a = \mathrm{abs}(b - \mathrm{x0}) > 0$ | units of X |
| $\theta$ | drift TOWARDS the level: $\theta  = \mu$ if b > x0, $\theta  = -\mu$ if b < x0 | per year |
| $t, T$ | horizon in years (same time unit as $\mu$ and $\sigma^{2}$) | years |

## First-passage law (N = standard normal cdf)
For $t > 0$:

$$
\operatorname{P}(\tau  \le  t) = N((\theta  t - a) / (\sigma  \sqrt{t})) + \exp (2 \theta  a / \sigma ^{2}) \cdot  N((-\theta  t - a) / (\sigma  \sqrt{t}))
$$

Density of $\tau$ on $t > 0$:

$$
f(t) = a / (\sigma  \sqrt{2 \pi  t^{3}}) \cdot  \exp (-(a - \theta  t)^{2} / (2 \sigma ^{2} t))
$$

For $\theta  \ge  0$, $\operatorname{P}(\tau  < \infty ) = 1$. For $\theta  < 0$:

$$
\operatorname{P}(\tau  < \infty ) = \exp (-2 \mathrm{abs}(\theta ) a / \sigma ^{2})
$$

- f integrates to $\operatorname{P}(\tau  < \infty )$, so it is a defective density when $\theta  < 0$. Evaluate the second CDF term as
  $\exp (2 \theta  a / \sigma ^{2} + \log  N(\ldots ))$ to avoid overflow when $\theta a/\sigma^2$ is large.
- $\theta  > 0$: $\tau$ is inverse Gaussian with mean $a / \theta$ and shape $a^{2} / \sigma ^{2}$; $\operatorname{Var}(\tau ) = a \sigma ^{2} / \theta ^{3}$.
  $\theta  < 0$: conditional on $\tau  < \infty , \tau$ has the same law with $\mathrm{abs}(  \theta  )$. $\theta  = 0$: $\operatorname{P}(\tau  \le  t) = 2 N(-a / (\sigma  \sqrt  t))$,
  $\tau  < \infty$ almost surely but E[$\tau$] is infinite.
- GBM: $a = \mathrm{abs}(\ln (H / \mathrm{S0}))$, $\theta  = \nu$ for $H > \mathrm{S0}$ and -$\nu$ for $H < \mathrm{S0}$. Ever hitting H: $\operatorname{P} = \min (1, (H / \mathrm{S0})^{2 \nu  / \sigma ^{2}})$.

## Running maximum / minimum with the terminal value
Let $M_{T} = \max _{0\le s\le T} X_{s}$, $L_{T} = \min _{0\le s\le T} X_{s}$, and shift to the start: $m' = m - \mathrm{x0}$, $l' = l - \mathrm{x0}$, $y = x - \mathrm{x0}$, $s = \sigma  \sqrt  T$.
For $m' \ge  0, y \le  m'$:

$$
\operatorname{P}(M_{T} \ge  m, X_{T} \le  x) = \exp (2 \mu  m' / \sigma ^{2}) N((y - 2 m' - \mu  T) / s)
$$

$$
\operatorname{P}(M_{T} \le  m, X_{T} \le  x) = N((y - \mu  T) / s) - \exp (2 \mu  m' / \sigma ^{2}) N((y - 2 m' - \mu  T) / s)
$$

$$
\operatorname{P}(M_{T} \le  m) = N((m' - \mu  T) / s) - \exp (2 \mu  m' / \sigma ^{2}) N((-m' - \mu  T) / s) = 1 - \operatorname{P}(\tau _{m} \le  T)
$$

For $l' \le  0, y \ge  l'$:

$$
\operatorname{P}(L_{T} \ge  l, X_{T} \ge  x) = N((\mu  T - y) / s) - \exp (2 \mu  l' / \sigma ^{2}) N((2 l' - y + \mu  T) / s)
$$

Joint density of $(M_{T}, X_{T})$ at $(m', y)$, where $m' \ge  \max (0, y)$:

$$
2 (2 m' - y) / (\sigma ^{3} \sqrt{2 \pi  T^{3}}) \cdot  \exp (-(2 m' - y)^{2} / (2 \sigma ^{2} T) + \mu  y / \sigma ^{2} - \mu ^{2} T / (2 \sigma ^{2}))
$$

- For $\operatorname{P}(M_T\le m,X_T\le x)$ only: when $y>m'$, replace $y$ by $m'$; when $m'<0$, this probability is zero.
- For $\operatorname{P}(M_T\ge m,X_T\le x)$, the two shortcuts differ. If $m'\le0$, the maximum condition is automatic and the probability is $N((y-\mu T)/s)$. If $m'>0$ and $y>m'$, use:

$$
\operatorname{P}(M_T\ge m,X_T\le x)
=e^{2\mu m'/\sigma^2}N((-m'-\mu T)/s)
+N((y-\mu T)/s)-N((m'-\mu T)/s).
$$

  The added CDF difference counts endpoints above the barrier, which necessarily crossed it. Minimum formulas follow by applying the corresponding maximum event to $-X$ with drift $-\mu$. For GBM map every price level into logs and use log drift $\nu$.
- Dependence on the level and the horizon (any drift): if $\mathrm{l1} < \mathrm{l2}$, the event "running minimum <= l1" implies "running minimum
  <= l2", so $\operatorname{P}(L_{T} \le  l)$ does not decrease as l rises; a lower level is harder to reach. Likewise $\operatorname{P}(M_{T} \ge  m)$ does not
  increase as m rises, and both hitting probabilities do not decrease as T grows (a longer window contains the shorter one).
  To check, state the event first, sort the levels (or horizons) in increasing numeric order, hold every other input fixed
  and compare the probabilities in that order.

## Conditional hitting given the endpoints (Brownian bridge)
Given $X_{u} = x_{u}$ and $X_{v} = x_{v}$ ($v > u$), both strictly on the starting side of b:

$$
\operatorname{P}(\mathrm{path} \mathrm{touches} b \mathrm{on} [u, v] \vert  x_{u}, x_{v}) = \exp (-2 (b - x_{u})(b - x_{v}) / (\sigma ^{2} (v - u)))
$$

It does not depend on $\mu$; it is 1 if either endpoint is at or beyond b. The same expression holds for a lower level. For GBM use logs and log-vol.

## Monte Carlo, never-hit paths and empirical CDFs
- Simulate X exactly on a grid of step dt (GBM in logs). For each step compute the bridge probability $p_{k}$. Either draw $U < p_{k}$ to flag a
  hit in that step ($\tau$ is then known only to within dt), or carry the survival weight $\prod _{k} (1 - p_{k})$: its mean estimates
  $\operatorname{P}(\tau  > t_{k})$ and $\operatorname{E}[1\{X_{T} \le  x\} \prod  (1 - p_{k})]$ estimates $\operatorname{P}(M_{T} \le  b, X_{T} \le  x)$, both without discretization bias at grid times.
- A plain check "a grid point is beyond b" misses crossings between grid points and underestimates hitting by order $\sigma  \sqrt{\mathrm{d}t}$.
- Paths that do not hit by the horizon have $\tau  = +\infty$(censored at T). Empirical CDF: $F(t) = \#\{i : \tau _{i} \le  t\} / N_{\mathrm{all}}$, with $N_{\mathrm{all}}$
  counting EVERY path. Do not drop never-hit paths (that gives $\operatorname{P}(\tau  \le  t \vert  \tau  \le  T)$, which reaches 1 at T); do not set them to T
  (a false atom at T); do not average $\tau$ over a sample containing inf, or with nanmean.
- E[$\tau$] is finite only for $\theta  > 0 (= a / \theta )$. Otherwise report what the task defines: $\operatorname{P}(\tau  \le  T)$,
  $\operatorname{E}[\tau  \vert  \tau  \le  T] = (\int _{0}^{T} t f(t) \mathrm{d}t) / \operatorname{P}(\tau  \le  T)$, or $\operatorname{E}[\min (\tau , T)] = \int _{0}^{T} \operatorname{P}(\tau  > t) \mathrm{d}t$.
  A quantile q of $\tau$ exists only for $q < \operatorname{P}(\tau  < \infty )$(within the horizon: $q \le  \operatorname{P}(\tau  \le  T)$).

## Discrete monitoring
- If the level is checked only at dates spaced dt (e.g. daily closes), the discrete probability is the target: simulate on those dates
  without bridge correction, or use the continuous formula with the level moved AWAY from the start (Broadie-Glasserman-Kou):
  $b' = b + \beta  \sigma  \sqrt{\mathrm{d}t}$ for an upper level, $b - \beta  \sigma  \sqrt{\mathrm{d}t}$ for a lower level (GBM: $H \exp (\pm \beta  \sigma  \sqrt{\mathrm{d}t})$),
  $\beta  = -\zeta (1/2) / \sqrt{2 \pi} \approx 0.5826$. Never compare a discretely monitored simulation with the continuous formula directly.
- The shift is an asymptotic correction: it is less accurate with few monitoring dates or when the start is within a few $\sigma  \sqrt{\mathrm{d}t}$ of the level.

## Drift and probability checks before interpretation

For GBM, distinguish the return drift $m$ in $\mathrm{d}S/S=m\,\mathrm{d}t+\sigma\,\mathrm{d}W$ from log drift $\nu=m-\sigma^2/2$. If the supplied drift is already $\nu$, the exact log increment is $\Delta\log S=\nu\Delta t+\sigma\sqrt{\Delta t}Z$; subtracting another $\sigma^2/2$ changes the model. Keep these two inputs separately named.

First check probabilities lie in $[0,1]$, a CDF is nondecreasing in time, and time-zero hits match the starting side. Under the same process and barrier, discrete-date hitting is a subset of continuous hitting. A Monte Carlo excess over the continuous probability needs assessment against its sampling standard error; a material excess calls for checking drift, event direction, endpoints and monitoring before attributing the gap to noise. Lower touches use $S_t\le H$; upper touches use $S_t\ge H$.

## Variants and common mistakes
- GBM: using m instead of $\nu  = m - \sigma ^{2}/2$, or the price distance H - S0 instead of $\ln (H/\mathrm{S0})$.
- Wrong sign of $\theta$ for a lower level; time units of t inconsistent with annualized $\mu$, $\sigma$.
- Terminal probability $\operatorname{P}(X_{T} \ge  b)$ is not the hitting probability (for $\mu  = 0$ hitting is twice the terminal probability: reflection principle).

## Applicability and known limits
- Exact for constant drift and volatility with continuous monitoring. Jumps, stochastic or time-varying volatility, mean reversion
  (OU) and two-sided barriers need other formulas or simulation; the bridge probability assumes Brownian motion within each step.

## Sources
Shreve (2004) Stochastic Calculus for Finance II, Springer (Sec. 7.2, maximum of Brownian motion with drift); Borodin & Salminen (2002)
Handbook of Brownian Motion: Facts and Formulae, 2nd ed., Birkhauser; Chhikara & Folks (1978) J. R. Statist. Soc. B 40:263-289 (inverse Gaussian);
Beaglehole, Dybvig & Zhou (1997) Financial Analysts Journal 53(1):62-68 and Glasserman (2004) Monte Carlo Methods in Financial Engineering,
Springer (Brownian-bridge correction); Broadie, Glasserman & Kou (1997) Mathematical Finance 7(4):325-349 (continuity correction).
