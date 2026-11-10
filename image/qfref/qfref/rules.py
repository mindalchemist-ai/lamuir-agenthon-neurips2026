import ast
import re

ZERO_LIKE = (0, 0.0, 1, 1.0)
DATE_CTORS = {"Timestamp", "to_datetime"}
ROW_FILTER_METHODS = {"query", "dropna", "head", "tail"}
WINDOW_METHODS = {"head", "tail"}
LAG_METHODS = {"shift": "K3", "diff": "K3d", "pct_change": "K3p"}
PARSE_CALLS = {"float", "int", "strptime", "strftime", "to_datetime", "Timestamp", "fromisoformat", "parse", "to_numeric", "Decimal"}
ROOT_CALLS = {"brentq", "newton", "bisect", "brenth", "root_scalar", "fsolve", "minimize", "least_squares", "curve_fit", "fit", "solve", "lstsq", "inv"}
SAFE_EXCEPT_CALLS = {"open", "read_csv", "read_json", "load", "loads", "read_parquet", "import_module", "listdir", "exists"}


def dotted(f):
    parts = []
    while isinstance(f, ast.Attribute):
        parts.append(f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        parts.append(f.id)
    parts.reverse()
    return ".".join(parts)


def call_tail(node):
    return node.func.attr if isinstance(node.func, ast.Attribute) else (node.func.id if isinstance(node.func, ast.Name) else "")


def kw(node, name):
    for k in node.keywords:
        if k.arg == name:
            return k.value
    return None


def base_name(e):
    while True:
        if isinstance(e, ast.Name):
            return e.id
        if isinstance(e, (ast.Attribute,)):
            e = e.value
        elif isinstance(e, ast.Subscript):
            e = e.value
        elif isinstance(e, ast.Call):
            e = e.func
        else:
            return None


def target_key(t):
    if isinstance(t, ast.Name):
        return t.id
    if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
        s = t.slice
        if isinstance(s, ast.Constant):
            return "%s[%r]" % (t.value.id, s.value)
        return t.value.id + "[...]"
    if isinstance(t, ast.Attribute):
        return dotted(t)
    if isinstance(t, (ast.Tuple, ast.List)):
        return None
    return None


def expr_key(e):
    if isinstance(e, ast.Name):
        return e.id
    if isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name) and isinstance(e.slice, ast.Constant):
        return "%s[%r]" % (e.value.id, e.slice.value)
    return None


def is_row_slice_sub(e):
    if not isinstance(e, ast.Subscript):
        return None
    s = e.slice
    owner = e.value
    if isinstance(owner, ast.Attribute) and owner.attr in ("iloc", "loc"):
        sl = s.elts[0] if isinstance(s, ast.Tuple) and s.elts else s
        if isinstance(sl, ast.Slice):
            return "window"
        if isinstance(sl, (ast.Compare, ast.BoolOp, ast.UnaryOp)) or (isinstance(sl, ast.BinOp) and isinstance(sl.op, (ast.BitAnd, ast.BitOr))):
            return "mask"
        if isinstance(sl, ast.Call) and call_tail(sl) in ("isin", "between", "notna", "notnull", "isna"):
            return "mask"
        return None
    if isinstance(s, ast.Slice):
        return "window"
    if isinstance(s, (ast.Compare, ast.BoolOp)) or (isinstance(s, ast.BinOp) and isinstance(s.op, (ast.BitAnd, ast.BitOr))):
        return "mask"
    if isinstance(s, ast.Call) and call_tail(s) in ("isin", "between", "notna", "notnull"):
        return "mask"
    if isinstance(s, ast.UnaryOp) and isinstance(s.op, ast.Invert):
        return "mask"
    if isinstance(s, ast.Name) and "mask" in s.id.lower():
        return "mask"
    return None


def row_filter_kind(e, ctx):
    cur = e
    while True:
        k = is_row_slice_sub(cur)
        if k:
            return k
        if isinstance(cur, ast.Call):
            t = call_tail(cur)
            if t in WINDOW_METHODS:
                return "window"
            if t in ("query", "dropna"):
                return "mask"
            cur = cur.func.value if isinstance(cur.func, ast.Attribute) else None
        elif isinstance(cur, ast.Attribute):
            cur = cur.value
        elif isinstance(cur, ast.Subscript):
            cur = cur.value
        elif isinstance(cur, ast.Name):
            return ctx["sliced"].get(cur.id)
        else:
            return None
        if cur is None:
            return None


