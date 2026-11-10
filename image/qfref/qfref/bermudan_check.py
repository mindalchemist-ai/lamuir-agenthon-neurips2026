import ast, json, re

_EX_PARAM = re.compile(r"^(n_ex|ex_steps|exercise_steps|exercise_idx|exercise_dates)$", re.I)
_EX_ARG = re.compile(r"(^|_)(ex|exer|exercise)(_|$|s$|\w*idx|\w*steps)", re.I)
_PAY_ARG = re.compile(r"(^|_)(pay|payment|payments|coupon|coupons)(_|$|s$)", re.I)


def _src(code, node):
    return ast.get_source_segment(code, node) or ""


def _callee(call):
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")


def _ex_functions(session_code: str) -> set:
    out = set()
    for code in session_code if isinstance(session_code, list) else [session_code]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef) and any(_EX_PARAM.match(a.arg) for a in n.args.args):
                out.add(n.name)
    return out


def bermudan_sites(code: str, session_code: list) -> list[dict]:
    sites = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return sites
    exf = _ex_functions(session_code + [code])
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        name = _callee(n)
        if "bermudan" not in name.lower() and name not in exf:
            continue
        args = [a.id for a in n.args if isinstance(a, ast.Name)] + [k.value.id for k in n.keywords if isinstance(k.value, ast.Name)]
        e = next((a for a in args if _EX_ARG.search(a)), None)
        p = next((a for a in args if _PAY_ARG.search(a) and a != e), None)
        if e and p:
            line = next((l.strip() for l in code.splitlines() if _src(code, n) in l), _src(code, n))
            sites.append({"call": _src(code, n), "call_line": line, "E": e, "P": p})
    return sites


def bermudan_probe(site: dict) -> str:
    return ("import json as _bmj\n"
            "try:\n"
            "    import numpy as _bmn\n"
            f"    _bme = _bmn.asarray({site['E']}).ravel(); _bmp = _bmn.asarray({site['P']}).ravel()\n"
            "    _bmok = _bme.dtype.kind in 'iu' or (_bme.dtype.kind == 'f' and _bmn.all(_bme == _bmn.round(_bme)))\n"
            "    _bmok = _bmok and (_bmp.dtype.kind in 'iu' or (_bmp.dtype.kind == 'f' and _bmn.all(_bmp == _bmn.round(_bmp))))\n"
            "    _bmd = _bmn.diff(_bmp)\n"
            "    if _bmok and len(_bme) >= 2 and len(_bmp) >= 2 and _bmn.all(_bmd > 0) and _bmn.all(_bmd == _bmd[0]):\n"
            "        print('BERM', _bmj.dumps({'E': [int(x) for x in _bme[:5]], 'P': [int(x) for x in _bmp[:5]], 'lenE': int(len(_bme)),"
            " 'lenP': int(len(_bmp)), 'eStep': sorted({int(x) for x in _bmn.diff(_bme)})[:3], 'p': int(_bmd[0])}))\n"
            "    else:\n"
            "        print('BERM null')\n"
            "except Exception:\n"
            "    print('BERM null')")


def bermudan_result(probe_output: str):
    m = re.search(r"BERM (\{.*\}|null)", probe_output or "")
    try:
        r = json.loads(m.group(1)) if m else None
    except ValueError:
        return None
    if r and r["P"][0] > r["E"][0] and (r["eStep"] != [r["p"]] or r["lenE"] > r["lenP"]):
        return r
    return None


def bermudan_note(site: dict, cell_no, r: dict, session_code: list) -> str:
    e, p = site["E"], site["P"]
    assign = None
    for code in reversed(session_code):
        found = re.findall(r"^[ \t]*%s\s*=(?!=)[^\n]*" % re.escape(e), code, re.M)
        if found:
            assign = found[-1].strip()
            break
    start = None
    if assign:
        m = re.search(r"range\(\s*([A-Za-z_]\w*)\s*,", assign) or re.search(r"\[\s*([A-Za-z_]\w*)\s*\]", assign)
        start = m.group(1) if m else None
    step = r["eStep"][0] if len(r["eStep"]) == 1 else "/".join(map(str, r["eStep"]))
    return (f"Code check: in your cell {cell_no}, `{site['call_line']}` passes exercise steps `{e}` = "
            f"{', '.join(map(str, r['E']))} ... ({r['lenE']} steps, spaced {step}) with payment steps `{p}` = "
            f"{', '.join(map(str, r['P']))} ... (spaced {r['p']}). A Bermudan exercise schedule normally lies on the expiry "
            f"and on the payment dates before the last, so its steps are spaced like the payment steps. Where `{e}` is "
            f"assigned (`{assign or '<assignment not found>'}`), the usual form is:\n"
            f"    {e} = [{start or '<expiry step>'}] + list({p}[:-1])\n"
            f"In your next cell do only this: replace that assignment and rerun the call (the functions and the tree are "
            f"already in your session; do not rebuild them), print len({e}) and its first steps, and rewrite the file that "
            f"holds these prices. If the task defines a different exercise schedule, quote that sentence and keep yours.")
