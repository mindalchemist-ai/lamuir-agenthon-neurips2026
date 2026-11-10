pandas 3.0.5 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

When the task text specifies how to build something or forbids a function, follow the task text.

# LibraryReference: Pair lags before slicing rolling windows

Create (lag,response) on the full timeline before slicing by response date; then jointly drop missing pairs. Slicing first loses the window's valid outside predecessor. rolling includes the current row; shift(1) moves values, freq moves labels. ewm(adjust=False) is recursive; adjust=True differs. Do not double-shift an engine's already lagged signal.

```python
import pandas as pd
s=pd.Series([3.,6.,2.,8.,4.])
pairs=pd.concat({'lag':s.shift(1),'response':s},axis=1).iloc[2:4].dropna()
assert pairs['lag'].tolist()==[6.,2.]
```

## Version check: forms that fail in this version

Removed: resample M/Q/Y -> ME/QE/YE; period M stays M.

Unavailable/wrong-object: Expanding.shift -> aggregate, then shift.
