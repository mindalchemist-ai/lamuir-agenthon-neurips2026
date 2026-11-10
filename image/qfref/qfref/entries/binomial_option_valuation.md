# Binomial valuation and exercise opportunities

## Check first: carry rate b, rate r and yield q

Many option texts write the drift with a cost-of-carry rate b instead of a yield. The three are tied by b = r - q:

| underlying | carry b | yield q = r - b |
|---|---|---|
| stock without dividends | r | 0 |
| stock or index with continuous yield q | r - q | q |
| futures or forward contract | 0 | r |
| foreign currency (foreign rate r_f) | r - r_f | r_f |

On a CRR tree the expected one-step growth of the underlying is exp(b * dt) = exp((r - q) * dt), and every step is discounted with exp(-r * dt). So the up-probability is p = (exp(b * dt) - d) / (u - d). A factor exp((r - b) * dt) is exp(q * dt): it grows the underlying at the yield, not at the carry. When a task gives b, convert it once to q = r - b and use the rest of this note unchanged.

Before pricing an American option, price a European option on the same tree with b = r (no yield) and compare it with Black-Scholes; then repeat with the task's b against the Black-Scholes price with yield q = r - b.

```python
import numpy as np
from scipy.stats import norm

def bs(S, K, T, r, q, sig, call=True):
    d1 = (np.log(S / K) + (r - q + 0.5 * sig**2) * T) / (sig * np.sqrt(T)); d2 = d1 - sig * np.sqrt(T)
    if call:
        return S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)

def crr_european(S, K, T, r, b, sig, n, call=True):
    dt = T / n; u = np.exp(sig * np.sqrt(dt)); d = 1 / u
    p = (np.exp(b * dt) - d) / (u - d)                       # growth at the carry b, not at r - b
    ST = S * u ** np.arange(n, -1, -1) * d ** np.arange(0, n + 1)
    V = np.maximum(ST - K, 0) if call else np.maximum(K - ST, 0)
    for _ in range(n):
        V = np.exp(-r * dt) * (p * V[:-1] + (1 - p) * V[1:])
    return V[0]

S, K, T, r, sig = 100.0, 100.0, 0.5, 0.05, 0.25
for b in (r, 0.0, r - 0.03):                                 # no yield, futures, yield 3%
    for call in (True, False):
        assert abs(crr_european(S, K, T, r, b, sig, 2000, call) - bs(S, K, T, r, r - b, sig, call)) < 2e-2

def crr_american(S, K, T, r, b, sig, n, call=True):
    dt = T / n; u = np.exp(sig * np.sqrt(dt)); d = 1 / u
    p = (np.exp(b * dt) - d) / (u - d)
    ST = S * u ** np.arange(n, -1, -1) * d ** np.arange(0, n + 1)
    V = np.maximum(ST - K, 0) if call else np.maximum(K - ST, 0)
    for j in range(n - 1, -1, -1):                           # step back to time j, which has j + 1 nodes
        Sj = S * u ** np.arange(j, -1, -1) * d ** np.arange(0, j + 1)   # node prices rebuilt at each step, same descending order
        V = np.exp(-r * dt) * (p * V[:-1] + (1 - p) * V[1:])
        V = np.maximum(V, Sj - K if call else K - Sj)         # early exercise against the node's own price
    return V[0]

assert abs(crr_american(S, K, T, r, r, sig, 2000, True) - crr_european(S, K, T, r, r, sig, 2000, True)) < 1e-8   # no yield: American call = European call
```

Use this reference for a CRR stock-price tree and European, Bermudan or American exercise under constant rates, continuous dividend yield and volatility. It supplies numerical pricing mathematics, not a replacement for a specifically requested PDE or analytical approximation.

## Conventions and notation

Explicit task definitions take precedence. S0 is current stock price, K is strike, r is the continuously compounded rate, q is continuous dividend yield, $\sigma  > 0$ is annualized volatility, $T > 0$ is remaining maturity, and n is the number of equal time intervals. Rates and volatility are decimal quantities. Node (i,j) means time i*dt and j upward moves, with $0 \le  j \le  i$. Cash dividends require separate event treatment and are not equivalent to a constant q.

## Transition model

Time interval:

$$
\mathrm{d}t = T/n
$$

CRR upward and downward stock multipliers:

$$
\begin{gathered}
u = \exp (\sigma \cdot \sqrt{\mathrm{d}t}) \\
d = 1/u
\end{gathered}
$$

Stock price at a recombining node:

$$
S_{i,j} = \mathrm{S0} \cdot  u^{j} \cdot  d^{i-j}
$$

The pricing probability matches the stock's risk-neutral growth after continuous dividend yield:

$$
p = (\exp ((r-q)\cdot \mathrm{d}t)-d)/(u-d)
$$

An arbitrage-free nondegenerate step requires $d < \exp ((r-q)\cdot \mathrm{d}t) < u$. A probability outside [0,1] indicates an invalid discretization; clipping changes the model. This probability is unrelated to an estimated historical upward-return frequency.

## Payoffs and stopping

Call exercise payoff:

$$
g_{\mathrm{call}}(S) = \max (S-K,0)
$$

Put exercise payoff:

$$
g_{\mathrm{put}}(S) = \max (K-S,0)
$$

Terminal value for the selected payoff g:

$$
V_{n,j} = g(S_{n,j})
$$

Continuation value H at an earlier node:

$$
H_{i,j} = \exp (-r\cdot \mathrm{d}t) \cdot  [p\cdot V_{i+1,j+1} + (1-p)\cdot V_{i+1,j}]
$$

Value when exercise is permitted at that node:

$$
V_{i,j} = \max (g(S_{i,j}),H_{i,j})
$$

Value when exercise is not permitted:

$$
V_{i,j} = H_{i,j}
$$

European exercise is only at expiry; Bermudan exercise uses specified dates; American tree exercise is available at every time node. The latter approximates continuous exercise as the time spacing shrinks. An exercise boundary represents positive exercise payoff that dominates continuation; zero-payoff ties are not evidence of economic early exercise.

## Checks and limits

On the same tree and contract, adding exercise opportunities cannot lower value. A non-dividend-paying call with nonnegative interest rates equals its European counterpart. European call-put parity holds on the tree. Convergence to a diffusion price can oscillate as strike alignment changes; more time steps need not improve every individual error monotonically.

At $\sigma =0$ the stock path is deterministic and the probability formula is singular: value follows from discounted contractual cash flows and allowed exercise times. At expiry the value is the payoff. The plain stock-only state does not retain running extrema or averages, so it is insufficient for path-dependent payoffs without additional state.

## Source and derivation

[Cox, Ross and Rubinstein (1979), Option Pricing: A Simplified Approach](https://bpb-us-w2.wpmucdn.com/u.osu.edu/dist/7/36891/files/2017/07/CRR79-1yy8av8.pdf), sections 3, 5 and 6: recombining valuation, diffusion limit and early exercise. The continuous-yield probability here follows directly from $p\cdot u+(1-p)\cdot d=\exp ((r-q)\cdot \mathrm{d}t)$; notation uses continuous annual rates rather than the paper's one-period gross return.
