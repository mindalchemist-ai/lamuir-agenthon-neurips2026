NumPy 2.5.3 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Compute array statistics without axis or dtype mistakes

Arrays are positional. Set axis/ddof explicitly: NumPy std defaults to 0, sample std to 1; nanmean explicitly skips missingness. corrcoef/cov use variables in rows unless rowvar=False. np.exp/log/sqrt/abs are elementwise; @ contracts matrices, outer forms rank-one updates. Simple wealth uses cumprod(1+r), log wealth exp(cumsum(r)); maximum.accumulate tracks peaks. Treat invalid domains and finite values explicitly.

```python
import numpy as np
x=np.array([.02,-.01,.04]); w=np.cumprod(1+x)
assert np.allclose(w,np.exp(np.cumsum(np.log1p(x))))
assert np.isclose(np.std(x,ddof=1)**2,np.var(x,ddof=1))
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: np.clip(axis=...) -> np.clip(...); pandas DataFrame.clip still supports axis.
