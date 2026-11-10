import ast, json, os, re

SPECS = {
    "numpy.quantile": (["q", "axis", "method"], "the default method='linear' interpolates between order statistics; other quantile conventions need an explicit method."),
    "numpy.percentile": (["q", "axis", "method"], "q is in percent (0-100), not a fraction; the default method='linear' interpolates."),
    "numpy.std": (["axis", "ddof"], "the default ddof=0 is the population value; pandas .std() defaults to ddof=1."),
    "numpy.var": (["axis", "ddof"], "the default ddof=0 is the population value; pandas .var() defaults to ddof=1."),
    "numpy.nanstd": (["axis", "ddof"], "the default ddof=0 is the population value."),
    "numpy.sum": (["axis"], "without axis it sums every element of a 2-D array into one number."),
    "numpy.cumsum": (["axis"], "without axis it flattens a 2-D array; a NaN makes every later sum NaN."),
    "numpy.gradient": (["varargs", "axis", "edge_order"], "spacing is passed positionally after the array; the ends use one-sided differences of edge_order."),
    "numpy.maximum": ([], "a third positional argument is the output array `out`, not a floor: write np.maximum(np.maximum(a, b), 0)."),
    "numpy.column_stack": (["tup"], "it takes one sequence of arrays; 1-D arrays become columns."),
    "pandas.DataFrame.std": (["axis", "ddof", "skipna"], "the default ddof=1 is the sample value; numpy's std defaults to ddof=0."),
    "pandas.Series.std": (["ddof", "skipna"], "the default ddof=1 is the sample value; numpy's std defaults to ddof=0."),
    "pandas.DataFrame.sum": (["axis", "skipna", "min_count"], "the default axis=0 sums each column; axis=1 sums across a row; an all-NaN sum is 0 unless min_count is set."),
    "pandas.DataFrame.reindex": (["labels", "index", "columns", "axis", "fill_value"], "a positional first argument reindexes the rows; pass columns= to reindex columns."),
    "pandas.DataFrame.sort_index": (["axis", "ascending", "level"], "it sorts the row labels ascending; it does not sort by any column."),
    "pandas.DataFrame.sort_values": (["by", "axis", "ascending", "kind"], "a name that is both an index level and a column raises; when rows that tie on the key must keep their order, pass kind='stable'."),
    "pandas.DataFrame.groupby": (["by", "as_index", "sort", "dropna"], "the default dropna=True drops rows whose key is NaN; sort=True orders the groups by key."),
    "pandas.DataFrame.merge": (["how", "on", "left_on", "right_on", "validate"], "a str key merged with a datetime or int key raises ValueError, and dates written as different strings ('2020-01-01' vs '2020-01-01 00:00:00') match nothing: bring both keys to one dtype first; the default how='inner' drops unmatched rows."),
    "pandas.DataFrame.astype": (["dtype", "errors"], "casting a float column with NaN to int raises; a string column with a non-numeric entry raises on astype(float), while pd.to_numeric(s, errors='coerce') turns that entry into NaN."),
    "pandas.core.base.IndexOpsMixin.value_counts": (["normalize", "dropna", "sort"], "the default dropna=True leaves NaN out of the counts and out of normalize."),
    "pandas.core.generic.NDFrame.resample": (["rule", "closed", "label"], "for 'ME', 'QE', 'YE' and 'W' rules the defaults are closed='right' and label='right'."),
    "pandas.to_datetime": (["format", "dayfirst", "utc", "unit"], "integers are read as nanoseconds unless unit is given; a 'YYYYMMDD' integer needs format='%Y%m%d' after astype(str)."),
        "pandas.Series": (["data", "index", "name"], "a dict's keys become the index; passing index= with a dict selects those keys."),
    "scipy.stats.skew": (["axis", "bias"], "the default bias=True applies no small-sample correction."),
    "scipy.stats.kurtosis": (["axis", "fisher", "bias"], "the default fisher=True returns excess kurtosis (normal = 0) and bias=True applies no correction."),
    "scipy.optimize.brentq": (["f", "a", "b", "xtol"], "f(a) and f(b) must have opposite signs, or it raises ValueError."),
    "pandas.core.generic.NDFrame.shift": (["periods", "freq", "fill_value"], "lag the whole series first, then cut the window; shifting a window that was cut first leaves its first row without the value before it."),
    "pandas.DataFrame.shift": (["periods", "freq", "axis", "fill_value"], "lag the whole frame first, then cut the window; shifting a window that was cut first leaves its first row without the value before it."),
    "pandas.Series.diff": (["periods"], "difference the whole series first, then cut the window; a window cut first loses its first difference."),
    "pandas.DataFrame.diff": (["periods", "axis"], "difference the whole frame first, then cut the window; a window cut first loses its first difference."),
    "pandas.core.generic.NDFrame.pct_change": (["periods", "fill_method", "freq"], "compute it on the whole series first, then cut the window; a window cut first loses its first return."),
    "statsmodels.tools.tools.add_constant": (["data", "prepend", "has_constant"], "a 1-D or single-row input that already looks constant gets no constant column; for one prediction row pass a 2-D array of one row, e.g. np.array([[x]]) with has_constant='add', or compute params[0] + params[1] * x directly; a 1-D list is read as a column."),
    "json.dump": (["obj", "fp", "default"], "a Timestamp written through default=str comes out as 'YYYY-MM-DD 00:00:00'; when the field is a date, write ts.strftime('%Y-%m-%d')."),
    "json.dumps": (["obj", "default"], "a Timestamp written through default=str comes out as 'YYYY-MM-DD 00:00:00'; when the field is a date, write ts.strftime('%Y-%m-%d')."),
    "pandas._libs.tslibs.timestamps._Timestamp.isoformat": (["sep", "timespec"], "it always includes the time ('YYYY-MM-DDT00:00:00'); when the field is a date, use .strftime('%Y-%m-%d')."),
    "pandas._libs.tslibs.timestamps.Timestamp.strftime": (["format"], "format '%Y-%m-%d' gives the date alone; str(ts) and isoformat() add the time."),
    "builtins.dict.get": ([], "a curve or price dictionary read with .get(key, 0) in a discount or a sum turns a missing key into 0 instead of an error; index it as d[key] or fill the key first."),
    "pandas.core.generic.NDFrame.rank": (["method", "ascending"], "method='first' breaks ties by the current row order; when the task states a tie rule, sort the rows by that rule first, then rank."),
}
CHECKLIST_DEFAULTS = {
                      "scipy.stats.skew": {"bias": True}, "scipy.stats.kurtosis": {"bias": True, "fisher": True}}
