import glob, json, os, re


DUPCOL_PROBE = ("import json as _t4j\n"
                "_t4o = []\n"
                "try:\n"
                "    import pandas as _t4p\n"
                "    for _t4k, _t4v in list(globals().items()):\n"
                "        if not _t4k.startswith('_') and isinstance(_t4v, _t4p.DataFrame) and _t4v.columns.duplicated().any():\n"
                "            _t4d = sorted({str(c) for c in _t4v.columns[_t4v.columns.duplicated()]})\n"
                "            _t4o.append({'name': _t4k, 'dups': _t4d, 'count': {d: int(sum(str(c) == d for c in _t4v.columns)) for d in _t4d},\n"
                "                         'columns': [str(c) for c in _t4v.columns][:30]})\n"
                "except Exception:\n"
                "    pass\n"
                "print('DUPCOLS', _t4j.dumps(_t4o))")


def dupcol_entries(probe_output: str) -> list[dict]:
    m = re.search(r"DUPCOLS (\[.*\])", probe_output or "")
    try:
        return json.loads(m.group(1)) if m else []
    except ValueError:
        return []


def dupcol_note(entry: dict) -> str:
    name, col = entry["name"], entry["dups"][0]
    n = entry["count"][col]
    pos = [str(i + 1) for i, c in enumerate(entry["columns"]) if c == col]
    return (f"Session check: DataFrame `{name}` has {n} columns named `{col}` (positions {', '.join(pos)} of "
            f"{len(entry['columns'])}); "
            f"`{name}['{col}']` returns a DataFrame of all {n} copies and `row['{col}']` returns {n} values, not one number, so "
            f"comparisons and arithmetic on it fail or broadcast. Keep one column per name: rename before combining so "
            f"only one source becomes `{col}`, or, once you know the first copy holds the values you want, "
            f"`{name} = {name}.loc[:, ~{name}.columns.duplicated()]`.")



_T5_SLICE = re.compile(r"^[ \t]*(?P<v>[A-Za-z_]\w*)\s*=\s*(?P<src>[A-Za-z_][\w.\[\]'\"]*?)\.(?P<how>iloc|loc)\["
                       r"\s*(?P<lo>[^\]\n:]+?)\s*:\s*(?P<hi>[^\]\n,]*?)\s*(?:,[^\]\n]*)?\](?:\.copy\(\))?\s*$", re.M)


def slice_lag_hits(code: str) -> list[dict]:
    hits = []
    for m in _T5_SLICE.finditer(code):
        v, lo = m.group("v"), m.group("lo").strip()
        if lo in ("0", "None") or re.fullmatch(r"['\"].*['\"]", lo) or m.group("src") == v:
            continue
        rest = re.sub(r"#[^\n]*", "", code[m.end():])
        nxt = re.search(r"^[ \t]*%s\s*=" % re.escape(v), rest, re.M)
        scope = rest[:nxt.start()] if nxt else rest
        sh = re.search(r"^[^\n]*\b%s(?:\[['\"](?P<col>\w+)['\"]\])?\s*\.shift\(\s*(?P<k>\d*)\s*\)[^\n]*$" % re.escape(v), scope, re.M)
        if sh and (sh.group("k") or "1") != "0":
            hits.append({"var": v, "slice_line": m.group(0).strip(), "shift_line": sh.group(0).strip(),
                         "src": m.group("src"), "how": m.group("how"), "lo": lo, "hi": m.group("hi").strip(),
                         "col": sh.group("col"), "k": sh.group("k") or "1"})
    return hits


def slice_lag_note(h: dict) -> str:
    col = f"['{h['col']}']" if h["col"] else ""
    return (f"Code note: in this cell `{h['var']}` is a row slice (`{h['slice_line']}`) and its lag is taken inside the "
            f"slice (`{h['shift_line']}`), so the first row of the slice gets NaN instead of the value just before "
            f"`{h['lo']}`, and dropping NaN removes that row. If the lag of the first row should come from the row before "
            f"the slice, lag the full series first and slice afterwards, for example: "
            f"`lagged = {h['src']}{col}.shift({h['k']}).{h['how']}[{h['lo']}:{h['hi']}]`.")



def _all_null(v):
    if v is None:
        return True
    if isinstance(v, dict):
        return bool(v) and all(_all_null(x) for x in v.values())
    return False


def _walk(obj, path, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append((path, k, v, obj))
            _walk(v, path + [str(k)], out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:5000]):
            _walk(v, path + [f"[{i}]"], out)


def null_key_notes(output_dir: str, min_count: int = 4) -> list[str]:
    out = []
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):
        try:
            data = json.load(open(fp))
        except Exception:
            continue
        entries = []
        _walk(data, [], entries)
        by = {}
        for path, k, v, parent in entries:
            by.setdefault(k, []).append((path, v, parent))
        for k, lst in by.items():
            if len(lst) < min_count or not all(_all_null(v) for _, v, _ in lst):
                continue
            if not any(not _all_null(pv) for _, _, parent in lst for pk, pv in parent.items() if pk != k):
                continue
            sib = next(pk for _, _, parent in lst for pk, pv in parent.items() if pk != k and not _all_null(pv))
            where = ".".join(lst[0][0] + [str(k)])
            out.append(f"Output check: in {os.path.relpath(fp, output_dir)} every `{k}` entry ({len(lst)} of {len(lst)}, "
                       f"e.g. {where}) is null, while `{sib}` next to it has values. A value that is missing everywhere "
                       f"usually means the writing loop looks it up under keys the computed results do not use. Print "
                       f"the keys the loop looks up next to the first keys of the dict that holds the `{k}` results, fix "
                       f"the lookup, and rewrite the file.")
            if len(out) >= 2:
                return out
    return out



_T6_VAL = re.compile(r"^\d{4}-\d{2}-\d{2} 00:00:00$")
_T6_TIME_ASKED = re.compile(r"HH:MM|%H|hh:mm|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}", re.I)


def midnight_date_notes(output_dir: str, statement: str) -> list[str]:
    if _T6_TIME_ASKED.search(statement or ""):
        return []
    out = []
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):
        try:
            data = json.load(open(fp))
        except Exception:
            continue
        entries = []
        _walk(data, [], entries)
        hits = [(".".join(p + [str(k)]), v) for p, k, v, _ in entries if isinstance(v, str) and _T6_VAL.match(v)]
        if hits:
            keys = ", ".join(f"`{p}` = '{v}'" for p, v in hits[:3])
            out.append(f"Output check: {os.path.relpath(fp, output_dir)} writes {keys}{' and more' if len(hits) > 3 else ''}: "
                       f"the str() of a midnight Timestamp. Use the plain 'YYYY-MM-DD' form, for example "
                       f"`pd.Timestamp(x).strftime('%Y-%m-%d')`, unless the task asks for a time of day.")
    return out
