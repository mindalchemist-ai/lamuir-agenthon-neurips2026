NumPy 2.5.3 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Apply stable elementwise transforms and payoff bounds

np.exp/log/sqrt/abs act elementwise. Use log1p/expm1 near zero; check domains. np.maximum/where/clip preserve array shape; they do not justify altering loss signs or economic bounds. Set std(ddof=...) explicitly; mean/sum reduce the requested axis.

```python
import numpy as np
x=np.array([1.,4.]); assert np.allclose(np.exp(np.log(x)),x)
assert np.maximum(x-2,0).tolist()==[0.,2.]
```

## Version check: forms that fail in this version

Removed: np.math -> Python math.

Unavailable/wrong-object: none verified.
