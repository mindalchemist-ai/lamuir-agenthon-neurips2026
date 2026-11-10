# Method: filtered historical simulation (FHS) from standardised residuals

When to use: the task instructions simulate portfolio returns by resampling standardised residuals and rescaling the
resampled residuals with each day's conditional volatilities.

```python
for t in range(T):
    sim = (Z[idx] * sigma[t]) @ w                  # Z[idx]: resampled residual rows; sigma[t]: one volatility per asset
    cut = np.percentile(sim, 100 * tail)           # tail = 0.01 for a 1% VaR; the task's quantile method if it names one
    var_fhs[t] = -cut
    es_fhs[t] = -sim[sim <= cut].mean()
```

Notes:
- One draw or one per day: draw one set of row indices `idx` and reuse it on every day when the task describes a single
  set of B bootstrap rows rescaled by each day's volatilities; draw a fresh `idx` for each day when the task says to
  resample for each day (or per window). With one seed, the per-day draws come from the same generator in day order.
- VaR cut and ES tail: linear interpolation in `np.percentile` and ES as the mean at or below the cut are one choice;
  use the quantile method and the tail inequality the task writes, and state them.

## Stationary bootstrap rows (Politis and Romano 1994)

Each row index is either a new block start drawn uniformly from 0..T-1 (always on the first row, then with probability
`p = 1 / expected block length`) or the previous index plus one, wrapping at T.

```python
rng = np.random.default_rng(seed)                  # the generator and seed the task names
idx = np.empty(B, dtype=int)
pos = int(rng.integers(0, T))                      # initial start drawn before the loop (see the table)
for i in range(B):
    if i == 0 or rng.random() < p_block:
        pos = int(rng.integers(0, T))              # new block start
    else:
        pos = (pos + 1) % T                        # continue the block
    idx[i] = pos
```

Implementations consume the random numbers in different orders, so the same seed gives different rows; each is a valid
sample of the same scheme, and VaR / ES from B rows move by sampling noise between them:

| Variant | Difference from the code above | When |
|---|---|---|
| extra initial start | the code above: one start drawn before the loop, then the first row draws again | the task names the scheme and a seed but no draw order; state it, since the plain form is equally valid |
| plain form | no draw before the loop | the task spells out this order |
| uniform on every row | `rng.random()` drawn on the first row too, before deciding | the task spells out this order |
| `arch.bootstrap.StationaryBootstrap(block_size, Z, seed=...)` | the library's internal order | the task names this class |

State the variant used.
