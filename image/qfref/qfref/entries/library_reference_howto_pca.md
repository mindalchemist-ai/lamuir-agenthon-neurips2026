NumPy 2.5.3; scikit-learn 1.9.0 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Fit components, standardize and preserve training boundaries

Fit scalers on training only (ddof=0), then transform test data. sklearn PCA centers but does not standardize; components_ is (components,features), explained_variance_ uses n-1, explained_variance_ratio_ is a share. Signs are arbitrary: apply any prescribed orientation consistently to fit and transform. Pipeline prevents preprocessing leakage; use TimeSeriesSplit with a label-horizon gap. Ridge depends on scaling.

```python
import numpy as np
from sklearn.decomposition import PCA
x=np.random.default_rng(51).normal(size=(20,3)); p=PCA(n_components=2,svd_solver='full').fit(x)
assert p.components_.shape==(2,3) and p.transform(x).shape==(20,2)
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: PCA.explained_variance_ratio -> explained_variance_ratio_.
