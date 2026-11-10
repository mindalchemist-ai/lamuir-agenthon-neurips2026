Python 3.13.15 is installed. Use only APIs that exist in this version: not older removed forms, and not newer or unverified ones.

# LibraryReference: Optional libraries and local helper scripts: check the environment

Setup:
```python
import importlib.util
```

Numba: some task environments may additionally provide it. `numba.njit` and `numba.prange` are optional acceleration interfaces, not Python or NumPy built-ins. No Numba compilation example is claimed as verified here; validate type support, first-call compilation and parallel numerical behavior in an environment that provides it.

- `importlib.util.find_spec(name)` returns ModuleSpec or None, checking importability without executing the module. The unchanged example below checks the recorded verification image; it does not establish Numba availability in other task environments or validate a Numba algorithm.
```python
assert importlib.util.find_spec('numba') is None
```
A local conversion script supplied with a task is a separate tool interface, not a public library function. Follow its local usage or CLI help, checking inputs, outputs, exit status and encoding. A filename alone does not establish a Python signature. Inspect an unavailable script before inventing an import path. A mathematical function name does not automatically denote a Python API.

## Version check: forms that fail in this version

### Removed or renamed forms
None among the verified calls shown.

### Unavailable or wrong-object forms
None among the verified calls shown.
