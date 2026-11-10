NumPy 2.5.3; pandas 3.0.5 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Allocate numerical arrays and preserve numerical precision

full_like inherits the prototype dtype: a fractional fill into integers truncates. Request dtype=float for perturbations and pricing grids. pandas.to_numeric(errors='ignore') is removed; use raise/coerce and validate. to_numpy can be a read-only view; use copy=True before mutation. Preserve label/position distinctions and finite outputs instead of silencing conversion failures.

```python
import numpy as np, pandas as pd
base=np.arange(4); step=np.full_like(base,.07,dtype=float)
assert np.allclose(step,.07) and np.full_like(base,.07).sum()==0
assert pd.to_numeric(pd.Series(['2','bad']),errors='coerce').isna().iloc[1]
```

## Version check: forms that fail in this version

Removed: to_numeric(errors='ignore') -> errors='raise' or 'coerce'; handle invalid values explicitly.

Unavailable/wrong-object: ndarray.values -> the array itself. s.get_loc(label) -> s.index.get_loc(label). Series.to_series() -> omit it, or copy(); Index.to_series is valid.
