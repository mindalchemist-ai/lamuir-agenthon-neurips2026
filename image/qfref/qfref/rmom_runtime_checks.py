import glob, json, math, os, re, sys
import pandas as pd

CAL_RE = re.compile(r"(?:after|following|beyond)\s+(?:the\s+)?(?:first\s+)?(\d+)(?:st|nd|rd|th)?\s+calendar\s+(month|day|week|quarter|year)s?", re.I)
FREQ = {"month": "M", "day": "D", "week": "W", "quarter": "Q", "year": "Y"}
DATE_COL_RE = re.compile(r"(^|_)(date|month|period|dt)($|_)", re.I)


def input_grid(data_dir, unit):
    vals = set()
    for p in sorted(glob.glob(os.path.join(data_dir, "**", "*"), recursive=True)):
        try:
            if p.endswith((".pqt", ".parquet")):
                df = pd.read_parquet(p)
            elif p.endswith(".csv"):
                df = pd.read_csv(p, nrows=2_000_000)
            else:
                continue
        except Exception:
            continue
        for c in df.columns:
            if not DATE_COL_RE.search(str(c)):
                continue
            s = pd.to_datetime(df[c], errors="coerce").dropna()
            if len(s):
                vals.update(s.dt.to_period(FREQ[unit]).unique())
    return sorted(vals)


def output_date_frames(out_dir):
    for p in sorted(glob.glob(os.path.join(out_dir, "*.csv"))):
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        cols = [c for c in df.columns if DATE_COL_RE.search(str(c))]
        if not cols:
            continue
        d = pd.to_datetime(df[cols[0]], errors="coerce")
        if d.notna().any():
            yield os.path.basename(p), df.assign(_d=d)


def check_calendar_offset(instruction, data_dir, out_dir):
    m = CAL_RE.search(instruction)
    if not m:
        return []
    n, unit = int(m.group(1)), m.group(2).lower()
    grid = input_grid(data_dir, unit)
    if len(grid) <= n:
        return []
    pos = {g: i for i, g in enumerate(grid)}
    frames = list(output_date_frames(out_dir))
    present = set()
    for _, df in frames:
        present.update(df["_d"].dropna().dt.to_period(FREQ[unit]).unique())
    notes = []
    for name, df in frames:
        first = df["_d"].min().to_period(FREQ[unit])
        p = pos.get(first)
        if p is None or p == 0:
            continue
        if p < n:
            continue
        expected = next((g for g in grid[n:] if g in present), None)
        if expected is not None and first != expected:
            notes.append(
                f"{name}: earliest row is {first} = position {p} (0-based) of the {len(grid)} distinct calendar {unit}s in the input data. "
                f"A start rule counted in calendar {unit}s with n = {n} uses that full grid (index {n} = {grid[n]}), "
                f"not the list of periods that survived your filters. Recheck which date list you skip the first {n} entries of."
            )
    return notes


def json_leaves(obj, path=""):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        if isinstance(obj, float) and math.isfinite(obj) and obj != 0:
            yield path, float(obj)
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from json_leaves(v, f"{path}.{k}" if path else str(k))


def column_means(out_dir):
    means = []
    for p in sorted(glob.glob(os.path.join(out_dir, "*.csv"))):
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if len(df) > 500_000:
            continue
        num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and df[c].notna().sum() > 1]
        cats = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c]) and 1 < df[c].nunique() <= 20]
        for c in num:
            means.append((os.path.basename(p), c, "all", df[c].mean()))
            for g in cats:
                for val, sub in df.groupby(g)[c]:
                    if sub.notna().sum() > 1:
                        means.append((os.path.basename(p), c, f"{g}={val}", sub.mean()))
    return means


def close(a, b, rel=1e-9):
    return abs(a - b) <= rel * max(abs(a), abs(b))


def check_key_column_alignment(out_dir):
    means = column_means(out_dir)
    if not means:
        return []
    cols = {c for _, c, _, _ in means}
    notes = []
    for p in sorted(glob.glob(os.path.join(out_dir, "*.json"))):
        try:
            leaves = list(json_leaves(json.load(open(p))))
        except Exception:
            continue
        for key, v in leaves:
            named = [c for c in cols if len(str(c)) >= 4 and str(key).endswith(str(c))]
            if not named:
                continue
            named_c = max(named, key=lambda c: len(str(c)))
            if any(c == named_c and close(v, mu) for _, c, _, mu in means):
                continue
            files = {f for f, c, _, _ in means if c == named_c}
            other = [(f, c, g) for f, c, g, mu in means if f in files and c != named_c and not str(named_c).endswith(str(c)) and close(v, mu)]
            if other:
                f, c, g = other[0]
                notes.append(f"{os.path.basename(p)}: '{key}' equals the mean of column '{c}' ({g}) in {f}, not of column '{named_c}'. Check the order in which coefficients are mapped to names.")
    return notes


def grader_status(task_dir):
    g = os.path.join(task_dir, "grader_output.txt")
    if not os.path.exists(g):
        return "none"
    lines = [l for l in open(g, errors="replace").read().strip().splitlines() if l.strip()]
    last = lines[-1] if lines else ""
    if "failed" in last or "error" in last:
        return "fail"
    return "pass" if "passed" in last else "other"


if __name__ == "__main__":
    raw, units, pattern = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "t1-*")
    instr_cache, grid_dirs = {}, {}
    stats = {}
    hits = []
    for out_dir in sorted(glob.glob(os.path.join(raw, "*", pattern, "output"))):
        td = os.path.dirname(out_dir)
        task = os.path.basename(td)
        ip = os.path.join(units, task, "instruction.md")
        if not os.path.exists(ip):
            continue
        if task not in instr_cache:
            instr_cache[task] = open(ip).read()
        st = grader_status(td)
        a = check_calendar_offset(instr_cache[task], os.path.join(units, task, "environment", "data"), out_dir)
        b = check_key_column_alignment(out_dir)
        for kind, f in (("A", a), ("B", b)):
            key = (kind, st, bool(f))
            stats[key] = stats.get(key, 0) + 1
            if f:
                hits.append((kind, st, os.path.relpath(td, raw), f[0][:260]))
    for k in sorted(stats):
        print("check=%s status=%s flagged=%s runs=%d" % (k[0], k[1], k[2], stats[k]))
    for h in hits:
        print(*h, sep=" | ")
