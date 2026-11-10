import os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "oc9"))
from oc9_checks import _S1_UNION, _S1_TOPN, _TRUE, _FALSE, _out_files, _csv_rows

_SCEN = re.compile(r"^(scenario|scenarios|scenario_name|scenario_id|scen|case|stress_case|stress_scenario|regime|shock)$", re.I)


def set_flag_notes(output_dir: str, statement: str) -> list[str]:
    if not statement or not _S1_UNION.search(statement):
        return []
    ns = {int(x) for x in _S1_TOPN.findall(statement)}
    if len(ns) != 1:
        return []
    n = ns.pop()
    out = []
    for fp in _out_files(output_dir, ".csv"):
        try:
            hdr, rows = _csv_rows(fp)
        except Exception:
            continue
        flags = [i for i, h in enumerate(hdr) if h.lower().startswith("in_")]
        if len(flags) < 2 or len(rows) <= n:
            continue
        scen = next((i for i, h in enumerate(hdr) if _SCEN.match(h.strip())), None)
        groups = {}
        for r in rows:
            groups.setdefault(r[scen] if scen is not None and scen < len(r) else None, []).append(r)
        for i in flags:
            vals = [r[i].strip().lower() if i < len(r) else "" for r in rows]
            if not all(v in _TRUE | _FALSE for v in vals):
                continue
            worst = max(((g, sum((r[i].strip().lower() if i < len(r) else "") in _TRUE for r in grp), len(grp))
                         for g, grp in groups.items()), key=lambda x: x[1])
            g, k, size = worst
            if k > n:
                rel = os.path.relpath(fp, output_dir)
                where = f" within scenario `{g}`" if scen is not None else ""
                out.append(f"Output check: {rel}: `{hdr[i]}` is true on {k} of {size} rows{where}, but the task builds this "
                           f"table from top-{n} lists, so membership of one list can be true on at most {n} rows"
                           f"{' per scenario' if scen is not None else ''}. The flag should mark membership of that list's "
                           f"top-{n} (the list used to build the union), not every holding of the source.")
    return out[:2]
