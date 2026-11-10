import ast, re


def _src(code, node):
    return ast.get_source_segment(code, node) or ""


def _names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _row_col(node, row):
    for s in ast.walk(node):
        if isinstance(s, ast.Subscript) and isinstance(s.value, ast.Name) and s.value.id == row \
                and isinstance(s.slice, ast.Constant) and isinstance(s.slice.value, str):
            return s.slice.value
    return None


_BUILTINS = {"float", "int", "str", "abs", "round", "len", "bool", "max", "min", "sum", "list", "tuple", "pd", "np"}


def _is_map(v, row):
    if isinstance(v, ast.Call):
        f = v.func
        return (isinstance(f, ast.Name) and f.id not in _BUILTINS) or (isinstance(f, ast.Attribute) and f.attr == "get")
    return isinstance(v, ast.Subscript) and isinstance(v.value, ast.Name) and v.value.id != row


def topup_sites(code: str) -> list[dict]:
    sites = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return sites
    for loop in [n for n in ast.walk(tree) if isinstance(n, ast.For)]:
        it, tgt = loop.iter, loop.target
        if not (isinstance(it, ast.Call) and isinstance(it.func, ast.Attribute) and it.func.attr == "iterrows"):
            continue
        row = tgt.elts[-1].id if isinstance(tgt, ast.Tuple) and isinstance(tgt.elts[-1], ast.Name) else None
        if not row:
            continue
        frame = _src(code, it.func.value)
        body = sorted((n for n in ast.walk(loop) if isinstance(n, ast.Assign) and len(n.targets) == 1
                       and isinstance(n.targets[0], ast.Name) and n is not loop), key=lambda n: n.lineno)
        assigns = {}
        for st in body:
            assigns.setdefault(st.targets[0].id, st)
        key0 = col = None
        for st in body:
            v = st.value
            c = _row_col(v, row)
            if c is None:
                continue
            if _is_map(v, row):
                key0, col = st.targets[0].id, c
                break
        if key0 is None:
            for st in body:
                if _row_col(st.value, row):
                    name = st.targets[0].id
                    for st2 in body:
                        v2 = st2.value
                        if name in _names(v2) and st2.lineno > st.lineno and _is_map(v2, row):
                            key0, col = st2.targets[0].id, _row_col(st.value, row)
                            break
                if key0:
                    break
        if key0 is None:
            continue
        derived = {key0}
        for st in body:
            if _names(st.value) & derived and _row_col(st.value, row) is None:
                derived.add(st.targets[0].id)
        for st in body:
            v = st.value
            if not (isinstance(v, ast.BinOp) and isinstance(v.op, ast.Sub)):
                continue
            diff = st.targets[0].id
            right = v.right
            vis = assigns[right.id].value if isinstance(right, ast.Name) and right.id in assigns else right
            if not (isinstance(vis, ast.Subscript) and _names(vis.slice) & derived):
                continue
            left = v.left
            n_node = assigns[left.id].value if isinstance(left, ast.Name) and left.id in assigns else left
            n_col = _row_col(n_node, row)
            if n_col is None:
                continue
            guard_line = None
            for n in ast.walk(loop):
                if isinstance(n, ast.If) and isinstance(n.test, ast.Compare) and isinstance(n.test.left, ast.Name) \
                        and n.test.left.id == diff:
                    op = n.test.ops[0]
                    if isinstance(op, (ast.Gt, ast.GtE)) and any(isinstance(b, ast.AugAssign) and diff in _names(b.value)
                                                                  for b in ast.walk(n)):
                        guard_line = f"if {_src(code, n.test)}:"
                    elif isinstance(op, (ast.Lt, ast.LtE)) and any(isinstance(b, ast.Assign) and _names(b.targets[0]) == {diff}
                                                                    for b in n.body):
                        guard_line = f"if {_src(code, n.test)}: {diff} = 0"
                if isinstance(n, ast.AugAssign) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) \
                        and n.value.func.id == "max" and diff in _names(n.value):
                    guard_line = _src(code, n).strip()
                if guard_line:
                    break
            if guard_line is None:
                continue
            chain = [st2 for st2 in body if st2.lineno < st.lineno and st2.targets[0].id in derived | {key0}]
            first = next(s for s in body if s.targets[0].id == key0)
            pre = [s for s in body if s.lineno < first.lineno and s.targets[0].id in _names(first.value)]
            vis_name = right.id if isinstance(right, ast.Name) else None
            subst = {s2.targets[0].id: _src(code, s2.value) for s2 in pre + chain}
            order = [s2.targets[0].id for s2 in pre + chain]
            skips = []
            for n in ast.walk(loop):
                if isinstance(n, ast.If) and n.lineno < st.lineno and n.body and isinstance(n.body[0], ast.Continue):
                    used = [k for k, nm in enumerate(order) if nm in _names(n.test)]
                    if used:
                        skips.append((max(used), _src(code, n.test)))
            sites.append({"frame": frame, "row": row, "col": col, "n_col": n_col, "diff": diff, "key0": key0,
                          "subst": subst, "skips": skips,
                          "visible": _src(code, vis), "visible_name": vis_name,
                          "line_key": _src(code, first).strip(), "line_diff": _src(code, st).strip(),
                          "line_guard": guard_line,
                          "chain": [_src(code, s).strip() for s in pre + chain], "n_expr": _src(code, n_node)})
            break
    return sites