CLOSING = ("Check your line against this. If it is wrong, fix it in the next cell; if it is right, go straight on with the next "
           "step in this reply, without a separate checking turn.")
MAX_LINES = 15
DESC_LINES = 4


def norm_qual(module: str, qualname: str) -> str:
    top = (module or "").split(".")[0]
    if top == "pandas":
        q = qualname.replace("core.frame.", "").replace("core.series.", "")
        cand = f"pandas.{q}"
        return cand if cand in SPECS or not module.startswith("pandas.core") else f"{module}.{qualname}"
    if top == "scipy" and ".stats" in module:
        return f"scipy.stats.{qualname.split('.')[-1]}"
    if top == "scipy" and ".optimize" in module:
        return f"scipy.optimize.{qualname.split('.')[-1]}"
    if module == "builtins":
        return f"builtins.{qualname}"
    if top == "numpy":
        return f"numpy.{qualname.split('.')[-1]}"
    return f"{module}.{qualname}"


def call_exprs(code: str) -> list:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    lines, out, seen = code.splitlines(), [], set()

    def plain(n):
        while isinstance(n, (ast.Attribute, ast.Subscript)):
            if isinstance(n, ast.Subscript) and any(isinstance(x, ast.Call) for x in ast.walk(n.slice)):
                return False
            n = n.value
        return isinstance(n, ast.Name)

    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and plain(n.func):
            e = ast.unparse(n.func)
            if e not in seen and not e.startswith(("print", "len", "range")):
                seen.add(e)
                out.append((e, lines[n.lineno - 1].strip() if n.lineno <= len(lines) else e))
    return sorted(out, key=lambda x: code.find(x[0]))


PROBE = r'''
import json as _vj, inspect as _vi
_vr = []
for _ve in __EXPRS__:
    try:
        _vo = eval(_ve, globals())
    except Exception:
        continue
    _vf = getattr(_vo, "__func__", _vo)
    _vm, _vq = getattr(_vf, "__module__", None), getattr(_vf, "__qualname__", None)
    if type(_vo).__name__ == "ufunc":
        _vm, _vq = "numpy", _vo.__name__
    if type(_vo).__name__ == "builtin_function_or_method" and type(getattr(_vo, "__self__", None)) is dict:
        _vm, _vq = "builtins", "dict." + _vo.__name__
    if isinstance(_vo, type):
        _vm, _vq = _vo.__module__, _vo.__qualname__
    if not _vm or not _vq:
        continue
    try:
        _vs = str(_vi.signature(_vo))
    except (TypeError, ValueError):
        _vs = ""
    _vr.append([_ve, _vm, _vq, _vs, _vi.getdoc(_vo) or ""])
print("VA_PROBE", _vj.dumps(_vr))
'''


def probe_code(exprs) -> str:
    return PROBE.replace("__EXPRS__", repr(list(exprs)))


def param_lines(doc: str, names) -> list:
    m = re.search(r"\nParameters\n-+\n(.*?)(?:\n\n[A-Z][A-Za-z ]+\n-+\n|\Z)", "\n" + doc, re.S)
    if not m:
        return []
    block, out = m.group(1).splitlines(), []
    for want in names:
        for i, l in enumerate(block):
            if re.match(rf"\**{re.escape(want)}\b", l) and not l.startswith(" "):
                desc = []
                for x in block[i + 1:]:
                    if x.strip() and not x.startswith(" "):
                        break
                    if x.strip() and not x.strip().startswith(".. "):
                        desc.append(x.strip())
                text = " ".join(desc[:DESC_LINES])
                if len(desc) > DESC_LINES:
                    ends = [k.end() for k in re.finditer(r"(?<![0-9])[.!?](?=\s|$)", text)]
                    text = text[:ends[-1]] if ends else text
                out.append(f"  {l.strip()}: {text}")
                break
    return out


