NumPy 2.5.3; SciPy 1.18.1 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Propagate a transition matrix over multiple periods

Use matrix_power(P,h) for integer horizons, not elementwise P**h. A continuous-time generator uses expm(Q*t). Rows/columns must follow the stated convention. logm(P)/t may be complex or fail generator constraints; inspect imaginary parts, row sums and off-diagonal signs.

```python
import numpy as np
from scipy.linalg import expm
P=np.array([[.8,.2],[0.,1.]])
assert np.allclose(np.linalg.matrix_power(P,3),P@P@P)
Q=np.array([[-.3,.3],[0.,0.]]); assert np.allclose(expm(Q).sum(axis=1),1)
```

## Version check: forms that fail in this version

Removed: logm(A,disp=False) -> logm(A); check expm reconstruction yourself.

Unavailable/wrong-object: none verified.