def is_date_scalar(e, ctx):
    if isinstance(e, ast.Name):
        return e.id in ctx["date_scalars"]
    if isinstance(e, ast.Call) and call_tail(e) in DATE_CTORS and e.args:
        a = e.args[0]
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            return ":" not in a.value and "T" not in a.value
        if isinstance(a, ast.Subscript) and base_name(a) in ctx["json_names"]:
            return True
        if isinstance(a, ast.Name) and a.id in ctx["date_strs"]:
            return True
        if call_tail(e) == "Timestamp" and isinstance(a, (ast.Name, ast.Subscript)) and base_name(a) not in ctx["frames"]:
            return True
    if isinstance(e, ast.Call) and call_tail(e) in ("normalize", "floor") and isinstance(e.func, ast.Attribute):
        return False
    return False


def contains_const_marker(e):
    src = ast.unparse(e)
    return ("add_constant" in src or "ones" in src or "'const'" in src or '"const"' in src
            or "intercept" in src.lower() or "full(" in src or "ones_like" in src)


class Ctx(dict):
    pass


def new_ctx():
    return Ctx(date_scalars=set(), json_names=set(), date_strs=set(), frames=set(), sliced={}, shifted=set(),
               known_cols={}, const_names=set(), assign_src={}, pct100=set(), uses_pandas_std=False,
               sliced_loop={}, boolcmp=set(), boolprev=set(), _par={})


def update_ctx(tree, ctx):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            rhs = node.value
            for t in node.targets:
                tk = target_key(t)
                names = [t.id] if isinstance(t, ast.Name) else []
                if isinstance(t, (ast.Tuple, ast.List)):
                    names = [x.id for x in t.elts if isinstance(x, ast.Name)]
                src = ast.unparse(rhs)
                for n in names:
                    ctx["assign_src"].setdefault(n, []).append(src)
                    if isinstance(rhs, ast.Call) and call_tail(rhs) in ("load", "loads") and "json" in dotted(rhs.func):
                        ctx["json_names"].add(n)
                    if isinstance(rhs, ast.Subscript) and base_name(rhs) in ctx["json_names"]:
                        ctx["json_names"].add(n)
                        ctx["date_strs"].add(n) if "date" in n.lower() or "end" in n.lower() or "start" in n.lower() else None
                    if is_date_scalar(rhs, ctx):
                        ctx["date_scalars"].add(n)
                    else:
                        ctx["date_scalars"].discard(n)
                    if isinstance(rhs, ast.Call) and call_tail(rhs) in ("read_csv", "read_parquet", "DataFrame", "merge", "concat", "read_json", "read_excel"):
                        ctx["frames"].add(n)
                    k = row_filter_kind(rhs, ctx) if not (isinstance(rhs, ast.Call) and call_tail(rhs) in ("read_csv", "DataFrame")) else None
                    if k:
                        ctx["sliced"][n] = k
                    elif n in ctx["sliced"] and not (isinstance(rhs, ast.Call) and call_tail(rhs) == "copy"):
                        ctx["sliced"].pop(n, None)
                    if contains_const_marker(rhs) or ({x.id for x in ast.walk(rhs) if isinstance(x, ast.Name)} & ctx["const_names"]):
                        ctx["const_names"].add(n)
                    wk = loop_window_slice(rhs)
                    if wk:
                        ctx["sliced_loop"][n] = id(innermost_loop(node, ctx["_par"]))
                    else:
                        ctx["sliced_loop"].pop(n, None)
                    if re.search(r"\*\s*100\b|100\s*\*", src):
                        ctx["pct100"].add(n)
                    cols = set(re.findall(r"'([^']+)'|\"([^\"]+)\"", src))
                    cols = {a or b for a, b in cols}
                    if isinstance(rhs, ast.Call) and call_tail(rhs) == "rename":
                        prev = ctx["known_cols"].get(base_name(rhs.func.value), set()) if isinstance(rhs.func, ast.Attribute) else set()
                        cols |= prev
                    ctx["known_cols"][n] = cols
                if tk:
                    if (isinstance(rhs, ast.Compare) and len(rhs.ops) == 1 and isinstance(rhs.ops[0], (ast.Gt, ast.Lt, ast.GtE, ast.LtE)) and not isinstance(rhs.comparators[0], ast.Constant) and not isinstance(rhs.left, ast.Constant)) or expr_key(strip_fill(rhs)) in ctx["boolcmp"]:
                        ctx["boolcmp"].add(tk)
                    else:
                        ctx["boolcmp"].discard(tk)
                    if is_prev_of_bool(rhs, ctx):
                        ctx["boolprev"].add(tk)
                    else:
                        ctx["boolprev"].discard(tk)
                if tk and "shift(" in ast.unparse(rhs) and not re.search(r"fillna|fill_value", ast.unparse(rhs)):
                    ctx["shifted"].add(tk)
                elif tk:
                    ctx["shifted"].discard(tk)
        if isinstance(node, ast.Call) and call_tail(node) in ("std", "var") and isinstance(node.func, ast.Attribute) and not dotted(node.func).startswith("np."):
            ctx["uses_pandas_std"] = True