def risky_params(name: str) -> list:
    params, pitfall = SPECS[name]
    word = lambda p: (rf"(?<![A-Za-z_]){re.escape(p)}(?![A-Za-z_])" if len(p) > 2 else
                      rf"(?<![A-Za-z_]){re.escape(p)}(?==|\()|\({re.escape(p)}\)")
    named = [p for p in params if re.search(word(p), pitfall)]
    return named or params[:1]


_IMPORT = {"pandas.core.base.IndexOpsMixin.value_counts": "pandas.Series.value_counts",
           "pandas.core.generic.NDFrame.resample": "pandas.DataFrame.resample",
           "pandas.core.generic.NDFrame.shift": "pandas.Series.shift",
           "pandas.core.generic.NDFrame.pct_change": "pandas.Series.pct_change",
           "pandas.core.generic.NDFrame.rank": "pandas.Series.rank",
           "statsmodels.tools.tools.add_constant": "statsmodels.api.add_constant",
           "pandas._libs.tslibs.timestamps._Timestamp.isoformat": "pandas.Timestamp.isoformat",
           "pandas._libs.tslibs.timestamps.Timestamp.strftime": "pandas.Timestamp.strftime",
           "builtins.dict.get": "builtins.dict.get"}
K2C_WORDS = re.compile(r"(^|[^a-z])(df|dfs|disc\w*|discount\w*|zero\w*|zc\w*|rates?|curve\w*|spot\w*|prices?|px|yields?|fx|fwd\w*|"
                       r"forward\w*|surv\w*|hazard\w*|par\w*|quote\w*)([^a-z]|$)")
K2C_NOT = re.compile(r"weight|count|vec|tf|idf|hold|kwargs|params|config|instr")


def build_note(name: str, expr: str, line: str, sig: str, doc: str) -> str:
    params, pitfall = SPECS[name]
    body = [f"API note on your line `{line or expr}`: `{expr}` is {name} in the installed version."]
    if sig:
        body.append(f"  {name.split('.')[-1]}{sig}"[:300])
    body += param_lines(doc, risky_params(name))
    body.append(f"  Known pitfall: {pitfall}")
    return "\n".join(body[:MAX_LINES - 1] + [CLOSING])


def note_text(name: str, line: str = "", expr: str = None) -> str:
    import importlib, inspect
    path = _IMPORT.get(name, name).split(".")
    obj = None
    for i in range(len(path), 0, -1):
        try:
            obj = importlib.import_module(".".join(path[:i]))
        except ImportError:
            continue
        for part in path[i:]:
            obj = getattr(obj, part)
        break
    try:
        sig = re.sub(r"^\(self,? ?", "(", str(inspect.signature(obj)))
    except (TypeError, ValueError):
        sig = ""
    return build_note(name, expr or name.split(".")[-1], line, sig, inspect.getdoc(obj) or "")


def dict_get_counts(expr: str, line: str) -> bool:
    m = re.search(re.escape(expr) + r"\(\s*([^,()]+)\s*,\s*0(?:\.0*)?\s*\)", line)
    lex = (expr + " " + (m.group(1) if m else "")).lower()
    return bool(m) and bool(K2C_WORDS.search(lex)) and not K2C_NOT.search(lex)


class VaDoc:

    def __init__(self):
        self.shown = set()

    def exprs(self, code: str) -> list:
        return [e for e, _ in call_exprs(code)]

    def notes(self, code: str, probe_output: str) -> list:
        m = re.search(r"VA_PROBE (\[.*\])", probe_output or "", re.S)
        if not m:
            return []
        lines = dict(call_exprs(code))
        out = []
        for expr, mod, qual, sig, doc in json.loads(m.group(1)):
            name = norm_qual(mod, qual)
            if name not in SPECS or name in self.shown:
                continue
            line = lines.get(expr, expr)
            if name == "builtins.dict.get" and not dict_get_counts(expr, line):
                continue
            self.shown.add(name)
            out.append(build_note(name, expr, line, sig, doc))
        return out



CARDS_PATH = next((p for p in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "va_cards.json"),
                               os.path.join(os.path.dirname(os.path.abspath(__file__)), "va_cards", "va_cards.json"))
                   if os.path.exists(p)), os.path.join(os.path.dirname(os.path.abspath(__file__)), "va_cards", "va_cards.json"))
LOOK_FOR = {"ddof": ["sample", "unbiased", "population"], "bias": ["unbiased", "bias-corrected", "adjusted"],
            "fisher": ["excess kurtosis", "Fisher", "Pearson"]}
VA_NO_CHANGE = ("If nothing needs a change, reply with your next step exactly as you planned it before this check: do not "
                "rewrite, re-run or resend any cell that already ran, and do not mention this check.")
VA_STEPS = ("If a point needs a change, call\n"
            "  `fix_line(new_line=\"<this one line with only its arguments changed>\", reason=\"<the sentence you quoted from "
            "<task_instructions>, or: not specified in the task instructions; checklist default>\")`\n"
            "as your whole reply; do not resend any code (the host changes only that line and reruns the cells that depend on "
            "it).\n" + VA_NO_CHANGE)
