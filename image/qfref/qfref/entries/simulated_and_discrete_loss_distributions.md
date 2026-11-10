# Simulated and discrete loss distributions: random streams, quantiles and tail means on a grid

Use this note for value-at-risk (VaR), expected shortfall (ES, CVaR) and related backtests on return series, simulated wealth paths or simulated credit losses. Most steps below have more than one standard reading. Each skeleton takes the choice as an argument: read its value from the task instructions, and when the instructions leave it open, pick one, write the choice in a comment, and use the same choice in every output. The skeletons assume `import numpy as np`, `import pandas as pd` and `from scipy import stats, special`.

## 12. Random streams and losses on a grid

Seed the random stream once, before the simulation, with the interface the task names, and take every draw from that same stream. Two interfaces are in use and neither is the default reading of a bare seed:

```python
np.random.seed(seed); z = np.random.standard_normal(n)       # legacy RandomState (MT19937) stream
rng = np.random.default_rng(seed); z = rng.standard_normal(n)  # Generator (PCG64) stream
```

When the task gives only a seed, state which interface you chose. A sampler or loop that seeds again (calls `np.random.seed(seed)` or `np.random.default_rng(seed)` inside) restarts the stream each time: later draws repeat the first numbers, the simulated losses lose most of their variation, and simulated quantiles come out systematically too low.