def innermost_loop(node, par):
    cur = node
    while cur in par:
        cur = par[cur]
        if isinstance(cur, (ast.For, ast.While, ast.comprehension, ast.FunctionDef)):
            return cur
    return None


def nonconst(e):
    return e is not None and not isinstance(e, ast.Constant) and not (isinstance(e, ast.UnaryOp) and isinstance(e.operand, ast.Constant))


def loop_window_slice(e):
    cur = e
    while isinstance(cur, ast.Call) and call_tail(cur) in ("copy", "reset_index", "sort_index") and isinstance(cur.func, ast.Attribute):
        cur = cur.func.value
    if isinstance(cur, ast.Subscript) and isinstance(cur.value, ast.Attribute) and cur.value.attr in ("iloc", "loc"):
        sl = cur.slice.elts[0] if isinstance(cur.slice, ast.Tuple) and cur.slice.elts else cur.slice
        if isinstance(sl, ast.Slice) and (nonconst(sl.lower) or nonconst(sl.upper)):
            return True
    return False


def strip_fill(e):
    while isinstance(e, ast.Call) and call_tail(e) in ("fillna", "astype") and isinstance(e.func, ast.Attribute):
        e = e.func.value
    return e


def is_prev_of_bool(e, ctx):
    e = strip_fill(e)
    if isinstance(e, ast.Call) and call_tail(e) == "shift" and isinstance(e.func, ast.Attribute):
        return expr_key(e.func.value) in ctx["boolcmp"]
    return expr_key(e) in ctx["boolprev"]


def scalar_index(sub, node, par):
    s = sub.slice
    if isinstance(s, ast.Constant) and isinstance(s.value, int):
        return True
    if isinstance(s, ast.UnaryOp) and isinstance(s.operand, ast.Constant):
        return True
    if isinstance(s, ast.Name):
        cur = node
        while cur in par:
            cur = par[cur]
            if isinstance(cur, (ast.For, ast.comprehension)) and isinstance(cur.target, ast.Name) and cur.target.id == s.id:
                return True
    return False


def parents(tree):
    par = {}
    for p in ast.walk(tree):
        for c in ast.iter_child_nodes(p):
            par[c] = p
    return par


