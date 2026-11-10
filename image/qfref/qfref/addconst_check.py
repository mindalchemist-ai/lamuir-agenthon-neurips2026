import ast, re


def _src(code, node):
    return ast.get_source_segment(code, node) or ""


def _is_add_constant(call):
    if not isinstance(call, ast.Call):
        return False
    f = call.func
    return ((isinstance(f, ast.Attribute) and f.attr == "add_constant") or
                                            (isinstance(f, ast.Name) and f.id == "add_constant"))


def _one(node):
    return isinstance(node, ast.Constant) and node.value in (1, 1.0)


def addconst_sites(code: str) -> list[dict]:
    sites = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return sites
    made = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and _is_add_constant(n.value):
            made[n.targets[0].id] = n.value
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "predict" and n.args):
            continue
        a = n.args[0]
        ac = a if _is_add_constant(a) else made.get(a.id) if isinstance(a, ast.Name) else None
        if ac is None or not ac.args:
            continue
        lst = ac.args[0]
        if isinstance(lst, (ast.List, ast.Tuple)) and len(lst.elts) == 2 and _one(lst.elts[0]) and not _one(lst.elts[1]):
            sites.append({"model": _src(code, n.func.value), "expr": _src(code, ac), "x": _src(code, lst.elts[1]),
                          "call": _src(code, n), "line": next((l.strip() for l in code.splitlines() if _src(code, n) in l), "")})
    return sites


def addconst_probe(site: dict) -> str:
    return ("import json as _acj\n"
            "try:\n"
            "    import numpy as _acn\n"
            f"    _acx = _acn.asarray({site['expr']})\n"
            f"    _acp = _acn.asarray({site['model']}.params, dtype=float).ravel()\n"
            f"    _acw = float(_acn.asarray({site['model']}.predict({site['expr']})).ravel()[0])\n"
            f"    _acr = float(_acp[0] + _acp[1] * float({site['x']}))\n"
            "    print('ADDCONST', _acj.dumps({'shape': list(_acx.shape), 'wrong': _acw, 'right': _acr}))\n"
            "except Exception:\n"
            "    print('ADDCONST null')")


def addconst_result(probe_output: str):
    m = re.search(r"ADDCONST (\{.*\}|null)", probe_output or "")
    try:
        r = __import__("json").loads(m.group(1)) if m else None
    except ValueError:
        return None
    if r and r["shape"] == [2, 2] and abs(r["wrong"] - r["right"]) > 1e-12 * max(1.0, abs(r["right"])):
        return r
    return None


def addconst_note(site: dict, cell_no, r: dict) -> str:
    x, m = site["x"], site["model"]
    return (f"Code check: cell {cell_no} calls `{site['expr']}`, and that design matrix has shape (2, 2). add_constant "
            f"treats a 1-D list as one column of observations, so it built the rows [[1, 1], [1, {x}]], and "
            f"`.predict(...)[0]` is the fit at x = 1, not at x = {x}. In your session: {m}.predict(...)[0] = "
            f"{r['wrong']:.6g}; {m}.params[0] + {m}.params[1] * {x} = {r['right']:.6g}. Build the single row explicitly:\n"
            f"    x_row = np.array([[1.0, float({x})]]); y_hat = {m}.predict(x_row)[0]\n"
            f"Recompute every prediction made this way and rewrite the files that use them. If you meant the fit at "
            f"x = 1, say so and keep it.")
