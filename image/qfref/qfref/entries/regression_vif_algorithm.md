# Variance inflation factor (VIF) from auxiliary OLS regressions
The task description inside <task_instructions> takes priority over this card: where it gives a different formula, input or convention, follow the task description.

The VIF of regressor $x_j$ measures how well the other regressors explain it: regress $x_j$ on all other regressors plus an intercept, take the centred $R^2_j$, and $\mathrm{VIF}_j = 1/(1-R^2_j)$. The usual error is computing $R^2$ from the wrong residual quantity.

```text
1. Input: regressor matrix $X$ (T rows, p columns, no constant column), aligned rows, no NaN.
2. For each column j:
   a. y = X[:, j];  Z = [1, X without column j]  (intercept first).
   b. beta = np.linalg.lstsq(Z, y, rcond=None)[0]   (take ONLY element 0, the coefficients).
   c. e = y - Z @ beta                              (residual vector, length T).
   d. SSR = sum(e^2);  SST = sum((y - mean(y))^2)   (centred total sum of squares).
   e. $R^2_j = 1 - SSR/SST$;  $\mathrm{VIF}_j = 1/(1 - R^2_j)$  (inf if $R^2_j = 1$).
3. Equivalent cross-checks (use one to verify, not to replace the task's method):
   - `statsmodels.api.OLS(y, sm.add_constant(Z_no_const)).fit().rsquared`;
   - $\mathrm{VIF}_j$ = j-th diagonal element of the inverse correlation matrix of X.
```

Note on `np.linalg.lstsq`: its second output is already the residual sum of squares (an array of shape (1,) for a 1-D target, empty if the system is rank-deficient), not the residual vector. Squaring it or summing its square gives a meaningless number that is far too small and pushes $R^2$ toward 1.

Checks:
- $1 \le \mathrm{VIF}_j$ for every j, and $0 \le R^2_j < 1$.
- VIF from step 2 matches the inverse-correlation-matrix diagonal to about 1e-8 relative.
- Pairwise correlations of the regressors are consistent: if all $|\rho| $ are small, no VIF should be large.
