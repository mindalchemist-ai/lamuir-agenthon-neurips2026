import ast, glob, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_DIR = os.environ.get("API_LINT_RULES_DIR", "/Users/Agenthon/fca-mini-swe/mini-swe/analysis/v212-90pct/research_1026/api_lint")
sys.path.insert(0, HERE)
sys.path.insert(0, RULES_DIR)
import rules
from addconst_check import addconst_sites, addconst_probe, addconst_result, addconst_note
from oc11a_checks import slice_lag_hits, slice_lag_note, midnight_date_notes

ENABLED = {"K1": True, "K3L": True, "K5i": True, "K6": False, "K4x": False, "K2c": False}
SUFFIX = " If your setup satisfies a condition this check cannot see, say which and keep it."
FAMILY = {"K1": "addconst", "K3L": "lag-in-window", "T5": "lag-in-window", "K5i": "date-bound", "A89": "date-bound",
          "K6": "date-midnight", "T6": "date-midnight", "K4x": "crossover", "K2c": "get-default"}


def _line(code, node):
    return code.splitlines()[node.lineno - 1].strip() if getattr(node, "lineno", 0) else ast.unparse(node)


class ApiLint:

    def __init__(self, enabled=None):
        self.enabled = dict(ENABLED, **(enabled or {}))
        self.ctx = rules.new_ctx()
        self.shown = set()
        self.history = []

    def cell(self, code: str, cell_no) -> list[dict]:
        sites = []
        try:
            tree = ast.parse(code)
        except SyntaxError:
            self.history.append(code)
            return sites
        par = rules.parents(tree)
        self.ctx["_par"] = par
        rule_hits = []
        for unit in rules.flatten(tree.body):
            rule_hits += rules.check(unit, par, self.ctx, {})
            rules.update_ctx(unit, self.ctx)
        if self.enabled["K1"]:
            for s in addconst_sites(code):
                sites.append(dict(rule="K1", key=(FAMILY["K1"], s["call"]), cell=cell_no, site=s, probe=addconst_probe(s)))
        t5 = {h["shift_line"]: h for h in slice_lag_hits(code)}
        for rid, node, det in rule_hits:
            line = _line(code, node)
            if rid == "K3L" and self.enabled["K3L"]:
                sites.append(dict(rule="K3L", key=(FAMILY["K3L"], line), cell=cell_no, line=line, lineno=node.lineno,
                                  det=det, t5=t5.pop(line, None), probe=None))
            elif rid == "K5" and self.enabled["K5i"] and isinstance(node, ast.Compare):
                s = self._k5i_site(node, line, det)
                if s:
                    sites.append(dict(s, cell=cell_no))
            elif rid == "K4x" and self.enabled["K4x"]:
                sites.append(dict(rule="K4x", key=(FAMILY["K4x"], line), cell=cell_no, line=line, lineno=node.lineno,
                                  expr=ast.unparse(node), probe=self._k4x_probe(node)))
            elif rid == "K2c" and self.enabled["K2c"]:
                sites.append(dict(rule="K2c", key=(FAMILY["K2c"], line), cell=cell_no, line=line, lineno=node.lineno,
                                  recv=ast.unparse(node.func.value), k=ast.unparse(node.args[0]),
                                  default=repr(node.args[1].value), probe=None))
        for line, h in t5.items():
            sites.append(dict(rule="T5", key=(FAMILY["T5"], line), cell=cell_no, t5=h, probe=None))
        self.history.append(code)
        return [s for s in sites if s["key"] not in self.shown]

    def _k5i_site(self, node, line, det):
        op = node.ops[0]
        L, R = node.left, node.comparators[0]
        col, bound = (L, R) if isinstance(op, (ast.LtE, ast.Gt)) else (R, L)
        sym = {ast.LtE: "<=", ast.Gt: ">", ast.GtE: ">=", ast.Lt: "<"}[type(op)]
        c, b = ast.unparse(col), ast.unparse(bound)
        probe = ("import json as _k5j\n"
                 "try:\n"
                 "    import pandas as _k5p\n"
                 f"    _k5s = _k5p.Series({c})\n"
                 "    if _k5s.dtype.kind in 'iufb':\n"
                 "        raise TypeError\n"
                 "    _k5c = _k5p.to_datetime(_k5s)\n"
                 f"    _k5b = _k5p.Timestamp({b})\n"
                 "    _k5t = (_k5c - _k5c.dt.normalize()).dropna()\n"
                 "    print('K5I', _k5j.dumps({'intraday': bool((_k5t != _k5p.Timedelta(0)).any()),"
                 " 'midnight': bool(_k5b == _k5b.normalize()), 'bound': str(_k5b)}))\n"
                 "except Exception:\n"
                 "    print('K5I null')")
        return dict(rule="K5i", key=(FAMILY["K5i"], line), line=line, lineno=node.lineno, col=c, bound=b, op=sym, probe=probe)

    def _k4x_probe(self, node):
        cur = None
        for side in (node.left, node.right):
            e = side.operand if isinstance(side, ast.UnaryOp) else side
            if rules.expr_key(e) in self.ctx["boolcmp"]:
                cur = e
        src = None
        for code in reversed(self.history):
            try:
                t = ast.parse(code)
            except SyntaxError:
                continue
            for n in ast.walk(t):
                if isinstance(n, ast.Assign) and len(n.targets) == 1 and rules.target_key(n.targets[0]) == rules.expr_key(cur) \
                        and isinstance(n.value, ast.Compare):
                    src = n.value
            if src is not None:
                break
        if src is None:
            return None
        a, b = ast.unparse(src.left), ast.unparse(src.comparators[0])
        return ("import json as _k4j\n"
                "try:\n"
                f"    _k4a, _k4b = {a}, {b}\n"
                "    _k4i = (_k4a.notna() & _k4b.notna()).idxmax()\n"
                "    if _k4i == _k4a.index[0]:\n"
                "        raise ValueError\n"
                f"    print('K4X', _k4j.dumps({{'first_true': bool(({ast.unparse(node)}).loc[_k4i]), 'at': str(_k4i)}}))\n"
                "except Exception:\n"
                "    print('K4X null')")

    def note(self, site: dict, probe_output: str = "") -> str | None:
        r, msg = site["rule"], None
        if r == "K1":
            res = addconst_result(probe_output)
            msg = addconst_note(site["site"], site["cell"], res) if res else None
        elif r == "K3L":
            h = site.get("t5")
            recv = site["det"].get("recv", "")
            mcol = re.search(r"\[['\"](\w+)['\"]\]", recv)
            col = (h or {}).get("col") or (mcol.group(1) if mcol else "col")
            frame = re.match(r"\w+", recv).group(0) if re.match(r"\w+", recv) else "frame"
            slice_expr = h["slice_line"] if h else site["det"].get("recv", "")
            source = h["src"] if h else "<full series>"
            msg = (f"Line {site['lineno']}: `{site['line']}` lags `{col}` after `{frame}` was cut to a window with "
                   f"`{slice_expr}`. The first row of the window becomes NaN instead of using the value just before the "
                   f"window, so the first pair in each window is lost. Lag on the full series first, then cut the window: "
                   f"`lagged = {source}['{col}'].shift(1); window = lagged.iloc[start:end + 1]`." + SUFFIX)
        elif r == "T5":
            msg = slice_lag_note(site["t5"])
        elif r == "K5i":
            m = re.search(r"K5I (\{.*\})", probe_output or "")
            v = json.loads(m.group(1)) if m else None
            if v and v["intraday"] and v["midnight"]:
                b = site["bound"]
                fix = f"{site['col']} < {b} + pd.Timedelta(days=1)" if site["op"] == "<=" else f"{site['col']} >= {b} + pd.Timedelta(days=1)"
                msg = (f"Line {site['lineno']}: `{site['line']}` compares `{site['col']}`, which holds intraday times, with "
                       f"`{b}`, a date-only Timestamp at midnight ({v['bound']}). `{site['op']} {b}` cuts the last day at "
                       f"00:00, so every later row on that day is {'dropped' if site['op'] == '<=' else 'kept'}. Make the end "
                       f"bound cover the whole day: `{fix}`." + SUFFIX)
        elif r == "K4x":
            m = re.search(r"K4X (\{.*\})", probe_output or "")
            v = json.loads(m.group(1)) if m else None
            if v and v["first_true"]:
                msg = (f"Line {site['lineno']}: `{site['line']}` detects a crossover from a stored comparison and its "
                       f"shifted copy. The comparison is False during warm-up, where its inputs are NaN, so the first day "
                       f"both inputs exist ({v['at']}) is counted as a crossover. Compare the shifted series themselves "
                       f"so warm-up rows stay False: `(fast.shift(1) <= slow.shift(1)) & (fast > slow)`." + SUFFIX)
        elif r == "K2c":
            msg = (f"Line {site['lineno']}: `{site['line']}` reads `{site['recv']}.get({site['k']}, {site['default']})` "
                   f"inside a sum or discounting step. If `{site['k']}` is missing, {site['default']} enters the calculation "
                   f"silently and every later value built on it changes. Index directly so a missing point raises, and "
                   f"fill it from the curve first if needed: `{site['recv']}[{site['k']}]`." + SUFFIX)
        if msg:
            self.shown.add(site["key"])
        return msg

    def output_notes(self, output_dir: str, statement: str) -> list[str]:
        if not self.enabled["K6"]:
            return midnight_date_notes(output_dir, statement)
        out = []
        pat = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]00:00:00$")
        if re.search(r"HH:MM|%H|hh:mm|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}", statement or "", re.I):
            return out
        for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):
            try:
                data = json.load(open(fp))
            except Exception:
                continue
            paths = []

            def walk(o, p):
                if isinstance(o, dict):
                    for k, v in o.items():
                        walk(v, p + [str(k)])
                elif isinstance(o, list):
                    for i, v in enumerate(o[:5000]):
                        walk(v, p + [f"[{i}]"])
                elif isinstance(o, str) and pat.match(o):
                    paths.append(".".join(p))
            walk(data, [])
            if paths:
                out.append(f"`{os.path.relpath(fp, output_dir)}` contains date strings with a ` 00:00:00` time part at "
                           f"`{', '.join(paths[:4])}`. They come from `str(Timestamp)`, `json.dump(..., default=str)` or "
                           f"`.isoformat()`, so a date field no longer reads as a plain date. Write dates explicitly: "
                           f"`pd.Timestamp(x).strftime('%Y-%m-%d')`." + SUFFIX)
        return out
