import ast

LAG, W, WIN = "lag", "w", "win"


def _is_rev_slice(s):
    return isinstance(s, ast.Slice) and s.lower is None and s.upper is None and isinstance(s.step, ast.UnaryOp) and isinstance(s.step.op, ast.USub) and isinstance(s.step.operand, ast.Constant) and s.step.operand.value == 1


def _is_window_slice(s):
    if not isinstance(s, ast.Slice) or s.step is not None:
        return False
    if isinstance(s.lower, ast.BinOp) and isinstance(s.lower.op, ast.Sub) and s.upper is not None:
        return True
    if isinstance(s.lower, ast.UnaryOp) and isinstance(s.lower.op, ast.USub) and s.upper is None:
        return True
    return False


def _fname(call):
    f = call.func
    if isinstance(f, ast.Attribute):
        return f.attr
    if isinstance(f, ast.Name):
        return f.id
    return ""


def _contains_exp(node):
    return any(isinstance(n, ast.Call) and _fname(n) == "exp" for n in ast.walk(node))


class Analyzer:
    def __init__(self):
        self.env = {}
        self.funcs = {}
        self.hits = []
        self.depth = 0
        self.pending = {}

    def kind(self, e, env):
        if isinstance(e, ast.Name):
            return env.get(e.id)
        if isinstance(e, ast.Constant):
            return None
        if isinstance(e, ast.Attribute):
            if e.attr in ("values", "T", "to_numpy"):
                return self.kind(e.value, env)
            return None
        if isinstance(e, ast.Subscript):
            base = e.value
            if isinstance(base, ast.Attribute) and base.attr in ("iloc", "loc"):
                base = base.value
            k = self.kind(base, env)
            s = e.slice
            if isinstance(s, ast.Tuple) and s.elts:
                rev = [x for x in s.elts if _is_rev_slice(x)]
                win = [x for x in s.elts if _is_window_slice(x)]
                s = rev[0] if rev else (win[0] if win else s.elts[0])
            if _is_rev_slice(s):
                return (k[0], 1 - k[1]) if k else None
            if _is_window_slice(s):
                return k if k else (WIN, 0)
            ks = self.kind(s, env)
            if ks and ks[0] == WIN:
                return ks
            return k
        if isinstance(e, ast.Call):
            n = _fname(e)
            if n in ("arange", "range") and isinstance(e.func, (ast.Attribute, ast.Name)):
                a = e.args
                if len(a) == 2 and isinstance(a[0], ast.BinOp) and isinstance(a[0].op, ast.Sub):
                    return (WIN, 0)
                if len(a) == 3:
                    st = a[2]
                    if isinstance(st, ast.UnaryOp) and isinstance(st.op, ast.USub):
                        return (LAG, 1)
                return (LAG, 0)
            if n in ("flip", "flipud"):
                k = self.kind(e.args[0], env) if e.args else None
                return (k[0], 1 - k[1]) if k else None
            if n == "reversed":
                k = self.kind(e.args[0], env) if e.args else None
                return (k[0], 1 - k[1]) if k else None
            if n == "exp":
                k = self.kind(e.args[0], env) if e.args else None
                return (W, k[1]) if k and k[0] in (LAG, W) else None
            if n in ("array", "asarray", "copy", "astype", "to_numpy", "ravel", "flatten", "list", "vstack", "stack"):
                if e.args:
                    k = self.kind(e.args[0], env)
                    if k:
                        return k
                if isinstance(e.func, ast.Attribute):
                    return self.kind(e.func.value, env)
                return None
            if n == "tail":
                return (WIN, 0)
            if n in ("sum",):
                return None
            return None
        if isinstance(e, ast.BinOp):
            l, r = self.kind(e.left, env), self.kind(e.right, env)
            if isinstance(e.op, ast.Sub) and r and r[0] == LAG and not l:
                return (LAG, 1 - r[1])
            for k in (l, r):
                if k and k[0] in (LAG, W):
                    return k
            return None
        if isinstance(e, ast.UnaryOp):
            return self.kind(e.operand, env)
        if isinstance(e, ast.ListComp) and len(e.generators) == 1:
            g = e.generators[0]
            if not _contains_exp(e.elt):
                return None
            it = self.kind(g.iter, env)
            if it is None or it[0] != LAG:
                return None
            p = it[1]
            if isinstance(g.target, ast.Name):
                sub = [n for n in ast.walk(e.elt) if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Sub) and isinstance(n.right, ast.Name) and n.right.id == g.target.id]
                if sub:
                    p = 1 - p
            return (W, p)
        return None

    def combos(self, node, env, where):
        found = []
        for c in ast.walk(node):
            pair = None
            if isinstance(c, ast.Call):
                n = _fname(c)
                if n == "average":
                    kw = {k.arg: k.value for k in c.keywords}
                    if "weights" in kw and c.args:
                        pair = (kw["weights"], c.args[0])
                elif n in ("dot", "tensordot") and len(c.args) >= 2:
                    pair = (c.args[0], c.args[1])
                elif n == "sum" and isinstance(c.func, ast.Attribute) and isinstance(c.func.value, ast.BinOp) and isinstance(c.func.value.op, ast.Mult):
                    pair = (c.func.value.left, c.func.value.right)
                elif n == "sum" and c.args and isinstance(c.args[0], ast.BinOp) and isinstance(c.args[0].op, ast.Mult):
                    pair = (c.args[0].left, c.args[0].right)
            elif isinstance(c, ast.BinOp) and isinstance(c.op, ast.MatMult):
                pair = (c.left, c.right)
            if isinstance(c, ast.Call) and _fname(c) in self.funcs and self.depth < 2:
                fd = self.funcs[_fname(c)]
                sub = dict(env)
                for p, a in zip(fd.args.args, c.args):
                    k = self.kind(a, env)
                    if k:
                        sub[p.arg] = k
                self.depth += 1
                saved = self.pending
                self.pending = {}
                self.block(fd.body, sub, where)
                for v in self.pending.values():
                    found.extend(v)
                self.pending = saved
                self.depth -= 1
            if not pair:
                continue
            ka, kb = self.kind(pair[0], env), self.kind(pair[1], env)
            if ka and kb and {ka[0], kb[0]} == {W, WIN}:
                w, win = (ka, kb) if ka[0] == W else (kb, ka)
                if (w[1] ^ win[1]) == 0:
                    found.append((where, ast.unparse(c)[:160]))
        return found

    def block(self, stmts, env, where):
        for st in stmts:
            if isinstance(st, ast.FunctionDef):
                self.funcs[st.name] = st
                continue
            if isinstance(st, (ast.For, ast.While, ast.If, ast.With, ast.Try)):
                if isinstance(st, ast.For):
                    self.hits.extend(self.combos(st.iter, env, where))
                body = list(getattr(st, "body", [])) + list(getattr(st, "orelse", []))
                for h in getattr(st, "handlers", []):
                    body += h.body
                body += list(getattr(st, "finalbody", []))
                self.block(body, env, where)
                continue
            found = self.combos(st, env, where)
            tname = st.targets[0].id if isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name) else None
            if tname:
                if found:
                    self.pending[tname] = found
                elif not any(isinstance(n, ast.Name) and n.id == tname for n in ast.walk(st.value)):
                    self.pending.pop(tname, None)
            else:
                self.hits.extend(found)
            if isinstance(st, ast.Assign) and len(st.targets) == 1:
                t = st.targets[0]
                k = self.kind(st.value, env)
                if isinstance(t, ast.Name):
                    if k:
                        env[t.id] = k
                    else:
                        env.pop(t.id, None)
            elif isinstance(st, ast.AugAssign) and isinstance(st.target, ast.Name):
                pass

    def cell(self, code, where):
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return
        self.pending = {}
        self.block(tree.body, self.env, where)
        for v in self.pending.values():
            self.hits.extend(v)


def check_run(cells):
    a = Analyzer()
    for c in cells:
        a.cell(c["code"], c["msg"])
    return a.hits