VA_STEPS_API = ("If a point needs a change, call\n"
                "  `fix_line(new_line=\"<this one line with only its arguments changed>\", reason=\"<one sentence: what the "
                "documentation above shows this line gets wrong>\")`\n"
                "as your whole reply; do not resend any code (the host changes only that line and reruns the cells that depend "
                "on it).\n" + VA_NO_CHANGE)
VA_EDIT = ("If a point needs a change, fix only this line. Call exactly:\n  `edit_cell(cell={cell}, old={old!r}, new={new!r})`\n"
           "Change nothing else in this cell or in any other cell; do not resend the cell. Then rerun only the steps that use "
           "these values\nand rewrite the files built from them. If nothing needs a change, continue with your next step in "
           "this same reply.")
VA_STEPS_NEXT_CELL = ("If a point needs a change, change only the arguments of this one line and run the cell again (and the cells "
                      "that use its results) in your next reply; do not rewrite other code.\n" + VA_NO_CHANGE)
VA_STEPS_CELL = ("If a point needs a change, make it in your next cell (it is not an argument of this one call): change only "
                 "what the point names, rerun the steps that use the result, and rewrite the files built from it; do not "
                 "rewrite other code.\n" + VA_NO_CHANGE)
CARD_ATTRS = {"conditional_volatility", "params"}


def look_for_text(words) -> str:
    return ", ".join(words[:-1]) + " or " + words[-1] if len(words) > 1 else words[0]


def load_cards(path: str = CARDS_PATH) -> dict:
    import glob
    out = {}
    for f in [path] + sorted(glob.glob(os.path.join(os.path.dirname(path), "va_cards_*.json"))):
        try:
            out.update(json.load(open(f)))
        except (OSError, ValueError):
            continue
    return out


def _wrap(n: int, *segments: str) -> str:
    out = []
    for i, seg in enumerate(segments):
        if seg.startswith("|"):
            out.append("\n".join("   " + l for l in seg.split("\n")))
            continue
        words = re.findall(r"(?:`[^`]*`|\$[^$]*\$|\S)+", seg)
        line, lines = f"{n}. " if i == 0 else "   ", []
        for w in words:
            if len(line) + len(w) + 1 > 127 and line.strip():
                lines.append(line.rstrip())
                line = "   "
            line += ("" if line.endswith(" ") else " ") + w
        lines.append(line.rstrip())
        out.append("\n".join(lines))
    return "\n".join(out)


WINDOW_CALLS = {"rolling", "expanding", "groupby", "ewm"}


def _plain(n) -> bool:
    while isinstance(n, (ast.Attribute, ast.Subscript, ast.Call)):
        if isinstance(n, ast.Subscript) and any(isinstance(x, ast.Call) for x in ast.walk(n.slice)):
            return False
        if isinstance(n, ast.Call):
            if not (isinstance(n.func, ast.Attribute) and n.func.attr in WINDOW_CALLS
                    and not any(isinstance(x, ast.Call) for a in n.args + [k.value for k in n.keywords] for x in ast.walk(a))):
                return False
            n = n.func
        n = n.value
    return isinstance(n, ast.Name)


def va_sites(code: str) -> list:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    lines, out = code.split("\n"), []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _plain(n.func):
            arg = ast.unparse(n.args[0]) if n.args and not any(isinstance(x, ast.Call) for x in ast.walk(n.args[0])) else None
            out.append({"kind": "call", "expr": ast.unparse(n.func), "attr": None, "arg": arg, "node": n, "keys": _order_keys(n)})
        elif isinstance(n, ast.Attribute) and n.attr in CARD_ATTRS and _plain(n.value) and isinstance(n.ctx, ast.Load):
            out.append({"kind": "attr", "expr": ast.unparse(n.value), "attr": n.attr, "arg": None, "node": n})
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    for k, s in enumerate(sorted(out, key=lambda s: (s["node"].lineno, s["node"].col_offset))):
        s.update(id=k, lineno=s["node"].lineno, col=s["node"].col_offset, parent=parents.get(s["node"]),
                 line=lines[s["node"].lineno - 1] if s["node"].lineno <= len(lines) else "")
    return sorted(out, key=lambda s: s["id"])


ORDER_METHODS = {"sort_values": ("by", 0), "nlargest": ("columns", 1), "nsmallest": ("columns", 1), "rank": (None, None)}
ORDER_RANK = re.compile(r"range\(\s*1\s*,|np\.arange\(\s*1\s*,|cumcount\(\)")


def _order_keys(call):
    f = call.func
    if not isinstance(f, ast.Attribute) or f.attr not in ORDER_METHODS:
        return None
    kw, pos = ORDER_METHODS[f.attr]
    if kw is None:
        return ""
    src = next((k.value for k in call.keywords if k.arg == kw), call.args[pos] if len(call.args) > pos else None)
    if src is None:
        return "" if f.attr == "sort_values" else None
    return ast.unparse(src) if not any(isinstance(x, ast.Call) for x in ast.walk(src)) else None


