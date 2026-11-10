NumPy 2.5.3; pandas 3.0.5 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Group, map categories and accumulate counts

Map labels before summing: groupby(mapped_keys).sum() combines collisions instead of overwriting. For integer positions use np.add.at or bincount; a[idx]+=v does not accumulate every duplicate. Keep missing-key handling explicit. Named counts and continuous measures need different dtypes.

```python
import numpy as np, pandas as pd
s=pd.Series([2,4,7],index=['red','blue','green']); m={'red':'warm','blue':'cool','green':'cool'}
g=s.groupby(s.index.map(m)).sum(); assert g['cool']==11
z=np.zeros(2); np.add.at(z,[1,1],[4,7]); assert z[1]==11
```

## Version check: forms that fail in this version

Removed: groupby(axis=1) -> df.T.groupby(...).agg(...).T; check dtypes.

Unavailable/wrong-object: none verified.
