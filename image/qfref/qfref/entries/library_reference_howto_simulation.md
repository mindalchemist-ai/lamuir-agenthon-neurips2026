NumPy 2.5.3 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Manage random streams and paired simulation draws

RandomState/seed and default_rng do not produce interchangeable sequences. Keep the specified interface and draw order. For finite-difference simulation sensitivities, reuse the same base random variates for both bumps instead of advancing a shared stream independently. Preserve distribution parameter units and array shape. Pair antithetic draws deliberately; estimate uncertainty for the actual dependent sampling scheme.

```python
import numpy as np
z=np.random.default_rng(53).normal(size=12)
up=np.exp(.03+.2*z); down=np.exp(-.03+.2*z)
assert np.allclose(up/down,np.exp(.06))
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