VA_PROBE = '\nimport json as _vj\n_vr = {}\nfor _vid, _vk, _ve, _va, _vkey in __SITES__:\n    try:\n        _vo = eval(_ve, globals())\n    except Exception:\n        continue\n    if _vk == "attr":\n        _vt = type(_vo)\n        _vr[_vid] = [_vt.__module__, _vt.__qualname__, None, None, None, None]\n        continue\n    _vf = getattr(_vo, "__func__", _vo)\n    _vm, _vq = getattr(_vf, "__module__", None), getattr(_vf, "__qualname__", None)\n    if type(_vo).__name__ == "ufunc":\n        _vm, _vq = "numpy", _vo.__name__\n    _vn = _vrows = None\n    if _va:\n        try:\n            _vin = eval(_va, globals())\n            import numpy as _vnp\n            _vn = int(_vnp.ndim(_vin))\n            _vrows = int(_vnp.shape(_vin)[0]) if _vn >= 1 else None\n        except Exception:\n            pass\n    _vself = getattr(_vo, "__self__", None)\n    _vtie = None\n    if _vkey is not None and _vself is not None:\n        try:\n            import numpy as _vnp, pandas as _vpd\n            _vk = None if _vkey == "" else eval(_vkey, globals())\n            if isinstance(_vk, (list, tuple)) and hasattr(_vself, "columns"):\n                _vk = [_c for _c in _vk if _c in _vself.columns]\n            _vs = _vself if _vk is None else _vself[_vk]\n            if hasattr(_vs, "ngroups") and hasattr(_vs, "obj"):\n                _vs = _vs.obj\n            _vcols = [_vs] if isinstance(_vs, _vpd.Series) else [_vs[_c] for _c in _vs.columns]\n            _vtie = False\n            for _vc in _vcols:\n                if _vc.dtype.kind == "f":\n                    _vu = _vnp.unique(_vc.dropna().to_numpy())\n                    if len(_vu) > 1 and bool(_vnp.any(_vnp.isclose(_vu[1:], _vu[:-1], rtol=1e-9, atol=1e-12))):\n                        _vtie = True\n        except Exception:\n            _vtie = None\n    _vr[_vid] = [_vm, _vq, _vn, _vrows, type(_vself).__module__ + "." + type(_vself).__qualname__ if _vself is not None and not isinstance(_vself, type(_vj)) else None, _vtie]\nprint("VA_SITES " + _vj.dumps(_vr, separators=(",", ":")))\n'


def va_probe_code(sites, cards=None) -> str:
    names = {k.rsplit(".", 1)[-1] for k in (cards if cards is not None else _card_names())}
    keep = [s for s in sites if s["kind"] == "attr" or s["expr"].rsplit(".", 1)[-1] in names]
    return VA_PROBE.replace("__SITES__", repr([[s["id"], s["kind"], s["expr"], s["arg"], s.get("keys")] for s in keep]))


def _card_names():
    if not hasattr(_card_names, "cards"):
        _card_names.cards = load_cards()
    return _card_names.cards


def _full_name(mod: str, qual: str, self_type: str, kind: str, attr: str, cards: dict):
    if kind == "attr":
        cands = [f"{mod}.{qual}.{attr}"]
    else:
        cands = [norm_qual(mod or "", qual or ""), f"{(mod or '').split('.')[0]}.{(qual or '').split('.')[-1]}"]
        if self_type:
            cands.append(norm_qual(self_type.rsplit(".", 1)[0], self_type.rsplit(".", 1)[1] + "." + (qual or "").split(".")[-1]))
            cands.append(f"{self_type.split('.')[0]}.{self_type.rsplit('.', 1)[1]}.{(qual or '').split('.')[-1]}")
        if mod and mod.startswith("arch.univariate.mean") and qual == "arch_model":
            cands.insert(0, "arch.arch_model")
        if mod and mod.startswith("statsmodels") and qual == "add_constant":
            cands.insert(0, "statsmodels.api.add_constant")
        if mod and mod.startswith("scipy.stats"):
            cands.insert(0, f"scipy.stats.{(qual or '').split('.')[-1]}")
        if (qual or "").startswith("ndarray."):
            cands.insert(0, f"numpy.{qual}")
        if mod and mod.startswith("pandas.core") and (qual or "").split(".")[0] in ("Rolling", "Expanding", "GroupBy"):
            cands.insert(0, f"pandas.{qual}")
    return next((c for c in cands if c in cards), None)


def _passed(card, call, receiver):
    params = card["params"]
    out = {}
    names = [p["name"] for p in params if p["kind"] in ("POSITIONAL_ONLY", "POSITIONAL_OR_KEYWORD")]
    if names and names[0] == "self":
        if receiver is not None:
            out["self"] = receiver
        names = names[1:]
    for name, a in zip(names, call.args):
        out[name] = ast.unparse(a)
    for k in call.keywords:
        if k.arg:
            out[k.arg] = ast.unparse(k.value)
    return out


def _literal(src):
    try:
        return ast.literal_eval(src)
    except (ValueError, SyntaxError):
        return "<expr>"


def _task_has(pattern: str, task: str) -> bool:
    return bool(pattern) and re.search(pattern, task or "", re.I) is not None


