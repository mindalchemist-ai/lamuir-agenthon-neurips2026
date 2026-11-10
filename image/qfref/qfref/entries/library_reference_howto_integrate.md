NumPy 2.5.3; SciPy 1.18.1 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Integrate, interpolate and differentiate numerical surfaces

quad returns integral/error estimate, not a bound; check convergence and truncation. leggauss nodes/weights on [-1,1] both need rescaling. PchipInterpolator preserves shape; CubicSpline needs boundary conditions. Require sorted unique coordinates and explicit extrapolation. gradient(f,coordinates,edge_order=2) handles irregular spacing; use successive gradients when specified for second derivatives. solve_banded uses packed diagonals.

```python
import numpy as np
from scipy.interpolate import PchipInterpolator
x=np.array([-2.,-.5,1.,3.]); g=np.gradient(x*x,x,edge_order=2)
assert np.allclose(g,2*x) and np.allclose(PchipInterpolator(x,x*x)(x),x*x)
```

## Version check: forms that fail in this version

Removed: np.trapz -> np.trapezoid. scipy.integrate.trapz -> scipy.integrate.trapezoid.

Unavailable/wrong-object: none verified.
