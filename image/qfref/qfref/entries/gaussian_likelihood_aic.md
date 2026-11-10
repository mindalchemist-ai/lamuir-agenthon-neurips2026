# Gaussian likelihoods and information criteria for return models

Use this when a task fits several return models (random walk, drifted random walk or GBM, mean-reverting AR(1)/OU, jump mixtures) by likelihood and compares them with AIC or BIC. If the task text defines a formula, a parameter count or a variance estimator, the task text wins.

## Check first

1. **The variance term is part of the likelihood.** For n observations r_t with model mean m_t and variance s^2, the Gaussian negative log-likelihood is

   NLL = 0.5 * n * log(2 * pi) + 0.5 * n * log(s^2) + sum((r_t - m_t)^2) / (2 * s^2).

   Dropping 0.5 * n * log(s^2) (keeping only the squared-error sum) makes models with different variances incomparable and usually picks the wrong one. Dropping the constant 0.5 * n * log(2 * pi) is harmless only when every compared model drops it.
2. **Which variance estimate goes with which mean.** The maximum-likelihood variance is the mean of squared residuals around the fitted mean: for a zero-drift model (martingale, driftless random walk) it is mean(r^2) when the task leaves the variance to the likelihood; when the task prescribes a population (ddof=0) standard deviation for that model's sigma, use std(r, ddof=0) as written (it is centred on the sample mean) while the model's mean stays zero, and say so in a comment; for a drifted model it is mean((r - mean(r))^2), the ddof=0 variance. At the MLE the last term of the NLL equals n / 2. A task that prescribes a ddof=1 standard deviation for a parameter changes the plugged-in value; use it as written and say so.
3. **AIC = 2 k + 2 NLL and BIC = k log(n) + 2 NLL, with k the number of fitted parameters** (a variance counts; a parameter fixed in advance does not). When the task does not list k for each model, write the count used per model in a comment. All models must be scored on the same observations: a model whose likelihood conditions on a lagged value either adds the first observation's stationary likelihood or all models drop that observation. Print the number of terms each model's NLL sums and check they are all the same n: for AR(1)/OU that is n - 1 conditional residuals plus one stationary term for the first observation. A likelihood helper that sums over the full return series, reused with a residual mean or for the first observation alone, sums the wrong terms.
4. **Nested models.** When model B contains model A as a special case and both are fitted by maximum likelihood on the same data, B's NLL cannot be larger than A's (B can reproduce A). A larger NLL for the bigger model means a missing term, a different sample or a failed optimizer.
5. **AR(1) to OU mapping.** theta = -log(phi) / dt is defined only for 0 < phi < 1. When the fitted phi falls outside, the common choice is to clip phi into the interval (a small positive floor and a cap just below 1) and recompute the intercept and residuals with the clipped value, so that theta, the half-life and the stationary first term stay defined and the OU fit stays in the comparison. Leave the OU fit out of the comparison only when the task says so. State the choice in a comment.

```python
import numpy as np

def gauss_nll(resid, var):
    n = len(resid)
    return 0.5 * n * np.log(2 * np.pi) + 0.5 * n * np.log(var) + np.sum(resid**2) / (2 * var)

def aic(k, nll):
    return 2 * k + 2 * nll

rng = np.random.default_rng(0)
r = 0.0004 + 0.01 * rng.standard_normal(500)
nll_zero = gauss_nll(r, np.mean(r**2))                           # zero drift: k = 1 (variance)
nll_drift = gauss_nll(r - r.mean(), np.mean((r - r.mean())**2))  # drift + variance: k = 2
assert nll_drift <= nll_zero + 1e-9                              # nested: the larger model is never worse
assert np.isclose(np.sum((r - r.mean())**2) / (2 * np.mean((r - r.mean())**2)), len(r) / 2)
assert gauss_nll(r, np.mean(r**2)) < gauss_nll(r, 4 * np.mean(r**2))   # the log-variance term matters
print(aic(1, nll_zero), aic(2, nll_drift))

# AR(1) exact likelihood: n - 1 conditional residuals plus the first observation under the stationary law
x, y = r[:-1], r[1:]
phi = float(np.cov(x, y, ddof=0)[0, 1] / np.var(x))
c = y.mean() - phi * x.mean()
e = y - (c + phi * x)
s2 = np.mean(e**2)
first = r[:1] - c / (1 - phi)
nll_ar = gauss_nll(e, s2) + gauss_nll(first, s2 / (1 - phi**2))
terms = {"zero": len(r), "drift": len(r), "ar1": len(e) + len(first)}
print(terms, aic(3, nll_ar))
assert len(set(terms.values())) == 1                             # every model scored on the same n observations
```

## Sources

Hamilton, Time Series Analysis (1994), ch. 5 (maximum likelihood for Gaussian AR models, conditional and exact likelihood); Akaike (1974), IEEE Trans. Automatic Control 19(6), 716-723; Schwarz (1978), Annals of Statistics 6(2), 461-464; Burnham and Anderson, Model Selection and Multimodel Inference, 2nd ed. (2002), ch. 2 (counting parameters, same data for all models).
