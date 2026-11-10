NumPy 2.5.3; statsmodels 0.15.0 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Regressions, coefficient indexing and robust errors

Build the intercept as specified. fit(cov_type='HAC',cov_kwds={'maxlags':L,'use_correction':False}) nests keywords; get_robustcov_results(cov_type='HAC',maxlags=L,use_correction=False) takes them directly. Bartlett is default; False omits T/(T-k). Set use_t explicitly. Robust-result params/tvalues are arrays: map model.exog_names. A sample-mean long-run variance with 1/T autocovariances is a different estimator, not an OLS shortcut.

```python
import numpy as np, statsmodels.api as sm
x=np.arange(8.); X=np.column_stack([np.ones(8),x]); y=x+np.sin(x)
r=sm.OLS(y,X).fit(); h=r.get_robustcov_results(cov_type='HAC',maxlags=1,use_correction=False,use_t=False)
assert h.params.shape==(2,)
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: cov_hac/cov_HAC -> robust results. cov_hac_simple: maxlags -> nlags. robust results: nested cov_kwds -> direct maxlags.
