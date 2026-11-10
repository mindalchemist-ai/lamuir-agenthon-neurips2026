import calendar, datetime as dt, glob, json, math, os, re, sys
import pandas as pd

TENOR_RE = re.compile(r"^(\d+)([MY])$")


def read_out(out_dir):
    csvs, jsons = {}, {}
    for p in sorted(glob.glob(os.path.join(out_dir, "*"))):
        b = os.path.basename(p)
        try:
            if b.endswith(".csv"):
                csvs[b] = pd.read_csv(p)
            elif b.endswith(".json"):
                jsons[b] = json.load(open(p))
        except Exception:
            pass
    return csvs, jsons


def read_inputs(data_dir):
    js, csvs = {}, {}
    for p in sorted(glob.glob(os.path.join(data_dir, "**", "*"), recursive=True)):
        b = os.path.basename(p)
        try:
            if b.endswith(".json") and os.path.getsize(p) < 2_000_000:
                js[b] = json.load(open(p))
            elif b.endswith(".csv") and os.path.getsize(p) < 20_000_000:
                csvs[b] = p
        except Exception:
            pass
    return js, csvs


def walk(v, path=""):
    if isinstance(v, dict):
        yield path, v
        for k, x in v.items():
            yield from walk(x, f"{path}/{k}")
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from walk(x, f"{path}[{i}]")


def leaves(v):
    if isinstance(v, dict):
        for x in v.values():
            yield from leaves(x)
    elif isinstance(v, list):
        for x in v:
            yield from leaves(x)
    elif isinstance(v, (int, float)) and not isinstance(v, bool):
        yield float(v)


def pdate(s):
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    y += d.year
    return dt.date(y, m + 1, min(d.day, calendar.monthrange(y, m + 1)[1]))


def k12(csvs, inp_csvs):
    out = []
    for f, df in csvs.items():
        if not all(c in df.columns for c in ("pair", "trade_date", "spot_locked")):
            continue
        hist = None
        for p in inp_csvs.values():
            try:
                h = pd.read_csv(p)
            except Exception:
                continue
            if "date" in h.columns and any(str(x) in h.columns for x in df["pair"].unique()):
                hist = h.assign(date=pd.to_datetime(h["date"], errors="coerce")).set_index("date").sort_index()
                break
        if hist is None or len(df) == 0:
            continue
        miss = 0
        for _, r in df.iterrows():
            pr, td, v = str(r["pair"]), pd.to_datetime(r["trade_date"], errors="coerce"), pd.to_numeric(r["spot_locked"], errors="coerce")
            if pr not in hist.columns or pd.isna(td) or pd.isna(v):
                continue
            i = hist.index.searchsorted(td)
            win = hist[pr].iloc[max(0, i - 5): i + 6]
            if not ((win - v).abs() < 1e-9 * max(1, abs(v))).any():
                miss += 1
        if miss:
            out.append(f"{f}: {miss} rows whose spot_locked is not the input spot of that pair near trade_date")
    return out