def _skipped(site, skip) -> bool:
    if "print" in skip and re.match(r"\s*print\(", site["line"]):
        return True
    par = site.get("parent")
    return ("zero_guard" in skip and isinstance(par, ast.Compare)
            and any(isinstance(c, ast.Constant) and c.value == 0 for c in [par.left] + par.comparators))


VA_DDOF_BROAD = False
NP_STDVAR = {"std", "var", "nanstd", "nanvar"}


def _ddof_of(call):
    f = call.func
    kw = {k.arg: k.value for k in call.keywords if k.arg}
    lit = lambda n: _literal(ast.unparse(n))
    if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("np", "numpy"):
        if f.attr in NP_STDVAR:
            d = lit(kw["ddof"]) if "ddof" in kw else 0
            return ("var", d) if isinstance(d, int) else None
        if f.attr == "cov":
            d = lit(kw["ddof"]) if "ddof" in kw else (0 if "bias" in kw and lit(kw["bias"]) is True else 1)
            return ("cov", d) if isinstance(d, int) else None
        return None
    if isinstance(f, ast.Attribute) and f.attr == "cov":
        d = lit(kw["ddof"]) if "ddof" in kw else 1
        return ("cov", d) if isinstance(d, int) else None
    return None


def ddof_calls(code: str) -> list:
    try:
        tree = ast.parse(code or "")
    except SyntaxError:
        return []
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and (x := _ddof_of(n)):
            out.append((ast.unparse(n), x[0], x[1]))
    return sorted(out, key=lambda c: code.find(c[0]) if c[0] in code else len(code))


def mixed_ddof(code: str) -> bool:
    got = ddof_calls(code)
    var, cov = {d for _, k, d in got if k == "var"}, {d for _, k, d in got if k == "cov"}
    return bool(var and cov and var != cov)


MIXED_NOTE = ("This cell divides its variances and its covariances by different `ddof`: {calls}. Inside one ratio or "
              "decomposition every variance and covariance must use the same `ddof`. To fix it, change only the `ddof` of "
              "this line's call so it matches the other calls in this cell, keep the line a single statement (do not join "
              "other lines into it), and give \"consistency\" as the reason.")


def mixed_note(code: str) -> str:
    return MIXED_NOTE.format(calls="; ".join(f"`{src}` uses `ddof={d}`" for src, _, d in ddof_calls(code)))


LAG_METHODS = {"shift", "diff", "pct_change"}
ORDER_OPS = (ast.Gt, ast.GtE, ast.Lt, ast.LtE)


def _is_mask(n):
    if isinstance(n, ast.Compare):
        return all(isinstance(o, ORDER_OPS) for o in n.ops)
    if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.BitAnd, ast.BitOr)):
        return _is_mask(n.left) or _is_mask(n.right)
    return isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "between"


def _window_slice(n, masks):
    if not isinstance(n, ast.Subscript):
        return False
    sl = n.slice.elts[0] if isinstance(n.slice, ast.Tuple) and n.slice.elts else n.slice
    if isinstance(sl, ast.Slice):
        return sl.lower is not None
    return _is_mask(sl) or (isinstance(sl, ast.Name) and sl.id in masks)


def _chain_has_window(n, masks, windows):
    while True:
        if _window_slice(n, masks):
            return True
        if isinstance(n, ast.Name):
            return n.id in windows
        if isinstance(n, (ast.Attribute, ast.Subscript)):
            n = n.value
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            n = n.func.value
        else:
            return False


def _loops(tree):
    out = {}

    def walk(n, loop):
        for c in ast.iter_child_nodes(n):
            out[id(c)] = loop
            walk(c, c if isinstance(c, (ast.For, ast.AsyncFor, ast.While, ast.FunctionDef, ast.Lambda)) else loop)
    walk(tree, None)
    return out


def _bindings(tree, loops, before):
    masks, windows = set(), set()
    assigns = sorted((n for n in ast.walk(tree) if isinstance(n, ast.Assign) and len(n.targets) == 1
                      and isinstance(n.targets[0], ast.Name) and n.lineno < before), key=lambda n: n.lineno)
    for n in assigns:
        if _is_mask(n.value):
            masks.add(n.targets[0].id)
        elif _chain_has_window(n.value, masks, windows) and loops.get(id(n)) is not None:
            windows.add(n.targets[0].id)
        else:
            windows.discard(n.targets[0].id)
    return masks, windows


def slice_then_lag(site, code):
    node = site["node"]
    if site["kind"] != "call" or not isinstance(node.func, ast.Attribute) or node.func.attr not in LAG_METHODS:
        return False
    if isinstance(node.func.value, ast.Name) and node.func.value.id in ("np", "numpy"):
        return False
    tree = ast.parse(code)
    loops = _loops(tree)
    me = next((n for n in ast.walk(tree) if isinstance(n, ast.Call) and n.lineno == node.lineno and n.col_offset == node.col_offset), None)
    if me is None or loops.get(id(me)) is None:
        return False
    masks, windows = _bindings(tree, loops, me.lineno)
    return _chain_has_window(me.func.value, masks, windows)


ARITH = (ast.Mult, ast.Div, ast.FloorDiv, ast.Pow)
DISCOUNT_CALL = re.compile(r"(^|\.)(exp|power|log|discount\w*|df\w*|pv\w*|npv)$", re.I)
PARAM_NAME = re.compile(r"(^|[^a-z])(pars|param\w*)([^a-z]|$)")