def in_accumulation(node, par):
    cur = node
    while cur in par:
        p = par[cur]
        if isinstance(p, ast.BinOp) and isinstance(p.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            return True
        if isinstance(p, ast.AugAssign):
            return True
        if isinstance(p, ast.Call) and call_tail(p) in ("sum", "prod", "fsum", "cumsum", "cumprod", "dot", "exp", "log"):
            return True
        if isinstance(p, (ast.stmt,)):
            return False
        cur = p
    return False


def flatten(stmts):
    for st in stmts:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield from flatten(st.body)
        elif isinstance(st, (ast.For, ast.AsyncFor)):
            yield st.iter
            yield from flatten(st.body)
            yield from flatten(st.orelse)
        elif isinstance(st, (ast.If, ast.While)):
            yield st.test
            yield from flatten(st.body)
            yield from flatten(st.orelse)
        elif isinstance(st, (ast.With, ast.AsyncWith)):
            for it in st.items:
                yield it.context_expr
            yield from flatten(st.body)
        elif isinstance(st, ast.Try):
            yield from flatten(st.body)
            for h in st.handlers:
                yield from flatten(h.body)
            yield from flatten(st.orelse)
            yield from flatten(st.finalbody)
        else:
            yield st


def check(root, par, ctx, run_meta):
    hits = []
    for node in ast.walk(root):
        if isinstance(node, ast.Call):
            tail = call_tail(node)
            dn = dotted(node.func)
            if tail == "add_constant" and node.args and kw(node, "has_constant") is None:
                a = node.args[0]
                why = None
                if isinstance(a, (ast.List, ast.Tuple)):
                    why = "list literal" if not (a.elts and isinstance(a.elts[0], (ast.List, ast.Tuple))) else ("single-row literal" if len(a.elts) == 1 else None)
                elif isinstance(a, ast.Call) and call_tail(a) in ("array", "asarray", "atleast_1d", "atleast_2d") and a.args and isinstance(a.args[0], (ast.List, ast.Tuple)):
                    inner = a.args[0]
                    if not (inner.elts and isinstance(inner.elts[0], (ast.List, ast.Tuple))):
                        why = "np.array of 1-D literal"
                    elif len(inner.elts) == 1:
                        why = "single-row 2-D literal"
                elif isinstance(a, ast.Subscript) and scalar_index(a, node, par):
                    why = "single element/row subscript"
                elif isinstance(a, ast.Call) and call_tail(a) == "reshape" and len(a.args) >= 1 and isinstance(a.args[0], ast.Constant) and a.args[0].value == 1:
                    why = "reshape(1, -1) single row"
                if why:
                    hits.append(("K1", node, dict(why=why, arg=ast.unparse(a)[:80])))
            if tail == "get" and len(node.args) == 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value in ZERO_LIKE and not isinstance(node.args[1].value, bool):
                if "environ" not in dn and in_accumulation(node, par):
                    stmt = node
                    while stmt in par and not isinstance(stmt, ast.stmt):
                        stmt = par[stmt]
                    counter = False
                    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Subscript):
                        counter = ast.unparse(stmt.targets[0].value) == ast.unparse(node.func.value)
                    if not counter:
                        hits.append(("K2", node, dict(recv=ast.unparse(node.func.value)[:60], key=ast.unparse(node.args[0])[:40], default=node.args[1].value)))
                        lex = (ast.unparse(node.func.value) + " " + ast.unparse(node.args[0])).lower()
                        if re.search(r"(^|[^a-z])(df|dfs|disc\w*|discount\w*|zero\w*|zc\w*|rates?|curve\w*|spot\w*|prices?|px|yields?|fx|fwd\w*|forward\w*|surv\w*|hazard\w*|par\w*|quote\w*)([^a-z]|$)", lex) and not re.search(r"weight|count|vec|tf|idf|hold|kwargs|params|config|instr", lex):
                            hits.append(("K2c", node, dict(recv=ast.unparse(node.func.value)[:60])))
            if tail in LAG_METHODS and isinstance(node.func, ast.Attribute):
                k = row_filter_kind(node.func.value, ctx)
                if k:
                    hits.append((LAG_METHODS[tail] + ("w" if k == "window" else "m"), node, dict(recv=ast.unparse(node.func.value)[:80])))
            if tail in LAG_METHODS and isinstance(node.func, ast.Attribute):
                recv = node.func.value
                b = base_name(recv)
                if loop_window_slice(recv) or (b in ctx["sliced_loop"] and ctx["sliced_loop"][b] == id(innermost_loop(node, par)) and innermost_loop(node, par) is not None):
                    hits.append(("K3L", node, dict(recv=ast.unparse(recv)[:80], fn=tail)))
            if tail == "shift" and kw(node, "fill_value") is not None and isinstance(kw(node, "fill_value"), ast.Constant) and kw(node, "fill_value").value is False:
                hits.append(("K4", node, dict(form="shift(fill_value=False)")))
            if tail in ("fillna", "astype") and isinstance(node.func, ast.Attribute):
                recv = node.func.value
                arg = node.args[0] if node.args else None
                is_false = isinstance(arg, ast.Constant) and arg.value is False
                is_bool = (isinstance(arg, ast.Name) and arg.id == "bool") or (isinstance(arg, ast.Constant) and arg.value == "bool")
                shifted = (isinstance(recv, ast.Call) and call_tail(recv) == "shift") or (expr_key(recv) in ctx["shifted"])
                if shifted and ((tail == "fillna" and is_false) or (tail == "astype" and is_bool and not (isinstance(recv, ast.Call) and call_tail(recv) == "fillna"))):
                    hits.append(("K4", node, dict(form=ast.unparse(node)[:80])))
            if tail == "between" and len(node.args) >= 2 and is_date_scalar(node.args[1], ctx):
                hits.append(("K5", node, dict(form="between", bound=ast.unparse(node.args[1])[:60])))
            if dn in ("np.random.default_rng", "numpy.random.default_rng", "np.random.seed", "np.random.RandomState", "default_rng"):
                if run_meta.get("seed_only"):
                    hits.append(("K7", node, dict(form=dn)))
            if tail == "rename" and isinstance(node.func, ast.Attribute):
                m = kw(node, "columns")
                if isinstance(m, ast.Dict):
                    known = set()
                    b = base_name(node.func.value)
                    sel = [x for x in ast.walk(node.func.value) if isinstance(x, ast.Subscript) and isinstance(x.slice, ast.List)]
                    if not sel:
                        known |= ctx["known_cols"].get(b, set())
                    for s in ast.walk(node.func.value):
                        if isinstance(s, ast.Constant) and isinstance(s.value, str):
                            known.add(s.value)
                    vals = [v.value for v in m.values if isinstance(v, ast.Constant)]
                    keys = [k.value for k in m.keys if isinstance(k, ast.Constant)]
                    for k_, v_ in zip(keys, vals):
                        if v_ in known and k_ != v_ and k_ in known:
                            hits.append(("K8", node, dict(src=k_, dst=v_)))
                    if len(vals) != len(set(vals)):
                        hits.append(("K8", node, dict(dup_values=True)))
            if tail == "to_datetime" and isinstance(kw(node, "errors"), ast.Constant) and kw(node, "errors").value == "coerce":
                hits.append(("E2", node, {}))
            if tail in ("get_indexer", "reindex", "get_loc") and isinstance(kw(node, "method"), ast.Constant) and kw(node, "method").value == "nearest":
                hits.append(("E3", node, dict(form=tail)))
            if tail == "merge_asof" and isinstance(kw(node, "direction"), ast.Constant) and kw(node, "direction").value == "nearest":
                hits.append(("E3", node, dict(form="merge_asof nearest")))
            if tail == "fillna" and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 0 and isinstance(node.func, ast.Attribute):
                r = node.func.value
                if isinstance(r, ast.Call) and call_tail(r) in ("merge", "reindex", "join"):
                    hits.append(("E4", node, dict(after=call_tail(r))))
                    stmt_src = ast.unparse(node).lower()
                    tgt = ""
                    cur = node
                    while cur in par and not isinstance(cur, ast.stmt):
                        cur = par[cur]
                    if isinstance(cur, ast.Assign):
                        tgt = ast.unparse(cur.targets[0]).lower()
                    if not re.search(r"(^|[^a-z])w(_|$|[0-9])|weight|^w_|hold|count|position|pos\b", tgt + " " + stmt_src.split(".reindex")[0]):
                        hits.append(("E4v", node, dict(after=call_tail(r))))
            if dn in ("np.std", "np.var", "numpy.std", "numpy.var") and kw(node, "ddof") is None and ctx["uses_pandas_std"]:
                hits.append(("D1", node, dict(fn=dn)))
            if tail in ("drop_duplicates", "last", "first", "duplicated") and isinstance(node.func, ast.Attribute):
                cur = node.func.value
                while isinstance(cur, (ast.Call, ast.Attribute, ast.Subscript)):
                    if isinstance(cur, ast.Call) and call_tail(cur) == "sort_values":
                        by = kw(cur, "by") or (cur.args[0] if cur.args else None)
                        single = isinstance(by, ast.Constant) or (isinstance(by, (ast.List, ast.Tuple)) and len(by.elts) == 1)
                        if single and kw(cur, "kind") is None:
                            hits.append(("D2", node, dict(by=ast.unparse(by)[:40] if by is not None else "")))
                        break
                    cur = cur.func if isinstance(cur, ast.Call) else cur.value
            if tail == "percentile" and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, (int, float)) and 0 < node.args[1].value < 1:
                hits.append(("D4", node, dict(form="percentile q<1")))
            if tail == "ppf" and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, (int, float)) and node.args[0].value > 1:
                hits.append(("D4", node, dict(form="ppf q>1")))
            if dn in ("stats.skew", "stats.kurtosis", "scipy.stats.skew", "scipy.stats.kurtosis", "skew", "kurtosis") and node.args and kw(node, "bias") is None:
                hits.append(("D5", node, dict(fn=dn)))
            if tail in ("OLS", "WLS", "GLS") and len(node.args) >= 2:
                X = node.args[1]
                ok = contains_const_marker(X)
                if isinstance(X, ast.Name):
                    ok = ok or X.id in ctx["const_names"] or any(contains_const_marker(ast.parse(s, mode="eval").body) if _parses(s) else False for s in ctx["assign_src"].get(X.id, []))
                if not ok and kw(node, "hasconst") is None:
                    hits.append(("D6", node, dict(X=ast.unparse(X)[:60])))
            if tail == "arch_model" and node.args:
                y = node.args[0]
                ysrc = ast.unparse(y)
                scaled = bool(re.search(r"100", ysrc)) or (isinstance(y, ast.Name) and y.id in ctx["pct100"])
                if not scaled and kw(node, "rescale") is None:
                    hits.append(("D7", node, dict(y=ysrc[:60])))
            if tail == "shift" and isinstance(node.func, ast.Attribute) and "conditional_volatility" in ast.unparse(node.func.value):
                hits.append(("D8", node, {}))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd):
            kinds = set()
            for side in (node.left, node.right):
                e = side.operand if isinstance(side, ast.UnaryOp) and isinstance(side.op, ast.Invert) else side
                if expr_key(e) in ctx["boolcmp"]:
                    kinds.add("cur")
                elif is_prev_of_bool(e, ctx):
                    kinds.add("prev")
            if kinds == {"cur", "prev"}:
                hits.append(("K4x", node, dict(form=ast.unparse(node)[:80])))
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            op = node.ops[0]
            L, R = node.left, node.comparators[0]
            for col, sc, bad in ((L, R, (ast.LtE, ast.Gt)), (R, L, (ast.GtE, ast.Lt))):
                if isinstance(op, bad) and is_date_scalar(sc, ctx) and not is_date_scalar(col, ctx) and not isinstance(col, ast.Constant):
                    scs, cols_ = ast.unparse(sc).lower(), ast.unparse(col).lower()
                    timey_scalar = bool(re.search(r"time|_ts|ts_|dt\b|_dt|hour|minute|stamp", scs))
                    timey_col = bool(re.search(r"time|_ts\b|ts_|datetime|stamp|bar|minute|hour", cols_))
                    hits.append(("K5", node, dict(form=ast.unparse(node)[:80], timey_scalar=timey_scalar, timey_col=timey_col)))
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute) and node.value.attr == "loc":
            s = node.slice
            sl = s.elts[0] if isinstance(s, ast.Tuple) and s.elts else s
            if isinstance(sl, ast.Slice):
                if sl.upper is not None and is_date_scalar(sl.upper, ctx):
                    hits.append(("K5", node, dict(form="loc slice end " + ast.unparse(sl.upper)[:40])))
                if isinstance(sl.upper, ast.BinOp) and isinstance(sl.upper.op, (ast.Add, ast.Sub)):
                    hits.append(("D3", node, dict(form=ast.unparse(sl)[:60])))
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Attribute) and t.attr == "columns" and isinstance(node.value, ast.List):
                vals = [e.value for e in node.value.elts if isinstance(e, ast.Constant)]
                if len(vals) != len(set(vals)):
                    hits.append(("K8", node, dict(dup_literal=True)))
            if isinstance(t, ast.Subscript) and isinstance(node.value, ast.Call) and call_tail(node.value) == "apply" and ".groupby(" in ast.unparse(node.value):
                hits.append(("D9", node, {}))
    return hits


