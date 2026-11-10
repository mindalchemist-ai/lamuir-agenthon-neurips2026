NumPy 2.5.3; pandas 3.0.5; statsmodels 0.15.0 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: statsmodels: regression, HAC and diagnostics

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.stattools import durbin_watson
rng=np.random.default_rng(21)
df=pd.DataFrame({'feature':rng.normal(size=24)},index=np.arange(24)+10)
df['response']=.4+.7*df['feature']+rng.normal(size=24)
X=sm.add_constant(df[['feature']],has_constant='skip'); res=sm.OLS(df['response'],X,missing='raise').fit()
```

- `add_constant(data,has_constant='skip')` returns a DataFrame/ndarray and does not normally add a duplicate constant. Forcing has_constant='add' may create rank deficiency. `OLS(endog,exog,missing='none').fit(...)` returns a results object; OLS does not automatically add an intercept. Align indices and drop missing rows jointly; do not filter y and X separately.
```python
assert isinstance(res.params,pd.Series); assert res.params.index.tolist()==['const','feature']; assert res.resid.index.equals(df.index); assert sm.add_constant(X).shape==X.shape
```
- `fit(cov_type='HAC',cov_kwds={'maxlags':L,'use_correction':False},use_t=False)` preserves labeled results. Bartlett is the default kernel; maxlags is the largest included lag. False omits the T/(T-k) correction. use_t=False uses normal reference tails; True uses a t reference distribution. Covariance correction and reference distribution are distinct choices.
- `res.get_robustcov_results(cov_type='HAC',maxlags=L,use_correction=False,use_t=False)` returns new results with ndarray params/tvalues. Pass these keywords directly, not inside cov_kwds. Map positions through `res.model.exog_names`.
```python
rob=res.get_robustcov_results(cov_type='HAC',maxlags=2,use_correction=False,use_t=False); fitted=sm.OLS(df['response'],X).fit(cov_type='HAC',cov_kwds={'maxlags':2,'use_correction':False},use_t=False); assert isinstance(rob.params,np.ndarray); assert isinstance(fitted.params,pd.Series); assert np.allclose(rob.cov_params(),fitted.cov_params()); assert np.isclose(rob.params[res.model.exog_names.index('feature')],res.params['feature'])
```
- `res.get_influence()` returns OLSInfluence. hat_matrix_diag is the leverage ndarray; cooks_distance is (distance array, p-value array); resid_studentized_external is the externally studentized residual array.
```python
influence=res.get_influence(); assert influence.hat_matrix_diag.shape==(24,); assert len(influence.cooks_distance)==2; assert influence.resid_studentized_external.shape==(24,)
```
- `durbin_watson(resids,axis=0)` returns a scalar/array: the sum of squared adjacent residual differences divided by the sum of squared residuals. Establish time order first.
```python
e=np.asarray(res.resid); assert np.isclose(durbin_watson(e),np.sum(np.diff(e)**2)/np.sum(e**2))
```
- `WLS(endog,exog,weights=...).fit()` returns results. weights are inverse error variances, not inverse error standard deviations.
```python
weighted=sm.WLS(df['response'],X,weights=np.ones(len(df))).fit(); assert np.allclose(weighted.params,res.params)
```
- `tsa.stattools.adfuller(x,maxlag=None,regression='c',autolag='AIC')` returns a tuple whose first two entries are statistic and p-value. The null is a unit root. Choose lags and deterministic terms from the definition; low p-values do not indicate nonstationarity.
```python
from statsmodels.tsa.stattools import adfuller
unit=adfuller(rng.normal(size=80),maxlag=2,regression='c',autolag=None,result_object=False); assert 0<=unit[1]<=1 and unit[2]==2
```

## Version check: forms that fail in this version

### Removed or renamed forms
- fillna(method=...) -> ffill()/bfill().
- to_numeric(errors='ignore') -> errors='raise' or 'coerce'; handle invalid values explicitly.
- np.math -> Python math.
- groupby(axis=1) -> df.T.groupby(...).agg(...).T; check dtypes.
- resample('M') -> resample('ME'); to_period('M') still uses M.
- resample('Q') -> resample('QE').
- resample('Y') -> resample('YE').
- DataFrame.applymap -> DataFrame.map.
- np.trapz -> np.trapezoid.

### Unavailable or wrong-object forms
- np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
- OLSResults.cov_hac()/cov_HAC() -> get_robustcov_results(cov_type='HAC',maxlags=L,...).
- cov_hac_simple(maxlags=L) -> cov_hac_simple(nlags=L).
- pd.random -> the specified NumPy RNG interface.
- s.get_loc(label) -> s.index.get_loc(label).
- Series.to_series() -> omit it, or copy(); Index.to_series is valid.
- expanding().shift(...) -> aggregate before shift; ordering follows the definition.
- string Series.dt -> to_datetime(series).dt.
- ndarray.values -> the array itself.
- DatetimeIndex.dt.year -> index.year.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).
- PeriodIndex.dt.year -> index.year.
- get_robustcov_results(cov_kwds=...) -> pass maxlags=L directly.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.

Predicting at one new point. add_constant treats its input as a column-ordered design matrix, so a 1-D list is a column of observations, not one row. sm.add_constant([1, x_new]) therefore builds two rows, [[1, 1], [1, x_new]], and predict(...)[0] returns the fit at x = 1 without raising an error. A single row has zero variance in every column, so with the default has_constant='skip', sm.add_constant(np.array([[x_new]])) returns it unchanged and adds no constant. Build the row explicitly instead:

```python
x_row = np.column_stack([np.ones(1), [x_new]])                      # shape (1, 2): [const, x]
# or: x_row = sm.add_constant(np.array([[x_new]]), has_constant='add')
y_hat = res.predict(x_row)[0]
assert np.isclose(y_hat, res.params[0] + res.params[1] * x_new)    # same as the hand-written line
```

For several regressors, pass one row in the same column order as the fitted exog, or compute params @ [1, x1, x2, ...] directly.