def _zero_one_default(call):
    if len(call.args) != 2 or call.keywords:
        return False
    d = call.args[1]
    if isinstance(d, ast.UnaryOp) and isinstance(d.op, ast.USub):
        return False
    return isinstance(d, ast.Constant) and type(d.value) in (int, float) and d.value in (0, 1)


def _enters_arith(node, parents, tree):
    cur = node
    while cur in parents and not isinstance(cur, ast.stmt):
        p = parents[cur]
        if isinstance(p, ast.BinOp) and isinstance(p.op, ARITH):
            return True
        if isinstance(p, ast.AugAssign) and isinstance(p.op, ARITH + (ast.Add, ast.Sub)):
            return True
        if isinstance(p, ast.Call) and cur is not p.func and DISCOUNT_CALL.search(ast.unparse(p.func)):
            return True
        if isinstance(p, ast.Assign):
            tgt = p.targets[0] if len(p.targets) == 1 else None
            if isinstance(tgt, ast.Name):
                for n in ast.walk(tree):
                    if isinstance(n, ast.Name) and n.id == tgt.id and isinstance(n.ctx, ast.Load) and n is not tgt:
                        if _direct(n, parents):
                            return True
            return False
        cur = p
    return False


def _direct(node, parents):
    cur = node
    while cur in parents and not isinstance(cur, ast.stmt):
        p = parents[cur]
        if isinstance(p, ast.BinOp) and isinstance(p.op, ARITH):
            return True
        if isinstance(p, ast.AugAssign) and isinstance(p.op, ARITH):
            return True
        if isinstance(p, ast.Call) and cur is not p.func and DISCOUNT_CALL.search(ast.unparse(p.func)):
            return True
        cur = p
    return False


def get_default_arith(site, code):
    node = site["node"]
    if site["kind"] != "call" or not isinstance(node.func, ast.Attribute) or node.func.attr != "get" or not _zero_one_default(node):
        return False
    lex = (ast.unparse(node.func.value) + " " + ast.unparse(node.args[0])).lower()
    if not K2C_WORDS.search(lex) or K2C_NOT.search(lex) or PARAM_NAME.search(lex):
        return False
    tree = ast.parse(code)
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    me = next((n for n in ast.walk(tree) if isinstance(n, ast.Call) and n.lineno == node.lineno and n.col_offset == node.col_offset), None)
    return me is not None and _enters_arith(me, parents, tree)


def _triggered(card, site, passed, probe, seen, task: str = "", output: str = "", code: str = "") -> bool:
    t = card["trigger"]
    st, kind = t["static"], t["static"]["kind"]
    if VA_DDOF_BROAD and card.get("ddof_card"):
        return card["fn"] not in seen and not re.match(r"\s*print\(", site["line"])
    if t.get("group") and t["group"] in seen:
        return False
    if kind == "off":
        return False
    if kind in ("first_call", "first_attribute"):
        return card["fn"] not in seen
    if kind == "param_rules":
        if _skipped(site, st.get("skip", [])):
            return False
        if st.get("mixed_ddof") and mixed_ddof(code):
            return True
        return any(_task_has(r["require"], task) and not _task_has(r.get("forbid", ""), task)
                   and ((r.get("missing") and r["param"] not in passed) or
                        (r["param"] in passed and _literal(passed[r["param"]]) in r["values"]))
                   for r in st["rules"])
    if kind == "get_default_arith":
        return get_default_arith(site, code)
    if kind == "slice_then_lag":
        return slice_then_lag(site, code)
    if kind == "near_tie":
        return probe[5] is True and (card["fn"].endswith(".rank") or ORDER_RANK.search(code or "") is not None)
    if kind == "line_match":
        return re.search(st["pattern"], site["line"]) is not None and not _task_has(st.get("forbid", ""), task)
    if kind == "output_warning":
        return any(all(re.search(p, output or "") for p in group) for group in st["any"])
    if kind == "param_missing_or":
        return st["param"] not in passed or _literal(passed[st["param"]]) in st["values"]
    if kind == "param_is":
        return st["param"] in passed and _literal(passed[st["param"]]) in st["values"]
    if kind == "into_predict":
        par = site.get("parent")
        into = isinstance(par, ast.Call) and isinstance(par.func, ast.Attribute) and par.func.attr == "predict"
        rt = t.get("runtime") or {}
        if into and rt.get("kind") == "one_row_or_1d":
            ndim, rows = probe[2], probe[3]
            return ndim is not None and (ndim < 2 or rows == 1)
        return into
    return False


def _default(card, p):
    return next((x for x in card["params"] if x["name"] == p), {})


def _fact(card, p, passed):
    if p in passed:
        return f"Your line sets `{p}={passed[p]}`."
    return f"Your line does not set `{p}`, so it runs with `{p}={_default(card, p).get('default_repr')}`."