def check_try(tree, par):
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            body = node.body
            fallback = all(isinstance(b, (ast.Pass, ast.Continue)) or
                           (isinstance(b, ast.Return) and (b.value is None or isinstance(b.value, ast.Constant) or "nan" in ast.unparse(b.value))) or
                           (isinstance(b, ast.Assign) and (isinstance(b.value, ast.Constant) or "nan" in ast.unparse(b.value)))
                           for b in body)
            tr = par.get(node)
            if fallback and isinstance(tr, ast.Try):
                trysrc = " ".join(ast.unparse(x) for x in tr.body)
                calls = {call_tail(c) for x in tr.body for c in ast.walk(x) if isinstance(c, ast.Call)}
                if not (calls & SAFE_EXCEPT_CALLS) and "import" not in trysrc[:20]:
                    hits.append(("E1", node, dict(calls=sorted(calls)[:6])))
                    if calls & PARSE_CALLS:
                        hits.append(("E1p", node, dict(calls=sorted(calls & PARSE_CALLS))))
                    elif calls & ROOT_CALLS:
                        hits.append(("E1r", node, dict(calls=sorted(calls & ROOT_CALLS))))
    return hits


def _parses(s):
    try:
        ast.parse(s, mode="eval")
        return True
    except SyntaxError:
        return False
