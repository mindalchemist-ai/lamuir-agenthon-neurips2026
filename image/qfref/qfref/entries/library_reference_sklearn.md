NumPy 2.5.3; scikit-learn 1.9.0 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: scikit-learn: preprocessing, PCA, regression and time splits

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import TimeSeriesSplit
rng=np.random.default_rng(31); X=rng.normal(size=(30,3)); y=X@np.array([1.,-.5,.2])+rng.normal(size=30)*.1
```

- `StandardScaler(with_mean=True,with_std=True).fit_transform(X)` returns an ndarray using training-column statistics and ddof=0 variances, not sample standard deviations. Only transform the test set; do not standardize the full sample before splitting.
```python
scaler=StandardScaler(); train=scaler.fit_transform(X[:20]); test=scaler.transform(X[20:]); assert np.allclose(train.std(axis=0,ddof=0),1); assert test.shape==(10,3)
```
- `PCA(n_components=None,svd_solver='auto',whiten=False,random_state=None).fit(X)` returns self. transform returns (samples,components); components_ has shape (components,features); explained_variance_ uses an n-1 denominator. PCA centers but does not automatically standardize. Signs are arbitrary; compare reconstructions or subspaces.
```python
pca=PCA(n_components=2,svd_solver='full').fit(train); score=pca.transform(train); assert score.shape==(20,2); assert pca.components_.shape==(2,3); assert np.all(np.diff(pca.explained_variance_)<=0)
```
- `LinearRegression(fit_intercept=True).fit(X,y)` returns self. coef_ is an ndarray and intercept_ a scalar/array; inferential p-values are not provided. `Ridge(alpha=...,fit_intercept=True)` applies an L2 coefficient penalty whose meaning depends on objective scaling and standardization.
```python
ols=LinearRegression().fit(X,y); assert ols.coef_.shape==(3,); pipe=make_pipeline(StandardScaler(),Ridge(alpha=1.)); pipe.fit(X[:20],y[:20]); assert pipe.predict(X[20:]).shape==(10,)
```
- `TimeSeriesSplit(n_splits=5,test_size=None,gap=0)` returns a splitter. split(X) yields chronological training/test position arrays. Set gap according to the prediction-label horizon to avoid future-label leakage; fixed-length return labels may still overlap across boundaries.
```python
splits=list(TimeSeriesSplit(n_splits=3,gap=2).split(X)); assert all(tr.max()+2<te.min() for tr,te in splits)
```
Defaults can change in future versions. Explicitly set the PCA solver, random seed and regularization. Training scores do not substitute for out-of-time performance.

## Additional explicitly named APIs

- `PCA.components_` is an ndarray shaped (components,features). `PCA.explained_variance_ratio_` gives each retained component's share of total sample variance, not its variance or a cumulative share. Use cumsum for cumulative shares; retaining fewer components normally leaves the sum below 1.
```python
assert pca.components_.shape==(2,3); assert pca.explained_variance_ratio_.shape==(2,); assert np.all(pca.explained_variance_ratio_>=0) and pca.explained_variance_ratio_.sum()<=1+1e-12; assert np.isclose(pca.explained_variance_ratio_.sum(),pca.explained_variance_.sum()/np.var(train,axis=0,ddof=1).sum())
```

## Version check: forms that fail in this version

### Removed or renamed forms
- np.math -> Python math.
- np.trapz -> np.trapezoid.

### Unavailable or wrong-object forms
- np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
- ndarray.values -> the array itself.
- datetime64.strftime -> pd.Timestamp(value).strftime(...).
- PCA.explained_variance_ratio -> explained_variance_ratio_.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
