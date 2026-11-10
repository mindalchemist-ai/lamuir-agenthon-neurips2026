import csv, glob, json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "oc9"))
from oc9_checks import _input_names

_NAME = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*(?:(?:<[A-Za-z_]+>|\{[A-Za-z_]+\})[A-Za-z0-9_]*)*)`")
_PH = re.compile(r"<[A-Za-z_]+>|\{[A-Za-z_]+\}")


def _pattern(name):
    parts = _PH.split(name)
    return "^" + "[A-Za-z0-9_.\\-]+".join(re.escape(p) for p in parts) + "$"


def _keys(output_dir):
    out = {}
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):
        try:
            data = json.load(open(fp))
        except Exception:
            continue
        stack = [data]
        while stack:
            o = stack.pop()
            if isinstance(o, dict):
                for k, v in o.items():
                    out.setdefault(str(k), os.path.relpath(fp, output_dir))
                    stack.append(v)
            elif isinstance(o, list):
                stack.extend(o[:2000])
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True)):
        try:
            with open(fp, newline="", errors="ignore") as f:
                hdr = next(csv.reader(f), [])
        except Exception:
            continue
        for h in hdr:
            out.setdefault(h, os.path.relpath(fp, output_dir))
    return out


def key_case_notes(output_dir: str, statement: str, data_dirs: list[str] = ()) -> list[str]:
    keys = _keys(output_dir)
    inputs = {x.lower() for x in _input_names(list(data_dirs))} if data_dirs else set()
    names = [n for n in dict.fromkeys(_NAME.findall(statement or "")) if n.lower() not in inputs]
    exact = [re.compile(_pattern(n)) for n in names]
    out = []
    for n, rx in zip(names, exact):
        if len(re.sub(_PH, "", n)) < 4 or any(rx.match(k) for k in keys):
            continue
        rxi = re.compile(_pattern(n), re.I)
        near = [k for k in keys if rxi.match(k) and not any(e.match(k) for e in exact)]
        if not near:
            continue
        lit = _PH.split(n)[0]
        got = near[0][:len(lit)] if lit and near[0].lower().startswith(lit.lower()) else None
        fix = (f"`{{(k.replace('{got}', '{lit}', 1) if k.startswith('{got}') else k): v for k, v in d.items()}}`"
               if got and got != lit else f"rename `{near[0]}` to the task's spelling")
        out.append(f"Output check: the task names `{n}`, and {keys[near[0]]} writes {len(near)} key(s) that match it only when "
                   f"letter case is ignored, for example `{near[0]}`. Keys are matched exactly, so write the task's spelling, "
                   f"for example {fix}, and rewrite the file.")
        if len(out) >= 3:
            break
    return out
