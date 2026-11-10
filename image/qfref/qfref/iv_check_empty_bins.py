import ast, re

SUM_AGG = re.compile(r"""['"]sum['"]|\.sum\(""")
PRICE_AGG = re.compile(r"""['"](first|last|max|min|ohlc)['"]|\.(first|last|ohlc)\(""")
VOL = re.compile(r"vol", re.I)
INTRADAY = re.compile(r"^\d*\s*(min|T|h|H|s|S|ms|us)$")


def _strings(node):
    return [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def _inside_print(tree):
    skip = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print":
            for m in ast.walk(n):
                skip.add(id(m))
    return skip


def _effective_removal(call):
    f = call.func
    name = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
    kw = {k.arg: k.value for k in call.keywords}
    if name == "dropna":
        if "subset" in kw:
            cols = _strings(kw["subset"])
            return any(not VOL.search(c) for c in cols)
        how = kw.get("how")
        if isinstance(how, ast.Constant) and how.value == "all":
            return False
        return True
    if name in ("notna", "notnull", "isna", "isnull"):
        target = f.value if isinstance(f, ast.Attribute) else (call.args[0] if call.args else None)
        cols = _strings(target) if target is not None else []
        return bool(cols) and any(not VOL.search(c) for c in cols)
    if "min_count" in kw:
        return True
    if name == "count":
        return True
    return False


def resample_hits(code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    if not (SUM_AGG.search(code) and PRICE_AGG.search(code)):
        return []
    dicts = {}
    for st in ast.walk(tree):
        if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) and isinstance(st.value, ast.Dict):
            dicts[st.targets[0].id] = ast.unparse(st.value)
    targets = []
    for st in ast.walk(tree):
        if not (isinstance(st, ast.Assign) and len(st.targets) == 1):
            continue
        rs = [n for n in ast.walk(st.value) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "resample"]
        if not rs or not rs[0].args or not isinstance(rs[0].args[0], ast.Constant) or not isinstance(rs[0].args[0].value, str):
            continue
        if not INTRADAY.match(rs[0].args[0].value.strip()):
            continue
        src = ast.unparse(st.value)
        for nm in [n.id for n in ast.walk(st.value) if isinstance(n, ast.Name) and n.id in dicts]:
            src += dicts[nm]
        if SUM_AGG.search(src) and PRICE_AGG.search(src):
            targets.append((st.lineno, ast.unparse(st.targets[0])))
    if not targets:
        return []
    skip = _inside_print(tree)
    first = min(t[0] for t in targets)
    if any("count" in _strings(st) for st in ast.walk(tree) if isinstance(st, ast.Dict)):
        return []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and id(n) not in skip and getattr(n, "lineno", 0) >= first and _effective_removal(n):
            return []
    return targets


def check_run(cells):
    hits = []
    for c in cells:
        for lineno, name in resample_hits(c["code"]):
            hits.append((c["msg"], name))
    return hits
