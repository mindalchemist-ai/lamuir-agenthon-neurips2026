import ast, glob, json, os, re


def _src(code, node):
    return ast.get_source_segment(code, node) or ""


def _uses(node, name):
    return any(isinstance(n, ast.Name) and n.id == name for n in ast.walk(node))


def theta_sites(code: str) -> list[dict]:
    sites = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return sites
    for loop in ast.walk(tree):
        if not (isinstance(loop, ast.For) and isinstance(loop.target, ast.Name) and isinstance(loop.iter, (ast.List, ast.Tuple))):
            continue
        names = [e.value for e in loop.iter.elts if isinstance(e, ast.Constant)]
        if "theta" not in names:
            continue
        g = loop.target.id
        for n in ast.walk(loop):
            if isinstance(n, ast.Call) and len(n.args) >= 2 and _uses(n.args[0], g) and _uses(n.args[1], g) \
                    and isinstance(n.func, (ast.Name, ast.Attribute)):
                fd, bs = _src(code, n.args[0]), _src(code, n.args[1])
                if not re.search(r"fd|finite|mc|est", fd, re.I) or not re.search(r"bs|black|analytic|closed|ref", bs, re.I):
                    continue
                line = next((l.strip() for l in code.splitlines() if _src(code, n) in l), _src(code, n))
                sites.append({"var": g, "call": _src(code, n), "fd": fd, "bs": bs, "line": line})
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and len(n.args) >= 2 and isinstance(n.func, (ast.Name, ast.Attribute)):
            fd, bs = _src(code, n.args[0]), _src(code, n.args[1])
            if all(re.search(r"\[\s*['\"]theta['\"]\s*\]", x) for x in (fd, bs)) and re.search(r"fd|finite|mc|est", fd, re.I) \
                    and re.search(r"bs|black|analytic|closed|ref", bs, re.I):
                line = next((l.strip() for l in code.splitlines() if _src(code, n) in l), _src(code, n))
                sites.append({"var": "_th_unused", "call": _src(code, n), "fd": fd, "bs": bs, "line": line})
    return list({s["call"]: s for s in sites}.values())


def theta_probe(site: dict) -> str:
    v = site["var"]
    return ("import json as _thj\n"
            "try:\n"
            f"    _thn = {{{v!r}: 'theta'}}\n"
            f"    _tha = float(eval({site['fd']!r}, globals(), _thn)); _thb = float(eval({site['bs']!r}, globals(), _thn))\n"
            f"    _thc = eval({site['call']!r}, globals(), _thn)\n"
            "    print('THETA', _thj.dumps({'fd': _tha, 'bs': _thb, 'check': bool(_thc)}))\n"
            "except Exception:\n"
            "    print('THETA null')")


def theta_result(probe_output: str):
    m = re.search(r"THETA (\{.*\}|null)", probe_output or "")
    try:
        r = json.loads(m.group(1)) if m else None
    except ValueError:
        return None
    if not r:
        return None
    a, b = r["fd"], r["bs"]
    if a * b < 0 and abs(a + b) < 0.05 * abs(a - b) and r["check"] is False:
        return r
    return None


def _bs_base(bs_expr: str, var: str, session_code: list):
    m = re.fullmatch(r"([A-Za-z_]\w*)\[\s*(['\"])(\w+)\2\s*\]\[\s*(?:%s|['\"]theta['\"])\s*\]" % re.escape(var), bs_expr.strip())
    if m:
        base = m.group(1)
    else:
        m2 = re.fullmatch(r"([A-Za-z_]\w*)\[\s*%s\s*\]" % re.escape(var), bs_expr.strip())
        if not m2:
            return None, []
        alias = m2.group(1)
        found = None
        for code in reversed(session_code):
            a = re.findall(r"^\s*%s\s*=\s*([A-Za-z_]\w*)\[\s*['\"](\w+)['\"]\s*\]" % re.escape(alias), code, re.M)
            if a:
                found = a[-1][0]
                break
        if not found:
            return alias, None
        base = found
    sides = []
    for code in session_code:
        sides += re.findall(r"\b%s\[\s*['\"](\w+)['\"]\s*\]" % re.escape(base), code)
    return base, list(dict.fromkeys(sides))


def _flag_name(site: dict, code: str):
    m = re.search(r"^\s*([A-Za-z_]\w*)\s*=\s*False\b", code, re.M)
    if m:
        return m.group(1)
    m = re.match(r"\s*[A-Za-z_]\w*\[\s*['\"](\w+)['\"]\s*\]\s*=", site["line"]) or re.match(r"\s*([A-Za-z_]\w*)\s*=", site["line"])
    return m.group(1) if m else None


def theta_note(site: dict, r: dict, code: str, session_code: list, output_dir: str) -> str:
    base, sides = _bs_base(site["bs"], site["var"], session_code)
    pos, neg = (site["fd"], site["bs"]) if r["fd"] > 0 else (site["bs"], site["fd"])
    fd_sign = "dV/dT" if r["fd"] > 0 else "dV/dt"
    bs_sign = "dV/dt" if r["fd"] > 0 else "dV/dT"
    if base and sides:
        copy = f"    bs_cmp = {{side: dict({base}[side], theta=-{base}[side]['theta']) for side in {tuple(sides)!r}}}"
    elif base:
        copy = f"    bs_cmp = dict({base}, theta=-{base}['theta'])"
    else:
        copy = "    # reverse the Black-Scholes theta sign in the values the check compares"
    flag = _flag_name(site, code)
    fdb = re.match(r"[A-Za-z_]\w*", site["fd"])
    errs = None
    if fdb and base:
        for c in reversed(session_code):
            m = re.search(r"^\s*([A-Za-z_]\w*)\[[^\]\n]+\]\s*=\s*[^\n]*\b%s\b[^\n]*-[^\n]*\b%s\b" % (re.escape(fdb.group(0)), re.escape(base)), c, re.M)
            if m:
                errs = m.group(1)
                break
    files = []
    for fp in sorted(glob.glob(os.path.join(output_dir, "*.json"))):
        try:
            text = open(fp, errors="ignore").read()
        except OSError:
            continue
        if any(x and x in text for x in (flag, errs)):
            files.append(os.path.basename(fp))
    what = (f"`{errs}`, " if errs else "") + f"`{site['line']}`" + (f" and the `{flag}` flag" if flag else "")
    files_part = f", print them, and rewrite {' and '.join(files)}." if files else ", print them, and rewrite the files that hold the result."
    return (f"In your next cell change only the Black-Scholes values used in the comparison; leave greeks.json as it is. "
            f"Your FD theta is {fd_sign} ({r['fd']:+.4g}) and the Black-Scholes theta is {bs_sign} ({r['bs']:+.4g}), so "
            f"reverse the Black-Scholes theta sign before comparing:\n{copy}\n"
            f"Recompute {what} with bs_cmp{files_part}")


SIGN_FAMILY_KEY = ("sign-convention", "theta")
