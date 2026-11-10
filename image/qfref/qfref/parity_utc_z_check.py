import csv, glob, json, os, re

Z_ASKED = re.compile(r"[Tt]railing\s+`?Z`?(?![\w-])|\d{2}:\d{2}(?::\d{2})?Z\b|HH:MM(?::SS)?Z\b")
FILE_HEAD = re.compile(r"^#{1,6}\s.*?([A-Za-z0-9_\-]+\.(?:csv|json))\b")
IDENT = re.compile(r"`([A-Za-z_][A-Za-z0-9_]*)`")
TS_ANY = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2}Z?)?$")
TS_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z$")
MAX_ROWS = 5000


def bad_ts(v) -> bool:
    return isinstance(v, str) and bool(TS_ANY.match(v.strip())) and not TS_Z.match(v.strip())


def _csv_hits(fp):
    hits = {}
    try:
        with open(fp, newline="") as f:
            for i, row in enumerate(csv.DictReader(f)):
                if i >= MAX_ROWS:
                    break
                for k, v in row.items():
                    if k is not None and bad_ts(v) and k not in hits:
                        hits[k] = v
    except Exception:
        return {}
    return hits


def _json_hits(fp):
    hits = {}
    try:
        data = json.load(open(fp))
    except Exception:
        return {}

    def walk(o, p):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, p + [str(k)])
        elif isinstance(o, list):
            for i, v in enumerate(o[:MAX_ROWS]):
                walk(v, p + [f"[{i}]"])
        elif bad_ts(o):
            hits.setdefault(".".join(p), o)
        if isinstance(o, dict):
            for k in o:
                if bad_ts(k):
                    hits.setdefault(".".join(p) + " (key)", k)
    walk(data, [])
    return hits


def z_scope(statement: str):
    files, fields = set(), set()
    cur_file = None
    items, buf = [], []
    for line in (statement or "").splitlines():
        m = FILE_HEAD.match(line)
        if line.lstrip().startswith("#"):
            items.append((cur_file, "\n".join(buf)))
            buf = []
            cur_file = m.group(1) if m else None
            continue
        if not line.strip() or line.lstrip().startswith("- "):
            items.append((cur_file, "\n".join(buf)))
            buf = []
        buf.append(line)
    items.append((cur_file, "\n".join(buf)))
    for f, text in items:
        if not Z_ASKED.search(text):
            continue
        named = {n for n in IDENT.findall(text) if n != "Z"}
        if named:
            fields |= named
        elif f:
            files.add(f)
    return files, fields


def utc_z_findings(output_dir: str, statement: str) -> dict:
    files, fields = z_scope(statement)
    if not files and not fields:
        return {}
    out = {}
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*"), recursive=True)):
        if fp.endswith(".csv"):
            h = _csv_hits(fp)
        elif fp.endswith(".json"):
            h = _json_hits(fp)
        else:
            continue
        if os.path.basename(fp) not in files:
            h = {k: v for k, v in h.items() if k.split(".")[-1].replace(" (key)", "") in fields}
        if h:
            out[os.path.relpath(fp, output_dir)] = h
    return out


def utc_z_notes(output_dir: str, statement: str) -> list[str]:
    notes = []
    for rel, h in utc_z_findings(output_dir, statement).items():
        where = ", ".join(f"`{k}` = '{v}'" for k, v in list(h.items())[:3])
        notes.append(f"Output check: {rel} writes {where}, but the task asks for UTC timestamps that end in `Z`. "
                     f"A timezone-aware datetime written by `to_csv`, `str()` or `.isoformat()` comes out as "
                     f"'YYYY-MM-DD HH:MM:SS+00:00'. Convert the column to text just before writing, for example "
                     f"`df.assign(col=df['col'].dt.strftime('%Y-%m-%dT%H:%M:%SZ'))`, or write the original input strings.")
    return notes