def card_note(card, site, passed, cell, version, callee, steps_mode="fix_line", same_cell=""):
    exact = site["line"]
    items = []
    for it in card["checklist"]:
        k = len(items) + 1
        segs = list(it["segments"])
        if it["kind"] == "axis":
            first = next((x["name"] for x in card["params"]), "a")
            segs[0] = segs[0].replace("{shown}", passed.get(first, "?"))
            block = _wrap(k, *segs)
            if "axis" in passed:
                block += f"\n   Your line sets `axis={passed['axis']}`."
        elif it["kind"] == "input":
            first = next((x["name"] for x in card["params"]), "data")
            block = _wrap(k, *[x.replace("{shown}", passed.get(first, "?")) for x in segs])
        elif it["kind"] == "calls":
            block = _wrap(k, *segs, f"Your line calls `{callee}`.")
        elif it["kind"] == "param":
            block = _wrap(k, *segs, *[_fact(card, p, passed) for p in it["params"]],
                          *([same_cell] if same_cell and it["rule"] == "ddof" else []))
        else:
            block = _wrap(k, *segs)
        items.append(block)
    head = f"API check on cell {cell}, line (exactly as it stands, with its indentation):\n```python\n{exact}\n```"
    body = "Check the following error-prone points of this call:\n" + "\n".join(items)
    if version == "D3":
        new, call_text = exact.strip(), ast.unparse(site["node"])
        for p, want in card["checklist_default"].items():
            have = _literal(passed[p]) if p in passed else _default(card, p).get("default")
            if want != have:
                new = _set_kw(new, call_text, p, want) if call_text in new else new
        if not card["checklist_default"]:
            return None
        steps = (VA_EDIT.format(cell=cell, old=exact.strip(), new=new) if new != exact.strip() else
                 "Nothing in this line needs a change; continue with your next step in this same reply.")
    elif steps_mode == "next_cell":
        steps = VA_STEPS_NEXT_CELL
    elif card.get("steps") == "cell":
        steps = VA_STEPS_CELL
    elif not card["task_driven"]:
        steps = VA_STEPS_API
    elif card["checklist_default"]:
        steps = VA_STEPS
    else:
        steps = VA_STEPS.replace(", or: not specified in the task instructions; checklist default", "")
    refs = list(card["references_always"]) + [l for p in passed if p != "self" for l in card["references_by_param"].get(p, [])]
    parts = [head, "", body, "", steps, "", f"Documentation of `{card['fn']}` (installed version, core part):", card["documentation"]]
    if refs:
        parts += ["", "Referenced documentation (followed from the text above):\n" + "\n".join(refs)]
    return "\n".join(parts)


def _set_kw(line: str, call_src: str, param: str, value) -> str:
    if re.search(rf"\b{param}\s*=", call_src):
        new_call = re.sub(rf"\b{param}\s*=\s*[^,)]+", f"{param}={value!r}", call_src, count=1)
    else:
        new_call = call_src[:-1] + (f"{param}={value!r})" if call_src.endswith("()") else f", {param}={value!r})")
    return line.replace(call_src, new_call, 1)


def va_notes(code: str, cell, sites: list, probe_output: str, cards: dict, seen: set, version: str = "D2",
             enabled=None, steps_mode: str = "fix_line", opened: list = None, task: str = "", output: str = "") -> list:
    m = re.search(r"VA_SITES (\{.*\})", probe_output or "")
    probe = json.loads(m.group(1)) if m else {}
    by_id = {s["id"]: s for s in sites}
    ddof_fns = []
    for k, v in sorted(((int(k), v) for k, v in probe.items())):
        if k in by_id and (f := _full_name(v[0], v[1], v[4], by_id[k]["kind"], by_id[k]["attr"], cards)) and cards[f].get("ddof_card"):
            ddof_fns.append(f)
    out = []
    for sid, vals in sorted(((int(k), v) for k, v in probe.items())):
        mod, qual, ndim, rows, self_type = vals[:5]
        near_tie = vals[5] if len(vals) > 5 else None
        s = by_id.get(sid)
        if s is None:
            continue
        fn = _full_name(mod, qual, self_type, s["kind"], s["attr"], cards)
        if fn is None or (enabled is not None and fn not in enabled):
            continue
        card = cards[fn]
        node = s["node"]
        receiver = ast.unparse(node.func.value) if s["kind"] == "call" and isinstance(node.func, ast.Attribute) and self_type else None
        passed = _passed(card, node, receiver) if s["kind"] == "call" else {}
        key = (fn, s["line"].strip())
        if key in seen or not _triggered(card, s, passed, [mod, qual, ndim, rows, self_type, near_tie], seen, task, output, code):
            continue
        other = next((f for f in ddof_fns if f != fn and cards[f].get("short") != card.get("short")), None) if card.get("ddof_card") else None
        same = f"`{cards[other]['short']}` in the same cell {cards[other]['ddof_default']}." if other else ""
        note = card_note(card, s, passed, cell, version, s["expr"], steps_mode, same)
        if note and card["trigger"]["static"].get("mixed_ddof") and mixed_ddof(code):
            note = note.replace("Check the following error-prone points", mixed_note(code) + "\n\nCheck the following error-prone points", 1)
        if note:
            seen.update({key, fn} | ({card["trigger"]["group"]} if card["trigger"].get("group") else set()))
            out.append(note)
            if opened is not None:
                opened.append({"cell": cell, "line": s["line"], "fn": fn})
    return out
