NumPy 2.5.3 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Select empirical quantiles and tail loss averages

quantile q is 0..1; percentile q is 0..100. Explicit method='lower' and default 'linear' differ. Match strict versus inclusive exceedances to the definition. ES is a tail average, not a quantile. Keep return/loss signs and probability tails distinct; Student-t scale is not standard deviation. Do not invent zero floors or silently change ddof.

```python
import numpy as np
x=np.array([1.,3.,6.,10.]); q=np.quantile(x,.5,method='lower')
assert q==3. and x[x>=q].mean()>q
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
