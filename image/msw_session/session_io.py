'save_json for the Python session: NumPy scalars and arrays become Python values, unsupported types raise before any\nfile is touched, and the target is replaced only after the whole content is serialised. autosave_json is a dict that\nrewrites its JSON file after every change.'
import difflib
import json
import os
import tempfile


def to_builtin(value, where="data"):
    """value with NumPy scalars as Python scalars and arrays as lists; anything else that JSON cannot hold raises TypeError
    naming where it is."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float)):
        return value
    module = type(value).__module__.split(".")[0]
    if module == "numpy":
        if hasattr(value, "tolist"):
            return to_builtin(value.tolist(), where)
        if hasattr(value, "item"):
            return to_builtin(value.item(), where)
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            key = to_builtin(k, f"{where} key {k!r}")
            if not isinstance(key, (str, int, float, bool)) and key is not None:
                raise TypeError(f"{where}: key {k!r} of type {type(k).__name__} cannot be a JSON key")
            out[key] = to_builtin(v, f"{where}[{k!r}]")
        return out
    if isinstance(value, (list, tuple)):
        return [to_builtin(v, f"{where}[{i}]") for i, v in enumerate(value)]
    raise TypeError(f"{where}: {type(value).__module__}.{type(value).__name__} is not JSON data; convert it first")


def save_json(path, data, *, indent=2, allow_nan=False):
    """Writes data to path as JSON; the file is replaced only after serialisation succeeds, so a failure leaves any existing
    file unchanged. NaN and infinity raise unless allow_nan=True. Returns the path."""
    payload = json.dumps(to_builtin(data), indent=indent, allow_nan=allow_nan)
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(payload)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


class autosave_json(dict):
    """A dict that rewrites its JSON file (with save_json) after every change, so each assigned value is on disk at once.
    Created on a path that already holds a JSON object, it starts from that content instead of emptying the file. A key the
    task entry does not name for this file (known from MSW_EXPECTED_KEYS) is still stored, with a printed warning.
    A value that cannot be written is reported and kept in the dict; the file then keeps its last good content."""

    def __init__(self, path, *args, **kwargs):
        super().__init__()
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        try:
            with open(path) as f:
                kept = json.load(f)
            if isinstance(kept, dict):
                super().update(kept)
                print(f"autosave_json: {path} already holds {len(kept)} keys; they are kept")
        except (OSError, ValueError):
            pass
        try:
            with open(os.environ["MSW_EXPECTED_KEYS"]) as f:
                self.expected = json.load(f).get(os.path.basename(path)) or []
        except (KeyError, OSError, ValueError):
            self.expected = []
        super().update(*args, **kwargs)
        for key in dict(*args, **kwargs):
            self._check_key(key)
        self._write()

    def _check_key(self, key):
        """Reports a key the task entry does not name for this file, with the nearest names it does give."""
        if self.expected and key not in self.expected:
            near = difflib.get_close_matches(str(key), self.expected, n=2, cutoff=0.6)
            print(f"autosave_json: key {key!r} is not a key the task names for this file"
                  + (f"; nearest: {', '.join(near)}" if near else ""))

    def _write(self):
        try:
            save_json(self.path, dict(self))
        except (TypeError, ValueError, OSError) as exc:
            print(f"autosave_json: {self.path} not rewritten: {exc}")

    def __setitem__(self, key, value):
        self._check_key(key)
        super().__setitem__(key, value)
        self._write()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._write()

    def update(self, *args, **kwargs):
        for key in dict(*args, **kwargs):
            self._check_key(key)
        super().update(*args, **kwargs)
        self._write()

    def pop(self, *args):
        value = super().pop(*args)
        self._write()
        return value

    def setdefault(self, key, default=None):
        value = super().setdefault(key, default)
        self._write()
        return value


def _stable_sort_default():
    """Makes pandas sort_values default to a stable sort in this session, so rows that tie keep their order."""
    try:
        import pandas as pd
    except ImportError:
        return
    for cls in (pd.DataFrame, pd.Series):
        original = cls.sort_values
        if getattr(original, "_stable_default", False):
            continue
        def sort_values(self, *args, _original=original, **kwargs):
            kwargs.setdefault("kind", "stable")
            return _original(self, *args, **kwargs)
        sort_values._stable_default = True
        sort_values.__doc__ = original.__doc__
        cls.sort_values = sort_values


_stable_sort_default()
