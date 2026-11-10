Python 3.13.15; NumPy 2.5.3 are installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: Session: save_json, autosave_json and qfref

These are common call forms with unrelated optional arguments omitted, not exhaustive API signatures. Examples share the setup within each entry; entries are independent. All data are synthetic.

Setup:
```python
from pathlib import Path
import tempfile, json, contextlib, io
import numpy as np
from session_io import save_json, autosave_json
import qfref
folder=Path(tempfile.mkdtemp())
```

- `save_json(path,data,*,indent=2,allow_nan=False)` returns the original path. NumPy scalars/arrays become Python values/lists; the entire payload is serialized before atomic replacement in the same directory. The parent directory must exist. NaN/Infinity raise ValueError by default. Convert Series/DataFrame/Timestamp explicitly to the required schema. Do not use allow_nan=True to emit nonstandard JSON.
```python
path=folder/'result.json'; returned=save_json(str(path),{'value':np.float64(2.5),'vector':np.array([1,2])}); assert returned==str(path) and json.loads(path.read_text())['vector']==[1,2]
```
Serialization failure preserves the last successful file. Catching an error does not mean the new values reached disk.
```python
before=path.read_text()
try:
    save_json(str(path),{'value':np.nan})
except ValueError:
    pass
else:
    raise AssertionError('nonfinite accepted')
assert path.read_text()==before
```
- `autosave_json(path,*args,**kwargs)` returns a dict subclass, restoring an existing JSON object. Top-level assignment, update, del, pop and setdefault rewrite the file. Write failures print an error and retain in-memory values while disk holds the last successful state. In-place changes inside nested objects do not trigger top-level hooks; inherited clear/popitem/|= operations also need not trigger them.
```python
auto=autosave_json(str(path)); auto['nested']={'count':1}; auto['nested']['count']=2; assert json.loads(path.read_text())['nested']['count']==1; auto['nested']=dict(auto['nested']); assert json.loads(path.read_text())['nested']['count']==2
```
Before finishing, explicitly call save_json(path,dict(auto)) and read the file back. Autosaving preserves progress; it does not validate fields, types or units.
```python
save_json(str(path),dict(auto)); assert json.loads(path.read_text())['value']==2.5
```
- `qfref.catalog()` returns None and prints the catalog. `qfref.show(name)` returns None and prints matching content, not executable formula functions. Queries match a complete entry name or a description substring, not arbitrary filename substrings.
```python
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    qfref.catalog()
assert 'library_reference_session_io' in buf.getvalue()
buf=io.StringIO()
with contextlib.redirect_stdout(buf):
    qfref.show('library_reference_session_io')
assert 'save_json' in buf.getvalue()
```

## Version check: forms that fail in this version

### Removed or renamed forms
None among the verified calls shown.

### Unavailable or wrong-object forms
- ndarray.values -> the array itself.

Wrong/current executions are recorded in LibraryReference API compatibility evidence; absence is not inferred from API memory.
