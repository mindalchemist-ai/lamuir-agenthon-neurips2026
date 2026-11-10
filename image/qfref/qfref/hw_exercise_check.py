import ast, re

_SCOPE = re.compile(r"bermudan|exercis|callable|early_ex", re.I)
_PAY = re.compile(r"pay|coupon|cash|cf\b|cfs\b|t_i\b|ti\b", re.I)
_EX = re.compile(r"exer|ex_val|exval|intrinsic|immediate|payoff", re.I)
_CONT = re.compile(r"cont|hold|continu|v_next|\bv\b|\bV\b", re.I)


def _src(code, node):
    return (ast.get_source_segment(code, node) or "").strip()


def _tiny(node):
    return isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and 0 < node.value <= 1e-6


def check_a(code):
    out = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return out
    if not _SCOPE.search(code):
        return out
    for n in ast.walk(tree):
        if not isinstance(n, ast.Compare) or len(n.ops) != 1:
            continue
        left, op, right = n.left, n.ops[0], n.comparators[0]
        if isinstance(op, ast.Lt):
            left, right = right, left
        elif not isinstance(op, ast.Gt):
            continue
        if isinstance(right, ast.BinOp) and isinstance(right.op, ast.Sub) and _tiny(right.right) and _PAY.search(_src(code, left)):
            out.append({"kind": "A", "line": _src(code, n), "lhs": _src(code, left), "rhs": _src(code, right.left),
                        "eps": _src(code, right.right)})
    return out


def _has_positive_term(node, code, ex_text):
    for sub in ast.walk(node):
        if isinstance(sub, ast.Compare) and len(sub.ops) == 1 and isinstance(sub.ops[0], (ast.Gt, ast.GtE)):
            r = sub.comparators[0]
            if isinstance(r, ast.Constant) and r.value == 0 and _src(code, sub.left) == ex_text:
                return True
            if isinstance(r, ast.Constant) and isinstance(r.value, (int, float)) and 0 < r.value <= 1e-6:
                return True
    return False


def check_b(code):
    out = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return out
    if not _SCOPE.search(code):
        return out
    for n in ast.walk(tree):
        if not isinstance(n, ast.Assign):
            continue
        cmps = [s for s in ast.walk(n.value) if isinstance(s, ast.Compare) and len(s.ops) == 1
                and isinstance(s.ops[0], ast.GtE)]
        positive_elsewhere = {_src(code, s.left) for s in ast.walk(tree) if isinstance(s, ast.Compare) and len(s.ops) == 1
                              and isinstance(s.ops[0], (ast.Gt, ast.GtE)) and isinstance(s.comparators[0], ast.Constant)
                              and isinstance(s.comparators[0].value, (int, float)) and 0 <= s.comparators[0].value <= 1e-6
                              and not (isinstance(s.ops[0], ast.GtE) and s.comparators[0].value == 0)}
        for c in cmps:
            lt, rt = _src(code, c.left), _src(code, c.comparators[0])
            if _EX.search(lt) and _CONT.search(rt) and not _EX.search(rt):
                if not _has_positive_term(n.value, code, lt) and lt not in positive_elsewhere:
                    out.append({"kind": "B", "line": _src(code, n), "ex": lt, "cont": rt})
    return out


def check(code):
    return check_a(code) + check_b(code)


def note(hits, cell_no):
    parts = []
    for h in hits:
        if h["kind"] == "A":
            parts.append(f"`{h['line']}` keeps a payment that falls exactly on `{h['rhs']}`: subtracting `{h['eps']}` turns `>` "
                         f"into `>=`. For payments strictly after the exercise date write `{h['lhs']} > {h['rhs']} + {h['eps']}`, "
                         f"or compare integer tree steps (`n_pay_i > n`).")
        else:
            parts.append(f"`{h['line']}` also marks nodes where `{h['ex']}` and `{h['cont']}` are both zero (deep out of the "
                         f"money), so the lowest such node becomes the boundary. An exercise node needs a positive exercise value: "
                         f"`({h['ex']} > 0) & ({h['ex']} >= {h['cont']})`.")
    return (f"Code check on your cell {cell_no}: " + " ".join(parts) +
            " In your next cell change only these lines, rerun the pricing loop, print the price and the boundary, and rewrite "
            "the file that holds them. If the task defines this differently, quote that sentence and keep yours.")