def topup_probe(site: dict) -> str:
    return ("import json as _mj\n"
            "_mo = []\n"
            "try:\n"
            "    _mg = {}\n"
            f"    for _, _mr in {site['frame']}.iterrows():\n"
            f"        _mns = {{{site['row']!r}: _mr}}\n"
            "        try:\n"
            "            _mskip = False\n"
            f"            for _mi, _ml in enumerate({site['chain']!r}):\n"
            "                exec(_ml, globals(), _mns)\n"
            f"                for _mj2, _mt in {site.get('skips', [])!r}:\n"
            "                    if _mj2 == _mi and bool(eval(_mt, globals(), _mns)):\n"
            "                        _mskip = True\n"
            "                if _mskip:\n"
            "                    break\n"
            "            if _mskip:\n"
            "                continue\n"
            f"            _mv = float(eval({site['visible']!r}, globals(), _mns))\n"
            f"            _mn = float(eval({site['n_expr']!r}, globals(), _mns))\n"
            "        except Exception:\n"
            "            continue\n"
            f"        _mk = repr(eval({site['visible'].split('[', 1)[1].rsplit(']', 1)[0]!r}, globals(), _mns))\n"
            f"        _mlab = str(_mns.get({site['key0']!r}))\n"
            f"        _mg.setdefault(_mk, []).append((str(_mr[{site['col']!r}]), _mn, _mv, _mlab))\n"
            "    for _mk, _ml in _mg.items():\n"
            "        if len(_ml) > 1 and sum(x[1] for x in _ml) > _ml[0][2] + 1e-9:\n"
            "            _mo.append({'target': _ml[0][3], 'sources': [x[0] for x in _ml], 'sum': sum(x[1] for x in _ml), 'visible': _ml[0][2]})\n"
            "except Exception:\n"
            "    pass\n"
            "print('MAPSKIP', _mj.dumps(_mo))")


def _inline(expr, subst, stop, depth=6):
    for _ in range(depth):
        new = expr
        for name, rhs in subst.items():
            if name not in stop:
                new = re.sub(r"\b%s\b" % re.escape(name), f"({rhs})", new)
        if new == expr:
            break
        expr = new
    return expr


def _example(site):
    row, col, key0 = site["row"], site["col"], site["key0"]
    sub = site["subst"]
    key_rhs = _inline(sub[key0], sub, {key0})
    key_rhs = re.sub(r"\b%s\s*\[\s*['\"]%s['\"]\s*\]" % (re.escape(row), re.escape(col)), "v", key_rhs)
    key_rhs = re.sub(r"\(\(v\)\)", "(v)", key_rhs)
    if re.search(r"\b%s\b" % re.escape(row), key_rhs):
        return None
    cell = _inline(site["visible"], {k: v for k, v in sub.items() if k != key0}, {key0})
    cell = re.sub(r"\b%s\b" % re.escape(key0), "t", cell)
    if re.search(r"\b%s\b" % re.escape(row), cell):
        return None
    own = set(sub) - {key0}
    skips = [re.sub(r"\b%s\b" % re.escape(key0), "t", t) for _, t in site.get("skips", [])
             if re.search(r"\b%s\b" % re.escape(key0), t) and not any(re.search(r"\b%s\b" % re.escape(o), t) for o in own | {row})]
    return key_rhs, cell, skips


def mapping_note(site: dict, cell_no, skipped: list | None) -> str:
    fr, col, ncol, diff = site["frame"], site["col"], site["n_col"], site["diff"]
    lines = [f"Mapping check on cell {cell_no}: `{site['line_key']}` maps source rows to targets, and each source row is "
             f"compared with the target's merged count (`{site['line_diff']}`) with negative differences dropped "
             f"(`{site['line_guard']}`)."]
    if skipped:
        parts = [f"target `{s['target']}`: source rows {', '.join(s['sources'])} add up to {s['sum']:g} while it holds "
                 f"{s['visible']:g}" for s in skipped]
        lines[0] += (f" Several source rows share one target here, and in the rows of `{fr}` after this cell "
                     + "; ".join(parts) + ", so part of the source counts was skipped.")
    ex = _example(site)
    if ex:
        key_rhs, cell, skips = ex
        lines[0] += " Add the source rows within each group first, then compare once per target, for example:"
        lines += ["    per_target = {}",
                  f"    for v, n in zip({fr}[{col!r}], {fr}[{ncol!r}]):",
                  f"        t = {key_rhs}",
                  "        if t is not None: per_target[t] = per_target.get(t, 0) + float(n)",
                  "    for t, n in per_target.items():"]
        lines += [f"        if {t}: continue" for t in skips]
        lines += [f"        {diff} = n - {cell}",
                  f"        if {diff} > 0: {cell} += {diff}"]
    else:
        lines[0] += " Add the source rows within each group first, then compare once per target."
    lines.append("If the task defines the correction per source row, quote that sentence and keep it.")
    return "\n".join(lines)
