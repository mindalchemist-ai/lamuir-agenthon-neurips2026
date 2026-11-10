NumPy 2.5.3; statsmodels 0.15.0 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: Fixed-design refits and randomization comparisons

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import itertools
import numpy as np
import statsmodels.api as sm
x=np.arange(7,dtype=float); X=np.column_stack([np.ones(7),x]); y=np.array([1.,3.,2.,5.,4.,8.,6.])
```

`np.linalg.pinv(a,rcond=...)` returns an ndarray shaped (columns,rows). With the same design, observations and weights, compute the pseudoinverse once, stack responses in rows, and use `Y @ pinv.T` for results shaped (draws,parameters). Do not reuse it after changing the design, missing-data sample or weights.
```python
P=np.linalg.pinv(X,rcond=1e-12); beta=P@y; residual=y-X@beta; Y=np.stack([y,y+residual]); batch=Y@P.T; assert np.allclose(batch[1],sm.OLS(Y[1],X).fit().params)
```
Restricted versus unrestricted wild-bootstrap fits, residual corrections and studentization follow the test definition. The preceding operation is fixed-design linear algebra, not a complete generic test. If using t statistics, recompute the appropriate standard error for every refit.

Full sign enumeration must include the identity transformation. Fixing one sign to halve the enumeration is valid only if the statistic is invariant to a global sign reversal; do not assume this generally. The example enumerates all signs and uses the absolute mean of the sign-flipped vector.
```python
signs=np.array(list(itertools.product((-1.,1.),repeat=len(y)))); stat=np.abs((signs*residual).mean(axis=1)); observed=abs(residual.mean()); identity=np.flatnonzero((signs==1).all(axis=1))[0]; tol=1e-12*max(1.,abs(observed)); hit=stat>=abs(observed)-tol; p=float(hit.mean()); assert hit[identity] and 0<=p<=1 and len(signs)==2**len(y)
```
Recomputed theoretically equal values can differ by several ulps. Compare `abs(stat)>=abs(observed)-tol`; do not exclude the identity through strict floating-point equality. Choose tolerance according to the statistic's scale and check sensitivity; it must not arbitrarily alter the test definition.

For full enumeration including the identity, directly average over the complete set. For B random draws without separately inserting the original sample, `(1+exceedance_count)/(B+1)` is common when specified by the test. Do not mechanically add one to a full enumeration. Do not use DataFrame row labels as parameter positions in a model matrix.
```python
rng=np.random.default_rng(4); draws=rng.choice([-1.,1.],size=(31,len(y))); sampled=np.abs((draws*residual).mean(axis=1)); corrected=(1+np.count_nonzero(sampled>=observed-tol))/(len(draws)+1); assert 0<corrected<=1
```

## Version check: forms that fail in this version

### Removed or renamed forms
- np.math -> Python math.
- np.trapz -> np.trapezoid.

### Unavailable or wrong-object forms
- np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
- OLSResults.cov_hac()/cov_HAC() -> get_robustcov_results(cov_type='HAC',maxlags=L,...).
- cov_hac_simple(maxlags=L) -> cov_hac_simple(nlags=L).
- ndarray.values -> the array itself.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).
- get_robustcov_results(cov_kwds=...) -> pass maxlags=L directly.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
