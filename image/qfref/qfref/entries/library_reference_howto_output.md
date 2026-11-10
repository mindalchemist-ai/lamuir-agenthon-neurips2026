NumPy 2.5.3; pandas 3.0.5; Python 3.13.15 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Write labeled and missing-safe deliverables

save_json converts NumPy values, rejects nonfinite numbers and atomically replaces a file; create the parent directory. autosave_json does not detect nested in-place edits: reassign or explicitly save again. Name a meaningful index with rename_axis(...).reset_index() before to_csv(index=False). CSV missing cells may use na_rep=''; do not replace valid missingness with zero. Verify actual schema, types and units by reading back.

```python
import pandas as pd, numpy as np, io
s=pd.Series([2.,np.nan],index=['a','b']).rename_axis('group')
f=s.reset_index(name='value'); text=f.to_csv(index=False,na_rep='')
assert text.startswith('group,value') and pd.read_csv(io.StringIO(text))['value'].isna().iloc[1]
```

## Version check: forms that fail in this version

Removed: none verified.

Unavailable/wrong-object: none verified.
