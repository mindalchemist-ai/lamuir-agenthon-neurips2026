# Method: rolling VaR backtest and coverage tests

When to use: the task instructions forecast VaR over a rolling window and test the violations: the Kupiec test of the
violation rate, the Christoffersen test of independence between days, and the conditional coverage test that sums the Kupiec statistic and the Christoffersen statistic.

## 1. Rolling forecasts and violations

For each day `i` in `range(W, N)`: fit on the window `[i - W, i)` only, forecast the VaR of day `i`, and record a
violation when the loss of day `i` is strictly greater than the VaR of day `i`. For a GARCH-based VaR, refit on each window and use
the one-step-ahead forecast of the window fit (`sigma_next`, arch conventions entry, section 2).

## 2. Coverage tests on the T forecast days

`viol` is the 0/1 violation series, `tail` the expected violation rate, which is the tail probability (`tail = 1 - level`, arch conventions entry, section 5).

```python
xlx = lambda k, q: 0.0 if k == 0 else k * np.log(q)             # 0 * log 0 = 0
viol = np.asarray(viol)[-T:]                                      # only the T forecast days, not the estimation window
assert len(viol) == T
x = int(viol.sum()); pi = x / T
lr_uc = -2 * (xlx(x, tail) + xlx(T - x, 1 - tail) - xlx(x, pi) - xlx(T - x, 1 - pi))
n00 = n01 = n10 = n11 = 0
for a, b in zip(viol[:-1], viol[1:]):                             # transitions between consecutive days
    n00 += a == 0 and b == 0; n01 += a == 0 and b == 1; n10 += a == 1 and b == 0; n11 += a == 1 and b == 1
p01 = n01 / (n00 + n01) if n00 + n01 else 0.0
p11 = n11 / (n10 + n11) if n10 + n11 else 0.0
p_all = (n01 + n11) / (n00 + n01 + n10 + n11)
l0 = xlx(n00 + n10, 1 - p_all) + xlx(n01 + n11, p_all)
l1 = xlx(n00, 1 - p01) + xlx(n01, p01) + xlx(n10, 1 - p11) + xlx(n11, p11)
lr_ind = -2 * (l0 - l1); lr_cc = lr_uc + lr_ind
p_uc, p_ind, p_cc = chi2.sf(lr_uc, 1), chi2.sf(lr_ind, 1), chi2.sf(lr_cc, 2)
```

Notes:
- A single violation not followed by another gives `n11 = 0` and a small but non-zero `lr_ind`.
