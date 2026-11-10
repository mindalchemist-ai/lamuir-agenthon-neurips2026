NumPy 2.5.3; arch 8.0.0 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Fit and forecast conditional variance

arch_model(...,rescale=False).fit(disp='off') needs convergence_flag==0. Choose the specified mean/innovation model. If inputs are multiplied by 100, undo means/volatility by 100 and variance/omega by 10000; alpha/beta stay unchanged. forecast(...,align='origin',reindex=False) labels origins; residual_variance differs from total variance with mean dynamics. Analytical multistep support depends on model; preserve named fitted parameters.

```python
import numpy as np
from arch import arch_model
v=np.random.default_rng(47).normal(size=250)
r=arch_model(v,mean='Zero',rescale=False).fit(disp='off')
assert r.convergence_flag==0 and r.forecast(horizon=1,reindex=False).variance.shape[1]==1
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: ARCHModelResult.predict -> forecast(...).
