import ast, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "oc10"))
from mapping_note import topup_sites, topup_probe, _example


def _transition_loop(session_code: list, key_expr_v: str):
    head = re.match(r"[\w.]+", key_expr_v)
    if not head:
        return None
    mapper = head.group(0)
    for code in reversed(session_code):
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        for loop in ast.walk(tree):
            if not (isinstance(loop, ast.For) and isinstance(loop.iter, ast.Call) and isinstance(loop.iter.func, ast.Attribute)
                    and loop.iter.func.attr == "iterrows" and isinstance(loop.target, ast.Tuple)):
                continue
            row = loop.target.elts[-1].id if isinstance(loop.target.elts[-1], ast.Name) else None
            src = ast.get_source_segment(code, loop) or ""
            if not row or mapper not in src or ".columns" not in src:
                continue
            m = re.search(r"\b%s\[\s*((['\"]).+?\2)\s*\]" % re.escape(row), src)
            if m:
                return ast.get_source_segment(code, loop.iter.func.value), m.group(1)
    return None


def a102_note(site: dict, cell_no, skipped: list, session_code: list) -> str | None:
    ex = _example(site)
    if not ex or not skipped:
        return None
    key_rhs, cell_t, skips = ex
    s = skipped[0]
    m = re.search(r",\s*([^\]]+)\]\s*$", site["visible"])
    dcol = m.group(1).strip() if m else None
    tl = _transition_loop(session_code, key_rhs)
    if dcol is None or tl is None:
        return None
    tm, bop = tl
    key0, row, fr, col, ncol, diff = site["key0"], site["row"], site["frame"], site["col"], site["n_col"], site["diff"]
    of_c = re.sub(r"\bv\b", "c", key_rhs)
    first_idx = re.match(r"[\w.]+\[\s*(.+?)\s*,", cell_t)
    idx_tc = re.sub(r"\bt\b", "tc", first_idx.group(1)) if first_idx else "tc"
    cell_k = re.sub(r"\bt\b", key0, cell_t)
    key_line = re.sub(r"\bv\b", f"{row}[{col!r}]", key_rhs)
    sources = ", ".join(s["sources"])
    target = str(s["target"]) if str(s["target"]).lstrip("-").isdigit() else repr(s["target"])
    lines = [f"Mapping check on cell {cell_no}: the loop that adds hidden defaults compares each rating's true defaults "
             f"with `{site['visible']}`. After mapping, that is the merged count of every rating sharing target "
             f"`{s['target']}` ({sources}): after your cell it holds {s['visible']:g}, while their true defaults add up to "
             f"{s['sum']:g}. \"Each BOP rating\" is met by comparing each rating with its own visible defaults counted before "
             f"mapping. In your next cell change only that loop inside the year loop, rerun the year loop, and leave the "
             f"rest of your code as it is:",
             f"    vis_raw = {{r[{bop}]: sum(float(r[c]) for c in {tm}.columns if (tc := {of_c}) is not None and {idx_tc} == {dcol} and pd.notna(r[c])) "
             f"for _, r in {tm}.iterrows()}}",
             f"    for _, {row} in {fr}.iterrows():",
             f"        {key0} = {key_line}",
             f"        if {key0} is None: continue"]
    tword = re.compile(r"\bt\b")
    lines += [f"        if {tword.sub(key0, t)}: continue" for t in skips if t.strip() != "t is None"]
    lines += [f"        {diff} = float({row}[{ncol!r}]) - vis_raw.get({row}[{col!r}], 0.0)",
              f"        if {diff} > 0: {cell_k} += {diff}",
              f"Then print {tword.sub(target, cell_t)} "
              f"for one year next to {sources}'s true defaults and rewrite the files built from these counts."]
    return "\n".join(lines)
