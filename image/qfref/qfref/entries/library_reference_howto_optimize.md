SciPy 1.18.1 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Solve roots and constrained calibration problems

brentq needs a continuous function and a sign-changing bracket or endpoint root. Check converged/residuals, never substitute an initial guess after failure. minimize needs success plus feasibility; SLSQP inequalities mean fun(x)>=0, L-BFGS-B only box bounds. least_squares takes residual vectors and linear-loss cost is half their squared sum. Check each restart before choosing an objective.

```python
from scipy.optimize import brentq
r,info=brentq(lambda v:v*v-5,0.,4.,full_output=True)
assert info.converged and abs(r*r-5)<1e-9
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
