# Method: scalar DCC(1,1) correlations on GARCH residuals

When to use: the task instructions estimate dynamic conditional correlations (DCC) for several assets from univariate
GARCH fits.

Standardised residuals: column i of `Z` is `res_i.std_resid` from asset i's univariate fit (arch conventions entry,
section 4). They have no unit: a fit on percent returns gives the same `std_resid` as one on decimal returns, so do
not divide them by 100. Check before fitting the correlations:

```python
assert np.allclose(Z.std(axis=0), 1, atol=0.2)     # each column has a standard deviation near 1
```
 `sigma[t]` is the vector of the assets' conditional volatilities in decimal units on day t.

With `z_t` the rows of `Z` (T x N): `Qbar = Z.T @ Z / T`, `Q_1 = Qbar`,
`Q_t = (1 - a - b) * Qbar + a * z_{t-1} z_{t-1}' + b * Q_{t-1}`, `R_t = diag(Q_t)^{-1/2} Q_t diag(Q_t)^{-1/2}`.
Which log-likelihood to report (all three have the same optimum `a, b`; the reported values differ by large amounts):

| Reported likelihood | Formula per day t | When |
|---|---|---|
| correlation component `L_C` (Engle 2002, second step) | `-0.5 * (log det R_t + z_t' R_t^{-1} z_t - z_t' z_t)` | a "DCC log-likelihood", "correlation-stage" or "second-step" likelihood with no formula given; this is the code below |
| correlation part without `z_t' z_t` | `-0.5 * (log det R_t + z_t' R_t^{-1} z_t)` | only when the task writes this formula |
| full (joint) log-likelihood | `-0.5 * (N log 2pi + 2 log det D_t + log det R_t + z_t' R_t^{-1} z_t)`, `D_t = diag(sigma_t)` | "total", "joint" or "full" log-likelihood, or a sum of the GARCH and correlation stages |


```python
def dcc_ll(a, b, Z):
    T, N = Z.shape; Qbar = Z.T @ Z / T; Q = Qbar.copy(); ll = 0.0
    for t in range(T):
        if t > 0:
            Q = (1 - a - b) * Qbar + a * np.outer(Z[t-1], Z[t-1]) + b * Q
        d = 1 / np.sqrt(np.diag(Q)); R = Q * np.outer(d, d)
        sign, logdet = np.linalg.slogdet(R)
        ll += -0.5 * (logdet + Z[t] @ np.linalg.solve(R, Z[t]) - Z[t] @ Z[t])
    return ll
def nll(x):
    a, b = x
    return 1e10 if a + b >= 0.9999 else -dcc_ll(a, b, Z)   # finite penalty: L-BFGS-B differences an inf or nan into a false stop
fit = minimize(nll, x0=[0.05, 0.93], bounds=[(1e-6, 0.9999), (1e-6, 0.9999)], method="L-BFGS-B")
a, b = fit.x; log_likelihood = -fit.fun
assert np.allclose(Z.std(axis=0), 1, atol=0.2) and a + b < 1
```

Notes:
- Use the optimizer and starting values the task instructions name; the ones above are an example.
- Keep the objective finite everywhere the optimizer may step: return a large number such as `1e10` outside the region, not `inf` or `nan`; then check that the fit reports success and moved from the starting values.
- Report the likelihood at the optimum, in the form chosen from the table; dropping `z_t' z_t` shifts it by about `-T * N / 2`.
- Portfolio volatility on day t: `ws = sigma[t] * w`, `sigma_p[t] = np.sqrt(ws @ R_t @ ws)`; portfolio return `r @ w`
  from the same return series the volatilities were fitted on.