A seed alone does not fix the random numbers. np.random.seed(s) with np.random.* functions uses the legacy MT19937 RandomState; np.random.default_rng(s) uses PCG64. They give different streams for the same seed. The draw order also matters: all factor draws then all idiosyncratic draws, the reverse, or one simulation at a time (factor, then that simulation's names). For losses on a grid, a quantile can move by one grid step between streams when the in-sample CDF at a grid point is close to the confidence level; print that CDF value next to the reported quantile.

```text
# the generator is created once, before the simulation; every draw below and later uses this same object
if generator == "legacy":
    np.random.seed(seed)
    draw = np.random.standard_normal
else:
    rng = np.random.default_rng(seed)
    draw = rng.standard_normal

def factor_and_name_draws(draw, n_sim, n_names, order):
    if order == "factor_first":
        M = draw(n_sim)
        E = draw((n_sim, n_names))
    elif order == "names_first":
        E = draw((n_sim, n_names))
        M = draw(n_sim)
    else:
        X = draw((n_sim, n_names + 1))
        M, E = X[:, 0], X[:, 1:]
    return M, E

def grid_quantile_report(L, level):
    var = np.quantile(L, level)
    below = L[L < var]
    return {"var": var, "cdf_at_var": float((L <= var).mean()),
            "cdf_at_next_lower": float((L <= below.max()).mean()) if below.size else 0.0}
```

## Quantiles and tail means on a discrete loss distribution

Simulated credit losses (a count of defaults or migrations times a fixed loss), aggregate losses on a monetary grid and any loss table that takes a few repeated values put large probability masses on single amounts. On such a distribution the usual readings of "VaR at level a" and "ES at level a" can differ by a whole grid step. For VaR none of the readings is the standard; read it from the task and state it. For ES the inclusive mean is the default (below).

| Quantity | Reading | Definition on a sample or pmf | Wording that selects it |
|---|---|---|---|
| VaR | order statistic | the k-th largest simulated loss with k = ceil(n * (1 - a)); equals `np.quantile(L, a, method="inverted_cdf")` | "historical" or "empirical" VaR as an order statistic, "the k-th worst outcome" |
| VaR | interpolated sample quantile | `np.quantile(L, a)` (method "linear", NumPy's default); can fall between two grid values | "quantile of the simulated losses" with no rule named, "percentile" computed by a library default |
| VaR | generalized inverse of the CDF | the smallest grid amount x with P(L <= x) >= a, accumulating pmf mass from the smallest amount | "smallest loss such that", "P(L <= VaR) >= a", a pmf or a discretized distribution |
| ES | strict tail mean | E[L \| L > VaR]; empty when VaR is the largest loss | only when the task writes "strictly greater than VaR" or a formula with a strict inequality |
| ES | inclusive tail mean | E[L \| L >= VaR]; always contains the VaR amount; the tail conditional expectation of Artzner et al. (1999), Definition 5.1 | the default when losses tie at VaR: "at or beyond VaR", and also "exceeding VaR", "beyond VaR" or "conditional on exceeding VaR" without "strictly" |
| ES | integrated quantile (tail mean) | the mean of exactly the worst (1 - a) share of probability, taking only the needed part of the VaR atom; equals min over c of c + E[max(L - c, 0)] / (1 - a) | "average of VaR over the tail", "coherent ES", "integrated quantile" |

How to choose when the wording does not decide:

- Without ties at VaR the strict and inclusive means are equal; on a grid, or with resampled or simulated losses that repeat, they can differ by a large amount and the inclusive mean is then the lower one. Report the inclusive mean unless the task writes a strict inequality or the word "strictly"; "beyond VaR" and "exceeding VaR", alone or inside a longer phrase, are not such a request. Print the strict mean and the mass at the VaR amount (`(L == var).mean()`) only as diagnostics; they do not change which value is written.
- A VaR that falls between two grid values is a sign of interpolation; a VaR equal to a grid value can come from any rule. Report `P(L <= VaR)` next to it so the reader can see which side of an atom it sits on.
- Use one quantile rule and one tail-mean rule for every level and every output that the same loss sample feeds.

```python
import numpy as np

rng = np.random.default_rng(7)
L = 0.6 * rng.binomial(20, 0.08, size=50_000)                 # losses on a grid of 0.6
a = 0.95
var_order = np.quantile(L, a, method="inverted_cdf")
var_interp = np.quantile(L, a)
amounts, counts = np.unique(L, return_counts=True)
cdf = np.cumsum(counts) / len(L)
var_inverse = amounts[np.searchsorted(cdf, a - 1e-12)]
strict, inclusive = L[L > var_order].mean(), L[L >= var_order].mean()
m = len(L) * (1 - a); worst = np.sort(L)[::-1]; j = int(np.floor(m))
integrated = (worst[:j].sum() + (m - j) * worst[j]) / m
assert var_order == var_inverse                                # the order statistic and the generalized inverse agree
assert inclusive <= integrated <= strict + 1e-12              # on a grid the three tail means are ordered
print({"cdf_at_var": float((L <= var_order).mean()), "mass_at_var": float((L == var_order).mean())})
```

## Task wording -> API arguments

Random numbers: np.random.seed(s) with np.random.normal / standard_normal / multivariate_normal uses the legacy RandomState; np.random.default_rng(s) returns a Generator whose normal, standard_normal and multivariate_normal give a different stream. Generator.multivariate_normal factorizes the covariance with method="svd" by default ("cholesky" and "eigh" change the draws).

## Sources

Jorion, Value at Risk, 3rd ed. (2007), ch. 5 (historical simulation, parametric VaR) and ch. 6 (backtesting). Acerbi and Tasche (2002), J. Banking and Finance 26(7), 1487-1503 (tail mean and conditional means at atoms). Rockafellar and Uryasev (2002), J. Banking and Finance 26(7), 1443-1471 (CVaR minimization formula). Hyndman and Fan (1996), American Statistician 50(4), 361-365 (sample quantile definitions). Boudoukh, Richardson and Whitelaw (1998), Risk 11(5), 64-67 (age-weighted historical simulation). J.P. Morgan/Reuters, RiskMetrics Technical Document, 4th ed. (1996), sec. 5.2 (EWMA). Kupiec (1995), J. Derivatives 3(2), 73-84 (proportion of failures). J.P. Morgan, CreditMetrics Technical Document (1997), ch. 8 (simulation). Docs: NumPy 2.5 numpy.quantile and Random Generator / legacy RandomState; SciPy 1.18 rv_continuous.fit, stats.t, special.xlogy; pandas 3.0 Series.ewm and Series.rolling.

## Loss by group in a simulated portfolio

For groups that partition the portfolio (initial rating, sector), two "mean loss" figures exist per group: the mean over scenarios of the group's total loss, and the mean loss of one member, smaller by the group size. A table that reports a figure for each group next to the portfolio figure is a breakdown: use the group total, so that the groups add up to the portfolio mean loss. Use the per-member mean only when the task asks for it per name, per obligor or per member of the group. An input quantity stated per bond or per name, such as a notional or a recovery amount, does not ask for it.

```python
group_total = {g: loss_by_name[:, idx].sum(axis=1) for g, idx in members.items()}   # one value per scenario
mean_loss = {g: v.mean() for g, v in group_total.items()}
assert np.isclose(sum(mean_loss.values()), loss_by_name.sum(axis=1).mean())   # the breakdown adds up
```
