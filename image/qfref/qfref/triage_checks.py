import glob, importlib.util, json, os, re

TRIAGE = os.environ.get("OC11_TRIAGE_DIR", "/Users/Agenthon/fca-mini-swe/mini-swe/analysis/v212-90pct/research_1026/oc11_triage")
ENABLED = {"pair_order": True}


def _load(folder, module, flat=None):
    for path in (os.path.join(TRIAGE, folder, module + ".py"), os.path.join(TRIAGE, (flat or module) + ".py")):
        if os.path.isfile(path):
            try:
                spec = importlib.util.spec_from_file_location(f"triage_{flat or module}", path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod
            except Exception:
                return None
    return None
    return None



_pair = _load("copula-equity-fitting", "pair_order_check")


def pair_order_notes(output_dir: str, statement: str) -> list[dict]:
    if not ENABLED["pair_order"] or _pair is None:
        return []
    problems = _pair.check(statement, output_dir)
    if not problems:
        return []
    first = problems[0]
    fname, rest = first.split(": pair ", 1)
    ab, names = rest.split(" is in the reverse of the task list order ", 1)
    msg = (f"Submit check: the output has pair labels whose members are in the reverse of the order the task text lists them "
           f"(first: {fname}: {ab}; list {names}). Unless the task asks for sorted or alphabetical order, rebuild the pairs "
           f"with itertools.combinations over the written list and rewrite the files.")
    return [{"rule": "pair_order", "key": ("pair-order", fname), "note": msg, "count": len(problems)}]



_lstsq = _load("fama-french-factor-model-new", "lstsq_ssr_lint")
ENABLED["lstsq_ssr"] = False


def lstsq_ssr_notes(code: str) -> list[dict]:
    if not ENABLED["lstsq_ssr"] or _lstsq is None:
        return []
    out = []
    for h in _lstsq.hits(code):
        line = code.splitlines()[h["use_line"] - 1] if h["use_line"] <= len(code.splitlines()) else ""
        if re.search(r"\b(print|type|isinstance|len)\([^\n]*\b%s\b" % re.escape(h["name"]), line):
            continue
        msg = (f"Check on this cell (line {h['use_line']}): `{h['name']}` holds the second output of `np.linalg.lstsq` from "
               f"line {h['lstsq_line']}. That output is already the residual sum of squares (shape (1,) for a 1-D target), not "
               f"the residual vector, so `{h['use']}` does not compute what it would compute on residuals. Rebuild the "
               f"residuals as `v - A @ coef` and recompute every quantity that used `{h['name']}`. If your setup satisfies a "
               f"condition this check cannot see, say which and keep it.")
        out.append({"rule": "lstsq_ssr", "key": ("lstsq-ssr", h["name"], h["use"]), "note": msg, "name": h["name"],
                    "probe": lstsq_ssr_probe(h["name"])})
    return out


def lstsq_ssr_probe(name: str) -> str:
    return ("try:\n"
            "    import numpy as _lsn\n"
            f"    print('LSTSQ', 'true' if _lsn.asarray(globals()[{name!r}]).size <= 1 else 'false')\n"
            "except Exception:\n"
            "    print('LSTSQ null')")


def lstsq_ssr_confirmed(probe_output: str) -> bool:
    return "LSTSQ true" in (probe_output or "")



_fwd = _load("cir-bond-pricing", "v3_forward_check")
ENABLED["forward_sign"] = True


def forward_sign_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["forward_sign"] or _fwd is None:
        return []
    return [{"rule": "forward_sign", "key": ("forward-sign", n.split("`")[1] if "`" in n else n[:60]), "note": n}
            for n in _fwd.forward_sign_notes(output_dir)]



_CAP_CLIP = re.compile(r"(?:\bmin\(|np\.minimum\(|\.clip\()[^\n]*\b\w*(?:max_pos|position_pct|pos_cap|position_cap|max_weight)\w*")
_PER_NAME = re.compile(r"\b\w*(?:weight_per_stock|per_stock_weight|weight_per_name|w_long|long_weight)\w*\b")
ENABLED["weight_cap"] = True


def weight_cap_notes(code: str) -> list[dict]:
    if not ENABLED["weight_cap"]:
        return []
    m = _CAP_CLIP.search(code)
    if not m or not _PER_NAME.search(code):
        return []
    line = next((l.strip() for l in code.splitlines() if m.group(0) in l), m.group(0)).strip()
    msg = (f"Code note: this cell shrinks a stated per-name weight to a position limit (`{line}`). If the task's steps name "
           f"the per-name weight to use and the limit only appears among the parameters, keep the stated weight and print the "
           f"conflict; clip only when the steps say to cap or clip positions. Uniform shrinking leaves Sharpe unchanged but "
           f"scales returns, volatility, drawdown, alpha and betas.")
    return [{"rule": "weight_cap", "key": ("weight-cap", line), "note": msg}]



_bin = _load("binance-btc-participation-tca", "check_V3", flat="binance_check_V3")
ENABLED["balance_lag"] = True
ENABLED["reference_time"] = True


def balance_reference_notes(output_dir: str, statement: str = "") -> list[dict]:
    if _bin is None:
        return []
    out = []
    for name in sorted(os.listdir(output_dir)) if os.path.isdir(output_dir) else []:
        path = os.path.join(output_dir, name)
        if name.endswith(".csv") and ENABLED["balance_lag"]:
            for p in _bin.balance_lag_problems(path):
                b, f = re.findall(r"`([^`]+)`", p)[:2]
                fix = (f" If the column should report the balance after each row's own fill: "
                       f"`df[{b!r}] = df[{b!r}] - df[{f!r}]`, then rewrite {name}.")
                out.append({"rule": "balance_lag", "key": ("balance-lag", name), "note": "Output check: " + p + fix})
        elif name.endswith(".json") and ENABLED["reference_time"]:
            out += [{"rule": "reference_time", "key": ("reference-time", p.split("`")[1]), "note": "Output check: " + p}
                    for p in _bin.reference_time_problems(path)]
    return out



_sub = _load("crypto-funding-rate-basis-carry", "subfit_count_check")
ENABLED["subfit_count"] = True


def subfit_count_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["subfit_count"] or _sub is None:
        return []
    out = []
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):
        try:
            data = json.load(open(fp))
        except Exception:
            continue
        for p in _sub.issues(data):
            out.append({"rule": "subfit_count", "key": ("subfit-count", os.path.basename(fp), p.split(":")[0]),
                        "note": f"Output check: {os.path.basename(fp)} {p}"})
    return out



_ph = _load("crypto-funding-rate-basis-carry", "placeholder_check")
ENABLED["placeholder_zeros"] = True


def placeholder_zero_notes(output_dir: str, session_code: list) -> list[dict]:
    if not ENABLED["placeholder_zeros"] or _ph is None:
        return []
    out = []
    for p in _ph.issues(output_dir, list(session_code)):
        name = p.split(":")[0]
        out.append({"rule": "placeholder_zeros", "key": ("placeholder-zeros", name),
                    "note": f"Output check: {p}. A block of zeros written earlier as a stand-in is still in the file: rewrite it "
                            f"now with the computed values, and update every other file that repeats the same quantities."})
    return out



_KAPPA_MAP = re.compile(r"(κ|kappa) *= *[−-] *(β|beta) */ *(Δt|dt)", re.I)
_KAPPA_LOG = re.compile(r"^[ \t]*(\w*kappa\w*)\s*=[^\n]*\blog\(", re.I | re.M)
_HEAT = re.compile(r"\bHDD\b|heating degree", re.I)
_COOL = re.compile(r"\bCDD\b|cooling degree", re.I)
_TDELTA = r"temp\w*delta|delta\w*temp"
ENABLED["kappa_log"] = False
ENABLED["degree_day_sign"] = True


def kappa_log_notes(code: str, statement: str) -> list[dict]:
    if not ENABLED["kappa_log"] or not _KAPPA_MAP.search(statement or ""):
        return []
    m = _KAPPA_LOG.search(code)
    if not m:
        return []
    msg = (f"Note: the task text states kappa = -beta/dt (beta = slope of the change on the level) and sigma = residual sd / "
           f"sqrt(dt). This cell computes kappa with a logarithm (`{m.group(0).strip()}`). Report the stated map; an exact "
           f"transition used for simulation does not change the calibration map. Recompute kappa and sigma and everything that "
           f"uses them.")
    return [{"rule": "kappa_log", "key": ("kappa-log",), "note": msg}]


def degree_day_probe(statement: str) -> str | None:
    if not ENABLED["degree_day_sign"]:
        return None
    sign = ">" if _HEAT.search(statement or "") else "<" if _COOL.search(statement or "") else None
    if sign is None:
        return None
    return ("import json as _ddj, re as _ddr\n"
            "_ddo = []\n"
            "for _ddk, _ddv in list(globals().items()):\n"
            f"    if not _ddk.startswith('_') and _ddr.search({_TDELTA!r}, _ddk, _ddr.I) and isinstance(_ddv, float) and _ddv {sign} 0:\n"
            "        _ddo.append([_ddk, _ddv])\n"
            "print('DDSIGN', _ddj.dumps(_ddo))")


def degree_day_notes(probe_output: str, statement: str) -> list[dict]:
    m = re.search(r"DDSIGN (\[.*\])", probe_output or "")
    hits = json.loads(m.group(1)) if m else []
    if not hits:
        return []
    name, value = hits[0]
    kind = "heating" if _HEAT.search(statement or "") else "cooling"
    bound = "at most zero" if kind == "heating" else "at least zero"
    msg = (f"Check: a {kind}-degree-day call {'loses' if kind == 'heating' else 'gains'} value when temperatures rise, so its "
           f"sensitivity to a temperature bump is {bound}; `{name}` = {value:.6g}. Check whether the bump moved the temperature or "
           f"the degree-days.")
    return [{"rule": "degree_day_sign", "key": ("degree-day-sign",), "note": msg}]



_ARRAY_CELL = re.compile(r"^\[\s*-?\d[\d.eE+-]*\s*\]$")
ENABLED["array_cell"] = True


def array_cell_notes(output_dir: str, files: list = None) -> list[dict]:
    if not ENABLED["array_cell"]:
        return []
    import csv as _csv
    paths = [os.path.join(output_dir, f) for f in files] if files else sorted(glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True))
    out = []
    for fp in paths:
        if not fp.endswith(".csv") or not os.path.isfile(fp):
            continue
        try:
            with open(fp, newline="", errors="ignore") as f:
                rows = list(_csv.reader(f))[:5001]
        except Exception:
            continue
        if len(rows) < 2:
            continue
        hdr = rows[0]
        for j, col in enumerate(hdr):
            vals = [r[j].strip() for r in rows[1:] if j < len(r) and r[j].strip()]
            hits = [v for v in vals if _ARRAY_CELL.match(v)]
            if hits:
                name = os.path.basename(fp)
                msg = (f"Output check: {name} column `{col}` holds one-element arrays instead of numbers ({len(hits)} of "
                       f"{len(vals)} cells, e.g. {hits[0]}). A value taken as a[i:i+1] is an array of length 1; stored in a "
                       f"DataFrame it makes an object column that .round() and select_dtypes(number) skip, and the CSV writes "
                       f"the brackets. Store a number instead: float(x) or x.item(), or index a[i] rather than a[i:i+1]. "
                       f"Rewrite {name} and rerun every later step that reads it.")
                out.append({"rule": "array_cell", "key": ("array-cell", name, col), "note": msg})
    return out



_side = _load("fx-forward-cross-rate", "side_checks", flat="fx_side_checks")
ENABLED["direction_sign"] = True


def direction_sign_notes(code: str) -> list[dict]:
    if not ENABLED["direction_sign"] or _side is None:
        return []
    out = []
    for h in _side.side_sign_hits_v2(code):
        s = h["sign"][0] if h.get("sign") else "sign"
        msg = (_side.side_note_v2(h) + f" A sign slip passes a sum check: the attribution components still add up to the "
               f"total, so only the sell records show it. For example: `{h['unsigned'][0].split('=', 1)[0].strip()} = {s} * "
               f"({h['unsigned'][0].split('=', 1)[1].strip()})`.")
        out.append({"rule": "direction_sign", "key": ("direction-sign", h["unsigned"][0]), "note": msg})
    return out



ENABLED["id_subset"] = True


def _input_ids(data_dirs):
    import pandas as pd
    sets = {}
    for d in data_dirs:
        for f in glob.glob(os.path.join(d, "**", "*.csv"), recursive=True):
            try:
                df = pd.read_csv(f, nrows=5000)
            except Exception:
                continue
            for c in df.columns:
                if re.search(r"(?i)(^|_)id$|_id$", str(c)) and not pd.api.types.is_numeric_dtype(df[c]):
                    v = df[c].dropna().astype(str)
                    if len(v) >= 2 and v.is_unique:
                        sets[f"{os.path.basename(f)}:{c}"] = set(v)
    return sets


def id_subset_notes(output_dir: str, data_dirs: list) -> list[dict]:
    if not ENABLED["id_subset"] or _side is None:
        return []
    ids = _input_ids(data_dirs)
    if not ids:
        return []
    out = []
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):
        try:
            obj = json.load(open(fp))
        except Exception:
            continue
        maps = list(_side._id_maps(obj))
        for src, s in ids.items():
            for path, keys in maps:
                if keys and keys < s:
                    miss = sorted(s - keys)
                    name = os.path.basename(fp)
                    msg = (f"Output check: {name} {path or '<root>'} has {len(keys)} of the {len(s)} IDs in {src}; missing "
                           f"{', '.join(miss[:8])}{' ...' if len(miss) > 8 else ''}. A loop that stopped part-way (for "
                           f"example on a KeyError) and was not rerun leaves exactly this. Rerun the loop over every ID and "
                           f"rewrite {name}; if some IDs are excluded on purpose, say which rule excludes them.")
                    out.append({"rule": "id_subset", "key": ("id-subset", name, path), "note": msg})
                    break
    return out[:2]



_ranks = _load("etf-cross-asset-lead-lag", "check_twin_ranks")
ENABLED["rank_equal"] = True


def rank_equal_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["rank_equal"] or _ranks is None:
        return []
    out = []
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):
        try:
            data = json.load(open(fp))
        except Exception:
            continue
        name = os.path.basename(fp)
        for path, ka, kb in _ranks.walk(data):
            rows = data
            for part in re.findall(r"\.([^.\[]+)|\[(\d+)\]", path):
                rows = rows[part[0]] if part[0] else rows[int(part[1])]
            preview = ", ".join(f"{r[ka]}/{r[kb]}" for r in rows[:3])
            msg = (f"Output check: in {name}, the list `{path.lstrip('.')}` has {len(rows)} rows whose `{ka}` and `{kb}` are "
                   f"equal on every row ({preview} ...). Two rankings taken from different tables rarely agree row for row; "
                   f"this usually means both were read from the same index labels instead of each table's sorted position. "
                   f"For each row, look up the item's position in the table that rank refers to (rank r = row r-1 after "
                   f"sorting that table), and rewrite the file. With iterrows on a sorted table, reset the labels first, for "
                   f"example `df = df.sort_values(...).reset_index(drop=True)`, or count positions with "
                   f"`for pos, (_, row) in enumerate(df.iterrows(), start=1)`.")
            out.append({"rule": "rank_equal", "key": ("rank-equal", name, path, ka, kb), "note": msg})
    return out[:2]



_exb = _load("hull-white-swaption", "exercise_check", flat="hw_exercise_check")
ENABLED["exercise_boundary"] = True


def exercise_boundary_notes(code: str, cell_no=None) -> list[dict]:
    if not ENABLED["exercise_boundary"] or _exb is None:
        return []
    hits = _exb.check(code)
    if not hits:
        return []
    return [{"rule": "exercise_boundary", "key": ("exercise-boundary",) + tuple(sorted(str(h) for h in hits))[:3],
             "note": _exb.note(hits, cell_no)}]



_ewma = _load("intraday-volume-fitting-and-execution-scheduling", "check_ewma_parity", flat="iv_check_ewma_parity")
_bins = _load("intraday-volume-fitting-and-execution-scheduling", "check_empty_bins", flat="iv_check_empty_bins")
ENABLED["ewma_parity"] = True
ENABLED["empty_bars"] = True

EWMA_NOTE = ("Weight-order check on cell {N}: `{EXPR}` combines exponential lag weights with a window whose rows run oldest to "
             "newest, and the reversals applied to the lags, the weights and the window add up to an even number (none, or two "
             "that cancel). The largest weight therefore sits on the oldest row. With lag 0 = most recent, reverse exactly one "
             "side and confirm before using the profile:\n\n```python\nlags = np.arange(len(window))[::-1]          # window "
             "rows oldest -> newest, newest gets lag 0\nw = np.exp(-np.log(2) * lags / half_life)\nassert w.argmax() == "
             "len(window) - 1         # largest weight on the newest row\n```\n\nRecompute every result that used these weights, "
             "including any choice made from them, and write the affected files again.")
BARS_NOTE = ("Bar check on cell {N}: `{NAME}` comes from an intraday resample that sums volume and takes first or last prices, and "
             "nothing after it removes empty bars. Resampling creates every interval between the first and last timestamp, so "
             "nights, weekends, holidays and early-close afternoons appear as bars with NaN prices and zero volume. Dropping rows "
             "with NaN volume does not remove them, because the sum of an empty bar is 0. Keep only bars that contain at least one "
             "trade before counting bars per session:\n\n```python\n{NAME} = {NAME}[{NAME}[\"{PRICE}\"].notna()]     # bars with at "
             "least one observation\nper_day = {NAME}.groupby({NAME}.index.date).size()\nprint(per_day.value_counts().head())          "
             "# full and short sessions should now differ\n```\n\nThen recount the bars per session and rewrite every file built "
             "from those counts.")


class EwmaParity:

    def __init__(self):
        self.a = _ewma.Analyzer() if (_ewma is not None and ENABLED["ewma_parity"]) else None
        self.seen = 0

    def cell(self, code: str, cell_no) -> list[dict]:
        if self.a is None:
            return []
        self.a.cell(code, cell_no)
        new, self.seen = self.a.hits[self.seen:], len(self.a.hits)
        return [{"rule": "ewma_parity", "key": ("ewma-parity", expr), "note": EWMA_NOTE.format(N=where, EXPR=expr)}
                for where, expr in new]


def empty_bars_notes(code: str, cell_no) -> list[dict]:
    if not ENABLED["empty_bars"] or _bins is None:
        return []
    out = []
    for _, name in _bins.resample_hits(code):
        m = re.search(r"['\"](\w+)['\"]\s*:\s*['\"](?:first|last)['\"]", code)
        price = m.group(1) if m else "Open"
        out.append({"rule": "empty_bars", "key": ("empty-bars", name), "note": BARS_NOTE.format(N=cell_no, NAME=name, PRICE=price)})
    return out



_mcg = _load("mc-greek-surface-1", "runtime_checks", flat="mcg_runtime_checks")
_mcg_txt = _load("mc-greek-surface-1", "drafts", flat="mcg_drafts")
ENABLED["scale_ratio"] = True
ENABLED["sign_double"] = True
ENABLED["method_gap"] = True


def _json_outputs(output_dir):
    out = {}
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True)):
        try:
            out[os.path.relpath(fp, output_dir)] = json.load(open(fp))
        except Exception:
            continue
    return out


def _any_all_false(jsons):
    return any(_mcg.summary_false(o) for o in jsons.values())


def scale_ratio_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["scale_ratio"] or _mcg is None or _mcg_txt is None:
        return []
    out = []
    for f, obj in _json_outputs(output_dir).items():
        for path, k1, k2, a, b, ratio in _mcg.c1_unit_factor(obj):
            out.append({"rule": "scale_ratio", "key": ("scale-ratio", f, path),
                        "note": _mcg_txt.C1["V1"].format(file=f, path=path, k1=k1, a=a, k2=k2, b=b, ratio=ratio)})
    return out[:2]


def sign_double_notes(output_dir: str, statement: str = "", shown: set = frozenset()) -> list[dict]:
    if not ENABLED["sign_double"] or _mcg is None or _mcg_txt is None:
        return []
    jsons = _json_outputs(output_dir)
    if not _any_all_false(jsons):
        return []
    out = []
    for ef, eobj in jsons.items():
        for gf, gobj in jsons.items():
            if gf == ef:
                continue
            for err_path, e, est_path, v in _mcg.c3_error_sign(eobj, gobj):
                key = ("sign-convention", ef)
                if key in shown or any(k[0] == "sign-convention" for k in shown):
                    continue
                out.append({"rule": "sign_double", "key": key,
                            "note": _mcg_txt.C3["V3"].format(err_file=ef, est_file=gf, err_path=err_path, e=e, est_path=est_path, v=v)})
                return out
    return out


def method_gap_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["method_gap"] or _mcg is None or _mcg_txt is None:
        return []
    if not _any_all_false(_json_outputs(output_dir)):
        return []
    out = []
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True)):
        hits = _mcg.c2b_same_size_methods(fp)
        if not hits:
            continue
        rows = list(__import__("csv").DictReader(open(fp)))
        sc = next(c for c in rows[0] if c.lower() in ("n", "n_paths", "paths", "num_paths"))
        n = max(float(r[sc]) for r in rows)
        vary, la, a, lb, b, band = hits[0]
        f = os.path.relpath(fp, output_dir)
        out.append({"rule": "method_gap", "key": ("method-gap", f),
                    "note": _mcg_txt.C2B["V1"].format(csv_file=f, n=f"{n:g}", label=f"{vary}={la}", a=a, b_label=f"{vary}={lb}",
                                                     b=b, diff=abs(a - b), band=band)})
    return out



ENABLED["calendar_offset"] = True
_rmom = _load("residual-momentum", "runtime_checks", flat="rmom_runtime_checks")
_RMOM_GRID: dict = {}
CAL_NOTE = ("Output check: {file}: the earliest row is {first}, position {p} (0-based) of the {n_grid} distinct calendar "
            "{unit}s in the input data. A start rule counted in calendar {unit}s with n = {n} counts every period on that "
            "full grid, including periods with no estimate (too few observations, missing regressors), so it starts at "
            "index {n} = {grid_n}, not after the first {n} entries of the list of estimated periods. For example:\n"
            "cal = np.sort(df[date_col].unique())  # all distinct periods, before any filter\n"
            "first = cal[{n}]\n"
            "fc_dates = [d for d in est_dates if d >= first]\n"
            "Rebuild the rows from fc_dates and rewrite {file}.")
def calendar_offset_notes(output_dir: str, statement: str = "", data_dirs=None) -> list[dict]:
    if not ENABLED["calendar_offset"] or _rmom is None:
        return []
    m = _rmom.CAL_RE.search(statement or "")
    if not m:
        return []
    n, unit = int(m.group(1)), m.group(2).lower()
    freq = _rmom.FREQ[unit]
    out = []
    for d in data_dirs or ("/input/environment/data", "/app/data"):
        if not os.path.isdir(d):
            continue
        if (d, unit) not in _RMOM_GRID:
            _RMOM_GRID[(d, unit)] = _rmom.input_grid(d, unit)
        grid = _RMOM_GRID[(d, unit)]
        if len(grid) <= n:
            continue
        pos = {g: i for i, g in enumerate(grid)}
        frames = list(_rmom.output_date_frames(output_dir))
        present = set()
        for _, df in frames:
            present.update(df["_d"].dropna().dt.to_period(freq).unique())
        for name, df in frames:
            first = df["_d"].min().to_period(freq)
            p = pos.get(first)
            if p is None or p < n:
                continue
            expected = next((g for g in grid[n:] if g in present), None)
            if expected is not None and first != expected:
                out.append({"rule": "calendar_offset", "key": ("calendar-offset", name),
                            "note": CAL_NOTE.format(file=name, first=first, p=p, n_grid=len(grid), unit=unit, n=n, grid_n=grid[n])})
        break
    return out


def _num(v):
    import math
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)



ENABLED["fx_identities"] = True
_fxr = _load("fx-carry-forward-hedge", "runtime_checks", flat="fx_runtime_checks")
_FX_GATES = {
    "tenor_date": (r"\btenors?\b|\b\d+[MY]\b", r"delivery|value date|settlement"),
    "cip": (r"\bforwards?\b", r"\bspot\b", r"deposit|interest rate|money[- ]market"),
    "bid_offer": (r"\bbid\b", r"\boffer\b|\bask\b"),
    "implied_copy": (r"\bimplied\b",),
    "strike_side": (r"\bdelta\b", r"\bstrikes?\b"),
    "overlay": (r"\boverlay\b", r"\bhedg"),
    "locked_spot": (r"\block", r"\bspot\b"),
    "fwd_direction": (r"\bdomestic\b", r"\bforeign\b", r"\bforwards?\b"),
}
_FX_NOTES = {
    "tenor_date": "Output check: {file} {where}: the delivery date {d} is not the spot date {s} plus {tenor} (calendar months "
                  "from spot, the day kept or set to the month's last day, then rolled to the next business day). Rebuild it "
                  "with calendar.monthrange for the month end.",
    "cip": "Output check: {file} {where}: the forward {fwd:.10g} is not spot x (1 + r_terms x t_terms) / (1 + r_base x t_base) "
           "built from the same record's spot, rates and year fractions ({cip:.10g}).",
    "bid_offer": "Output check: {file} {where}: `{bid}` = {b:.10g} is above `{offer}` = {o:.10g}; a bid is never above its offer. "
                 "Check which side of each input quote feeds each leg.",
    "implied_copy": "Output check: {file} {where}: `{key}` = {v:.10g} is exactly a number from the input files; an implied "
                    "quantity comes from solving the stated relation, not from copying an input.",
    "strike_side": "Output check: {file} {where}: a {n}-delta {cp} has strike {k:.6g} against forward {f:.6g}; out-of-the-money "
                   "delta quotes put a call strike above the forward and a put strike below it. Solve delta(K) = target with "
                   "the bracket on that side and check delta at the solved strike.",
    "overlay": "Output check: {file}: `{hedged}` differs from `{unhedged}` + `{overlay}` on {n} row(s), or the overlay is 0 on "
               "every row; the hedged return is the unhedged return plus the hedge overlay of the same day.",
    "locked_spot": "Output check: {file}: {n} row(s) whose `{spot}` is not the input spot of that pair within 5 rows of `{date}`. "
                   "Take the locked spot from the input history on the trade date.",
    "fwd_direction": "Output check: {file} {where}: the forward {f:.6g} is on the wrong side of spot {s:.6g} for the input "
                     "domestic and foreign rates (the forward is above spot exactly when the domestic rate is higher).",
}


def _short(o, *must, avoid=()):
    hits = [(len(str(k)), k) for k, v in o.items() if all(w in str(k).lower() for w in must)
            and not any(w in str(k).lower() for w in avoid) and _num(v)]
    return min(hits)[1] if hits else None


def fx_identity_notes(output_dir: str, statement: str = "", data_dirs=None) -> list[dict]:
    if not ENABLED["fx_identities"] or _fxr is None:
        return []
    import math
    st = statement or ""
    on = {k for k, pats in _FX_GATES.items() if all(re.search(p, st, re.I) for p in pats)}
    if not on:
        return []
    csvs, jsons = _fxr.read_out(output_dir)
    d = next((x for x in (data_dirs or ("/input/environment/data", "/app/data")) if os.path.isdir(x)), None)
    inp_js, inp_csvs = _fxr.read_inputs(d) if d else ({}, {})
    out, seen = [], set()

    def add(rule, file, fkey, **kw):
        if (rule, file) not in seen:
            seen.add((rule, file))
            out.append({"rule": "fx_identities", "key": ("fx-" + rule, file, fkey), "note": _FX_NOTES[rule].format(file=file, **kw)})

    in_vals = {round(x, 12) for js in inp_js.values() for x in _fxr.leaves(js) if x != 0} if "implied_copy" in on else set()
    params = {}
    if "fwd_direction" in on:
        for js in inp_js.values():
            for _, o in _fxr.walk(js):
                idk = next((k for k, v in o.items() if re.search(r"(^|_)id$", str(k)) and isinstance(v, str)), None)
                dom, fo = _short(o, "domestic", "rate"), _short(o, "foreign", "rate")
                if idk and dom and fo:
                    params[o[idk]] = (o[dom], o[fo])
    for f, js in jsons.items():
        for path, o in _fxr.walk(js):
            if not isinstance(o, dict):
                continue
            where = path or "top level"
            tenor = path.rsplit("/", 1)[-1]
            if "tenor_date" in on and _fxr.TENOR_RE.match(tenor):
                sk = next((k for k in sorted(o, key=len) if "spot" in k.lower() and "date" in k.lower()), None)
                dk = next((k for k in sorted(o, key=len) if "date" in k.lower() and any(w in k.lower() for w in ("delivery", "value", "maturity", "settle"))), None)
                s, dd = (_fxr.pdate(o.get(sk)), _fxr.pdate(o.get(dk))) if sk and dk else (None, None)
                if s and dd:
                    m = _fxr.TENOR_RE.match(tenor)
                    lo = _fxr.add_months(s, int(m.group(1)) * (12 if m.group(2) == "Y" else 1))
                    if not (lo <= dd <= lo + __import__("datetime").timedelta(7)):
                        add("tenor_date", f, where, where=where, d=dd, s=s, tenor=tenor)
            if "cip" in on:
                fk = _short(o, "forward", "mid") or _short(o, "forward", avoid=("point", "pip", "basis", "diff", "error", "bid", "offer"))
                sk = _short(o, "spot", "mid") or _short(o, "spot", avoid=("bid", "offer", "date"))
                rb = _short(o, "base", "r", avoid=("t_", "bid", "offer"))
                rt = _short(o, "terms", "r", avoid=("t_", "bid", "offer"))
                tb = next((k for k in o if str(k).lower().startswith("t_") and "base" in str(k).lower() and _num(o[k])), None)
                tt = next((k for k in o if str(k).lower().startswith("t_") and "terms" in str(k).lower() and _num(o[k])), None)
                if all((fk, sk, rb, rt, tb, tt)) and o[fk]:
                    sc = lambda k: o[k] / 100 if str(k).lower().endswith("pct") else o[k]
                    F = o[sk] * (1 + sc(rt) * o[tt]) / (1 + sc(rb) * o[tb])
                    if abs(F / o[fk] - 1) > 1e-6:
                        add("cip", f, where, where=where, fwd=o[fk], cip=F)
            for k, v in o.items():
                lk = str(k).lower()
                if "bid_offer" in on and "bid" in lk and _num(v) and not any(w in lk or w in path.lower() for w in ("basis", "spread", "point", "pip", "swap", "return", "pnl", "diff", "error")):
                    for side in ("offer", "ask"):
                        ok = str(k).replace("bid", side).replace("Bid", side.capitalize())
                        if ok != k and _num(o.get(ok)) and v > o[ok] + 1e-12:
                            add("bid_offer", f, f"{where}/{k}", where=where, bid=k, offer=ok, b=v, o=o[ok])
                if "implied_copy" in on and lk.startswith("implied") and _num(v) and v != 0 and round(float(v), 12) in in_vals:
                    add("implied_copy", f, f"{where}/{k}", where=where, key=k, v=v)
            if "strike_side" in on:
                qt = next((str(v) for v in o.values() if isinstance(v, str) and re.fullmatch(r"\d+\s*d[_ -]?(call|put)", v.strip(), re.I)), None)
                kk = _short(o, "strike")
                fk = _short(o, "forward", avoid=("point", "pip", "rate")) or _short(o, "spot", avoid=("date",))
                if qt and kk and fk and o[fk] > 0:
                    m = re.match(r"(\d+)\s*d[_ -]?(call|put)", qt.strip(), re.I)
                    n, cp, K, F = int(m.group(1)), m.group(2).lower(), o[kk], o[fk]
                    if n < 50 and (not (0.5 * F < K < 2 * F) or (cp == "call" and K <= F) or (cp == "put" and K >= F)):
                        add("strike_side", f, where, where=where, n=n, cp=cp, k=K, f=F)
            if "fwd_direction" in on and params:
                pid = next((v for k, v in o.items() if re.search(r"(^|_)id$", str(k)) and isinstance(v, str) and v in params), None)
                fk, sk = _short(o, "forward", avoid=("point", "pip", "rate", "bid", "offer")), _short(o, "spot", avoid=("date", "bid", "offer"))
                if pid and fk and sk and (o[fk] - o[sk]) * (params[pid][0] - params[pid][1]) < 0:
                    add("fwd_direction", f, where, where=where, f=o[fk], s=o[sk])
    import pandas as pd
    for f, df in csvs.items():
        cols = [str(c) for c in df.columns]
        if "overlay" in on:
            un = next((c for c in sorted(cols, key=len) if "unhedged" in c.lower()), None)
            ov = next((c for c in sorted(cols, key=len) if "overlay" in c.lower()), None)
            he = next((c for c in sorted(cols, key=len) if "hedged" in c.lower() and "unhedged" not in c.lower() and "overlay" not in c.lower()
                       and "return" in c.lower()), None)
            if un and ov and he and len(df):
                x = df[[un, ov, he]].apply(pd.to_numeric, errors="coerce")
                gap = (x[he] - x[un] - x[ov]).abs() > 1e-9
                if gap.any() or (x[ov].fillna(0) == 0).all():
                    add("overlay", f, he, hedged=he, unhedged=un, overlay=ov, n=int(gap.sum()))
        if "locked_spot" in on and len(df):
            pc = next((c for c in cols if c.lower() in ("pair", "ccy_pair", "currency_pair")), None)
            dc = next((c for c in sorted(cols, key=len) if "trade" in c.lower() and "date" in c.lower()), None)
            sc_ = next((c for c in sorted(cols, key=len) if "spot" in c.lower() and any(w in c.lower() for w in ("lock", "fix"))), None)
            if pc and dc and sc_:
                ren = df.rename(columns={pc: "pair", dc: "trade_date", sc_: "spot_locked"})
                hits = _fxr.k12({f: ren}, inp_csvs)
                if hits:
                    add("locked_spot", f, sc_, n=int(re.search(r"(\d+) rows", hits[0]).group(1)), spot=sc_, date=dc)
    return out



ENABLED["xccy_identities"] = True
_xccy = _load("mtm-xccy-basis-desk/checks", "xccy_checks", flat="xccy_checks")
_XCCY_FIX = {
    "K1": "Use the tenor labels exactly as the input tables write them.",
    "K3": "A forward equal to spot on some positive tenors but not on others usually comes from a short-end interpolation that "
          "falls back to spot; check the forward at each of those rows.",
    "K5": "The stress P&L of a row is its stressed value minus the base value reported in the JSON output; recompute the column "
          "from those two.",
    "K6": "Take the year fraction from the row's own accrual start and end under the day count the task gives for that leg.",
    "K7": "A coupon amount is notional x year fraction x coupon rate on the same row; recompute it from those three columns.",
    "K8": "pv is the cash flow times its discount factor (times the FX rate when the row has one); recompute it on those rows.",
    "K9": "Every reset row is 0, so the resetting notional never changes; apply the notional reset at each reset date.",
}


def xccy_identity_notes(output_dir: str, statement: str = "", data_dirs=None) -> list[dict]:
    if not ENABLED["xccy_identities"] or _xccy is None:
        return []
    d = next((x for x in (data_dirs or ("/input/environment/data", "/app/data")) if os.path.isdir(x)), None)
    oc, oj = _xccy._csvs(output_dir), _xccy._jsons(output_dir)
    ic = _xccy._csvs(d) if d else []
    runs = {"K1": lambda: _xccy.k1_tenor_labels(oc, ic), "K3": lambda: _xccy.k3_forward_equals_spot(oc),
            "K5": lambda: _xccy.k5_stress_pnl(oc, oj), "K6": lambda: _xccy.k6_accrual_year_frac(oc),
            "K7": lambda: _xccy.k7_coupon_amount(oc), "K8": lambda: _xccy.k8_pv_product(oc), "K9": lambda: _xccy.k9_reset_rows_zero(oc)}
    out = []
    for k, f in runs.items():
        try:
            msgs = f()
        except Exception:
            continue
        for m in msgs:
            body = m.split(" ", 1)[1] if m.startswith(k + " ") else m
            out.append({"rule": "xccy_identities", "key": ("xccy-" + k, body.split(":")[0]),
                        "note": f"Output check: {body}. {_XCCY_FIX[k]}"})
    return out



ENABLED["scale_mismatch"] = True
_SCALE_POW = (-6, -3, -2, 2, 3, 6)
_SCALE_REL = 1e-9
_SCALE_TEXT = ("Output check: {file} `{field}` = {v:.10g}, and {other_file} `{other_field}` = {w:.10g}. These are the same "
               "number up to a factor of 10^{k} ({w:.10g} = {v:.10g} x 10^{k}){more}. Check whether both fields hold the "
               "same quantity. If they do, write them in one unit, the one the task text gives for each field, unless the "
               "task asks for the two units on purpose. If they are different quantities, an exact match like this usually "
               "means one was computed from, or set to, the other; recompute each from its own definition and print both.")


def _scale_leaves(obj, path=""):
    if isinstance(obj, bool):
        return
    if isinstance(obj, float):
        if obj == obj and abs(obj) != float("inf") and obj != 0:
            yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            yield from _scale_leaves(v, f"{path}.{k}" if path else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:2000]):
            yield from _scale_leaves(v, f"{path}[{i}]")


def _scale_csv(fp):
    import csv as _csv
    out = []
    try:
        with open(fp, newline="", errors="ignore") as f:
            rows = _csv.reader(f)
            hdr = next(rows, [])
            for i, row in enumerate(rows):
                for j, cell in enumerate(row):
                    try:
                        x = float(cell)
                    except ValueError:
                        continue
                    if x == x and abs(x) != float("inf") and x != 0 and ("." in cell or "e" in cell.lower()):
                        out.append((f"{hdr[j] if j < len(hdr) else j}[row {i}]", x))
                    if len(out) >= 20000:
                        return out
    except Exception:
        return out
    return out


def scale_mismatch_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["scale_mismatch"]:
        return []
    import bisect
    numbers = {}
    for fp in sorted(glob.glob(os.path.join(output_dir, "**", "*"), recursive=True)):
        if fp.endswith(".csv"):
            numbers[fp] = _scale_csv(fp)
        elif fp.endswith(".json"):
            try:
                numbers[fp] = list(_scale_leaves(json.load(open(fp))))
            except Exception:
                numbers[fp] = []
    out = []
    for fp, leaves in numbers.items():
        if not fp.endswith(".json") or not leaves:
            continue
        others = sorted((x, os.path.relpath(q, output_dir), f) for q, xs in numbers.items() if q != fp for f, x in xs)
        keys = [o[0] for o in others]
        if not keys:
            continue

        def near(x):
            i = bisect.bisect_left(keys, x - abs(x) * _SCALE_REL)
            return others[i] if i < len(keys) and abs(keys[i] - x) <= abs(x) * _SCALE_REL else None

        hits = []
        for field, v in leaves:
            if len(re.sub(r"[^0-9]", "", ("%.15g" % abs(v)).split("e")[0]).strip("0")) < 8:
                continue
            if abs(v - round(v, 4)) <= 1e-8 * max(1.0, abs(v)) or abs(v - float('%.4g' % v)) <= 1e-9 * abs(v) or near(v):
                continue
            for k in _SCALE_POW:
                if m := near(v * 10.0 ** k):
                    hits.append((field, v, k, m))
                    break
        if hits:
            field, v, k, (w, of, ofield) = hits[0]
            name = os.path.relpath(fp, output_dir)
            more = (f"; {len(hits) - 1} more field(s) of {name} differ the same way: "
                    + ", ".join(f"`{h[0]}`" for h in hits[1:4]) + (" ..." if len(hits) > 4 else "")) if len(hits) > 1 else ""
            out.append({"rule": "scale_mismatch", "key": ("scale-mismatch", name),
                        "note": _SCALE_TEXT.format(file=name, field=field, v=v, other_file=of, other_field=ofield, w=w, k=k,
                                                   more=more)})
    return out



ENABLED["kde_bandwidth"] = True
KDE_NOTE = ("Code check: cell {cell} line {line} `{src}` multiplies a gaussian_kde bandwidth factor (.factor) into a value "
            "taken from its .covariance. In scipy.stats.gaussian_kde, kde.covariance is already the kernel covariance, equal "
            "to kde.factor**2 times the ddof=1 data covariance, so the factor is applied twice and the kernels become far "
            "too narrow. For one-dimensional data the kernel standard deviation is\n"
            "h = np.sqrt(kde.covariance[0, 0])\n"
            "which equals kde.factor * np.std(x, ddof=1). Recompute h this way and rerun every result that used it.")


class KdeBandwidth:

    def __init__(self):
        self.taint, self.kde = {}, False

    def _tags(self, node):
        import ast
        t = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Attribute) and n.attr == "covariance":
                t.add("cov")
            elif isinstance(n, ast.Attribute) and n.attr in ("factor", "covariance_factor"):
                t.add("factor")
            elif isinstance(n, ast.Name):
                t |= self.taint.get(n.id, set())
        return t

    def cell(self, code: str, cell_no) -> list[dict]:
        import ast
        if not ENABLED["kde_bandwidth"]:
            return []
        self.kde = self.kde or "gaussian_kde" in code
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []
        events = []
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
                events.append((node.lineno, node.col_offset, 0, node))
            elif isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)) and node.value is not None:
                events.append((getattr(node, "end_lineno", node.lineno), 10 ** 6, 1, node))
        out, lines = [], code.splitlines()
        for _, _, kind, node in sorted(events, key=lambda e: e[:3]):
            if kind == 0:
                left, right = self._tags(node.left), self._tags(node.right)
                if self.kde and (("factor" in left and "cov" in right) or ("cov" in left and "factor" in right)):
                    src = lines[node.lineno - 1].strip() if node.lineno <= len(lines) else ""
                    out.append({"rule": "kde_bandwidth", "key": ("kde-bandwidth", src),
                                "note": KDE_NOTE.format(cell=cell_no, line=node.lineno, src=src)})
            else:
                tags = self._tags(node.value)
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for n in (x.id for tg in targets for x in ast.walk(tg) if isinstance(x, ast.Name)):
                    if tags:
                        self.taint[n] = set(tags) | (self.taint.get(n, set()) if isinstance(node, ast.AugAssign) else set())
                    elif not isinstance(node, ast.AugAssign):
                        self.taint.pop(n, None)
        return out



ENABLED["utc_z_suffix"] = True
_utcz = _load("option-put-call-parity-forward-audit", "utc_z_check", flat="parity_utc_z_check")
UTC_Z_NOTE = ("Output check: {file} {where} `{field}` holds '{value}', a date and time not in the UTC form with a final `Z` after the seconds, but the "
              "task says: \"{quote}\". A timezone-aware datetime written by to_csv, str() or .isoformat() comes out as "
              "'YYYY-MM-DD HH:MM:SS+00:00'. Convert it to text just before writing, for example\n"
              "{fix}\n"
              "and rewrite {file}.")


def _utc_z_quotes(statement: str) -> dict:
    out = {}
    for line in (statement or "").splitlines():
        if _utcz.Z_ASKED.search(line):
            files, fields = _utcz.z_scope(line)
            for n in fields:
                out.setdefault(n, line.strip(" -*\u2014"))
    files, fields = _utcz.z_scope(statement)
    for line in (statement or "").splitlines():
        if _utcz.Z_ASKED.search(line):
            for n in files | fields:
                out.setdefault(n, line.strip(" -*\u2014"))
    return out


def utc_z_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["utc_z_suffix"] or _utcz is None:
        return []
    quotes = _utc_z_quotes(statement)
    out = []
    for rel, hits in _utcz.utc_z_findings(output_dir, statement).items():
        field, value = next(iter(hits.items()))
        name = field.replace(" (key)", "").split(".")[-1]
        quote = quotes.get(name) or quotes.get(os.path.basename(rel)) or next(iter(quotes.values()), "")
        csv_file = rel.endswith(".csv")
        fix = (f"df[{field!r}] = pd.to_datetime(df[{field!r}], utc=True).dt.strftime('%Y-%m-%dT%H:%M:%SZ')" if csv_file else
               "text = ts.tz_convert('UTC').strftime('%Y-%m-%dT%H:%M:%SZ')  # ts: the pd.Timestamp itself, not its string")
        more = [k for k in hits if k != field]
        where = "column" if csv_file else "field"
        note = UTC_Z_NOTE.format(file=rel, where=where, field=field, value=value, quote=quote[:240], fix=fix)
        if more:
            note += " The same holds for " + ", ".join(f"`{k}`" for k in more[:4]) + "."
        out.append({"rule": "utc_z_suffix", "key": ("utc-z", rel), "note": note})
    return out



ENABLED["key_shift"] = True
SHIFT_NOTE = ("Output check: {json}: `{key}` = {v:.10g} equals the mean of column `{other}` ({group}) in {csv}, not the mean "
              "of column `{named}` that its name points to ({mu:.10g}). Check which quantity the task defines for `{key}`. If it "
              "is the one named, the value came from the wrong column, often because a list of values was zipped with a list "
              "of names in a different order; map each value to its name by the column itself, for example "
              "`{{c: df[c].mean() for c in names}}`, and rewrite {json}.")


def key_shift_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["key_shift"] or _rmom is None:
        return []
    import math
    means = [(f, c, g, mu) for f, c, g, mu in _key_means(output_dir)]
    if not means:
        return []
    cols = {c for _, c, _, _ in means}
    out = []
    for p in sorted(glob.glob(os.path.join(output_dir, "*.json"))):
        try:
            leaves = list(_rmom.json_leaves(json.load(open(p))))
        except Exception:
            continue
        for key, v in leaves:
            if len(re.sub(r"[^0-9]", "", ("%.15g" % abs(v)).split("e")[0]).strip("0")) < 6:
                continue
            named = [c for c in cols if len(str(c)) >= 4 and str(key).endswith(str(c))]
            if not named:
                continue
            nc = max(named, key=lambda c: len(str(c)))
            if any(c == nc and _rmom.close(v, mu) for _, c, _, mu in means):
                continue
            files = {f for f, c, _, _ in means if c == nc}
            other = [(f, c, g, mu) for f, c, g, mu in means
                     if f in files and c != nc and not str(nc).endswith(str(c)) and _rmom.close(v, mu)]
            if other:
                f, c, g, _ = other[0]
                mu_named = next((mu for f2, c2, g2, mu in means if f2 == f and c2 == nc and g2 == g), float("nan"))
                out.append({"rule": "key_shift", "key": ("key-shift", os.path.basename(p), key),
                            "note": SHIFT_NOTE.format(json=os.path.basename(p), key=key, v=v, other=c, group=g, csv=f,
                                                      named=nc, mu=mu_named)})
    return out


def _key_means(output_dir):
    import pandas as pd
    frames, out = {}, []
    for f, c, g, mu in _rmom.column_means(output_dir):
        if f not in frames:
            try:
                frames[f] = pd.read_csv(os.path.join(output_dir, f))
            except Exception:
                frames[f] = None
        df = frames[f]
        if df is None:
            continue
        s = df[c] if g == "all" else df.loc[df[g.split("=", 1)[0]].astype(str) == g.split("=", 1)[1], c]
        if s.dropna().nunique() > 1:
            out.append((f, c, g, mu))
    return out


import ast


ENABLED["loc_window"] = True
OFFSETS = {"Timedelta", "DateOffset", "timedelta", "BDay", "Day", "to_timedelta"}

LOC_WINDOW_NOTE = ("Code check: cell {cell} line {line} `{src}` selects rows with a label slice whose stop is the loop "
                   "variable `{v}`. `.loc[a:b]` includes the stop label b, so with an integer index `.loc[{v} - W:{v}]` holds "
                   "W + 1 rows and includes row `{v}` itself; `.iloc[a:b]` and `range(a, b)` exclude b. If the window is "
                   "meant to be the W rows before `{v}`, select it with\n"
                   "train = df.iloc[{v} - W:{v}]\n"
                   "assert len(train) == W and train.index.max() < df.index[{v}]\n"
                   "and rerun every result that used the window.")


def _is_window(sl, v):
    if sl is None:
        return False
    lo, hi = sl
    return (isinstance(hi, ast.Name) and hi.id == v and isinstance(lo, ast.BinOp) and isinstance(lo.op, ast.Sub)
            and isinstance(lo.left, ast.Name) and lo.left.id == v
            and not any(isinstance(n, ast.Attribute | ast.Name) and getattr(n, "attr", getattr(n, "id", "")) in OFFSETS
                        for n in ast.walk(lo.right)))


def _slice_parts(node):
    if isinstance(node, ast.Slice) and node.step is None:
        return node.lower, node.upper
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "slice" and len(node.args) == 2
            and not node.keywords):
        return node.args[0], node.args[1]
    return None


def loc_window_notes(code: str, cell_no) -> list[dict]:
    if not ENABLED["loc_window"]:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    out, lines, seen = [], code.splitlines(), set()
    for loop in (n for n in ast.walk(tree) if isinstance(n, ast.For) and isinstance(n.target, ast.Name)):
        v = loop.target.id
        bound = {}
        for n in ast.walk(loop):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                parts = _slice_parts(n.value)
                if _is_window(parts, v):
                    bound[n.targets[0].id] = True
        for n in ast.walk(loop):
            if not (isinstance(n, ast.Subscript) and isinstance(n.value, ast.Attribute) and n.value.attr == "loc"):
                continue
            key = n.slice.elts[0] if isinstance(n.slice, ast.Tuple) and n.slice.elts else n.slice
            hit = _is_window(_slice_parts(key), v) or (isinstance(key, ast.Name) and key.id in bound)
            if hit and n.lineno not in seen:
                seen.add(n.lineno)
                src = lines[n.lineno - 1].strip() if n.lineno <= len(lines) else ""
                out.append({"rule": "loc_window", "key": ("loc-window", src),
                            "note": LOC_WINDOW_NOTE.format(cell=cell_no, line=n.lineno, src=src, v=v)})
    return out



import math

ENABLED["parity"] = True
PARITY_TOL = 1e-3
COLS = {"S": ("s", "spot", "spot_price", "s0", "underlying_price"), "K": ("k", "strike", "strike_price"),
        "T": ("t", "ttm", "maturity", "tau", "time_to_maturity", "expiry_years", "t_years"),
        "r": ("r", "rate", "risk_free_rate", "rf"), "q": ("q", "dividend_yield", "div_yield"),
        "sigma": ("sigma", "vol", "volatility", "implied_vol"), "type": ("option_type", "type", "cp", "call_put", "right")}
PRICE = ("price", "option_price", "fd_price", "pde_price", "value", "premium")
PARITY_NOTE = ("Output check: in {file}, {n} of {m} call/put pairs with the same S, K, T, r{qs} break put-call parity "
               "C - P = S e^{{-qT}} - K e^{{-rT}} by more than {tol:g} (largest {worst:.4g} at {where}). For European options "
               "this identity holds exactly, so the prices carry a numerical error of this size. Compute the residual for "
               "every pair, as\n"
               "res = C - P - (S * np.exp(-q * T) - K * np.exp(-r * T))\n"
               "and refine the method (finer grid, more time steps, Rannacher start, or the closed form where the task "
               "allows any method) until max(abs(res)) is below the accuracy the task states; then recompute the Greeks.")


def _read(path):
    import pandas as pd
    try:
        return pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
    except Exception:
        return None


def _pick(df, names):
    low = {c.lower(): c for c in df.columns}
    return next((low[n] for n in names if n in low), None)


def parity_notes(output_dir: str, statement: str, data_dirs: list) -> list[dict]:
    if not ENABLED["parity"]:
        return []
    import numpy as np
    if re.search(r"american|early exercise|bermudan", statement, re.I):
        return []
    tables = [p for d in data_dirs for p in glob.glob(os.path.join(d, "**", "*"), recursive=True)
              if p.endswith((".csv", ".parquet"))]
    outs = [p for p in glob.glob(os.path.join(output_dir, "**", "*"), recursive=True) if p.endswith((".csv", ".parquet"))]
    notes = []
    for ip in tables:
        inp = _read(ip)
        if inp is None or len(inp) > 200000:
            continue
        c = {k: _pick(inp, v) for k, v in COLS.items()}
        if not all(c[k] for k in ("S", "K", "T", "r", "type")):
            continue
        if c["q"] is None and re.search(r"dividend", statement, re.I) and not re.search(r"non-dividend|no dividend", statement, re.I):
            continue
        kind = inp[c["type"]].astype(str).str.lower().str[0]
        if not set(kind) <= {"c", "p"}:
            continue
        for op in outs:
            out = _read(op)
            if out is None:
                continue
            pc = _pick(out, PRICE)
            ids = [x for x in out.columns if x in inp.columns and inp[x].is_unique and out[x].is_unique and x not in c.values()]
            if pc is None or not ids:
                continue
            m = inp.merge(out[[ids[0], pc]], on=ids[0])
            m["_k"] = kind.loc[m.index] if len(m) == len(inp) else m[c["type"]].astype(str).str.lower().str[0]
            keys = [c[k] for k in ("S", "K", "T", "r", "q", "sigma") if c[k]]
            bad, total = [], 0
            for key, g in m.groupby(keys):
                calls, puts = g[g["_k"] == "c"][pc], g[g["_k"] == "p"][pc]
                if len(calls) != 1 or len(puts) != 1:
                    continue
                total += 1
                vals = dict(zip(keys, key if isinstance(key, tuple) else (key,)))
                S, K, T, r = (float(vals[c[k]]) for k in ("S", "K", "T", "r"))
                q = float(vals[c["q"]]) if c["q"] else 0.0
                res = float(calls.iloc[0]) - float(puts.iloc[0]) - (S * math.exp(-q * T) - K * math.exp(-r * T))
                if not np.isfinite(res) or abs(res) > PARITY_TOL:
                    bad.append((abs(res), f"S={S:g}, K={K:g}, T={T:.4g}"))
            if bad and total:
                worst = max(bad)
                notes.append({"rule": "parity", "key": ("parity", os.path.basename(op)),
                              "note": PARITY_NOTE.format(file=os.path.basename(op), n=len(bad), m=total, tol=PARITY_TOL,
                                                         worst=worst[0], where=worst[1], qs=", q" if c["q"] else "")})
    return notes



ENABLED["baw_coef"] = True
BAW_NOTE = ("Code check: cell {cell}, function `{fn}`: the early-exercise coefficient `{a}` (line {line}) uses `{d}`, which "
            "is computed from the spot `{spot}` (line {dline}), while the premium term is `{a} * ({spot} / {crit}) ** q`. In "
            "the Barone-Adesi-Whaley approximation the coefficient is fixed at the critical price: "
            "A2 = (S*/q2) [1 - e^{{(b-r)T}} N(d1(S*))] for the call and A1 = -(S**/q1) [1 - e^{{(b-r)T}} N(-d1(S**))] for the "
            "put, with d1 evaluated at the critical price, not at spot. Compute d1 at `{crit}` for the coefficient, keep "
            "d1 at `{spot}` only for the European price, then rerun every price and premium that used this function.")


def _names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _power_terms(fn):
    out = []
    for n in ast.walk(fn):
        if (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow) and isinstance(n.left, ast.BinOp)
                and isinstance(n.left.op, ast.Div) and isinstance(n.left.left, ast.Name) and isinstance(n.left.right, ast.Name)):
            if isinstance(n.right, ast.Name) and re.match(r"q_?[12]$", n.right.id):
                out.append((n.left.left.id, n.left.right.id))
    return out


def _uses_log_of(node, spot):
    for n in ast.walk(node):
        if isinstance(n, ast.Call) and getattr(n.func, "attr", getattr(n.func, "id", "")) == "log" and n.args:
            a = n.args[0]
            if (isinstance(a, ast.BinOp) and isinstance(a.op, ast.Div) and isinstance(a.left, ast.Name) and a.left.id == spot) or \
                    (isinstance(a, ast.Name) and a.id == spot):
                return True
    return False


def baw_coef_notes(code: str, cell_no) -> list[dict]:
    if not ENABLED["baw_coef"]:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    out, lines = [], code.splitlines()
    for fn in (n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.Lambda)) and isinstance(n, ast.FunctionDef)):
        terms = _power_terms(fn)
        if not terms:
            continue
        assigns = sorted(((n.lineno, n) for n in ast.walk(fn) if isinstance(n, ast.Assign) and len(n.targets) == 1
                          and isinstance(n.targets[0], ast.Name)), key=lambda x: x[0])
        for spot, crit in terms:
            if spot == crit:
                continue
            for line, a in assigns:
                rhs = a.value
                tgt = a.targets[0].id
                if crit not in _names(rhs) or not any(isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "cdf"
                                                     or c_name(c) in _cdf_vars(assigns, line) for c in ast.walk(rhs)):
                    continue
                feed = set()
                for c in ast.walk(rhs):
                    if isinstance(c, ast.Call) and getattr(c.func, "attr", "") == "cdf":
                        feed |= _names(c)
                    elif isinstance(c, ast.Name) and c.id in _cdf_vars(assigns, line):
                        feed |= _cdf_vars(assigns, line)[c.id]
                for d in sorted(feed - {spot, crit}):
                    last = next((x for x in reversed(assigns) if x[0] < line and x[1].targets[0].id == d), None)
                    if last and _uses_log_of(last[1].value, spot) and crit not in _names(last[1].value):
                        src = lines[line - 1].strip() if line <= len(lines) else ""
                        out.append({"rule": "baw_coef", "key": ("baw-coef", fn.name, tgt),
                                    "note": BAW_NOTE.format(cell=cell_no, fn=fn.name, a=tgt, line=line, d=d, spot=spot,
                                                            crit=crit, dline=last[0])})
                        break
    seen, uniq = set(), []
    for r in out:
        if r["key"] not in seen:
            seen.add(r["key"])
            uniq.append(r)
    return uniq


def c_name(c):
    return c.id if isinstance(c, ast.Name) else None


def _cdf_vars(assigns, before):
    out = {}
    for line, a in assigns:
        if line >= before:
            break
        v = a.value
        if isinstance(v, ast.Call) and getattr(v.func, "attr", "") == "cdf":
            out[a.targets[0].id] = _names(v)
    return out




ENABLED["global_param"] = True
GLOBAL_PARAM_NOTE = ("Code check: cell {cell}: `{f}` takes a parameter `{p}` and calls `{g}` (line {line}), but `{g}` has no "
                     "parameter `{p}` and reads the global `{p}` instead, so inside `{g}` the value is the global one, "
                     "whatever `{f}` was called with. Add `{p}` as a parameter of `{g}`, pass it in this call, and rerun "
                     "every result that varied `{p}`.")


def _free_reads(fn):
    params = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
    params |= {a.arg for a in (fn.args.vararg, fn.args.kwarg) if a}
    stored = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del))}
    loads = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return params, loads - params - stored


def global_param_notes(code: str, cell_no) -> list[dict]:
    if not ENABLED["global_param"]:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    info = {name: _free_reads(fn) for name, fn in fns.items()}
    out, seen = [], set()
    for fname, fn in fns.items():
        fparams, _ = info[fname]
        for call in (n for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in fns):
            g = call.func.id
            if g == fname:
                continue
            gparams, gfree = info[g]
            passed = {k.arg for k in call.keywords if k.arg} | _names_in(call)
            for p in sorted((fparams & gfree) - gparams):
                if p in passed or len(p) > 12 or p in ("self", "cls") or not _varied(tree, fname, p):
                    continue
                key = ("global-param", fname, g, p)
                if key not in seen:
                    seen.add(key)
                    out.append({"rule": "global_param", "key": key,
                                "note": GLOBAL_PARAM_NOTE.format(cell=cell_no, f=fname, p=p, g=g, line=call.lineno)})
    return out


def _names_in(call):
    return set()


def _varied(tree, fname, p):
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == fname
               and any(k.arg == p and not (isinstance(k.value, ast.Name) and k.value.id == p) for k in n.keywords)
               for n in ast.walk(tree))



ENABLED["cdf_jump"] = True
CDF_JUMP_NOTE = ("Output check: {file} column `{col}` ({group}) rises to exactly 1.0 at the last grid point {g} = {last:g}, "
                 "from {prev:.4g} one point before, while `{other}` there is {ov:.4g}. A simulated CDF that jumps to 1 at "
                 "the horizon usually counts the paths that never reached the level as reaching it at the horizon (a "
                 "never-hit time set to T, or a first index that defaults to the last step), so `tau <= T` holds for "
                 "every path. Give never-hit paths an infinite time, e.g.\n"
                 "tau = np.where(hit.any(axis=1), hit.argmax(axis=1) * dt, np.inf)\n"
                 "and recompute the CDF and every statistic that used tau.")


def cdf_jump_notes(output_dir: str) -> list[dict]:
    if not ENABLED["cdf_jump"]:
        return []
    import pandas as pd
    out = []
    for path in glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True):
        try:
            df = pd.read_csv(path)
        except Exception:
            continue
        cdfs = [c for c in df.columns if "cdf" in str(c).lower() and pd.api.types.is_numeric_dtype(df[c])]
        if len(cdfs) < 2 or len(df) > 100000:
            continue
        grids = [c for c in df.columns if c not in cdfs and pd.api.types.is_numeric_dtype(df[c])]
        texts = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
        if not grids:
            continue
        g = grids[0]
        groups = df.groupby(texts) if texts else [("all", df)]
        for key, part in groups:
            part = part.sort_values(g)
            if len(part) < 3:
                continue
            for col in cdfs:
                s = part[col].to_numpy()
                for other in (c for c in cdfs if c != col):
                    ov = float(part[other].to_numpy()[-1])
                    if s[-1] == 1.0 and s[-2] < 0.9 and ov < 0.99:
                        out.append({"rule": "cdf_jump", "key": ("cdf-jump", os.path.basename(path), col),
                                    "note": CDF_JUMP_NOTE.format(file=os.path.basename(path), col=col, group=key, g=g,
                                                                 last=float(part[g].to_numpy()[-1]), prev=float(s[-2]),
                                                                 other=other, ov=ov)})
                        break
    seen, uniq = set(), []
    for r in out:
        if r["key"] not in seen:
            seen.add(r["key"])
            uniq.append(r)
    return uniq




ENABLED["argmax_hit"] = True
ARGMAX_HIT_NOTE = ("Code check: cell {cell} line {line} `{src}` marks the rows of `{idx}` (a first index from np.argmax of a "
                   "comparison, line {aline}) as never reaching the level by looking at the last column only. A path that "
                   "crossed the level earlier and is back on the other side at the end is marked as never hitting it, so "
                   "hit probabilities and first-passage times come out too low. Decide \"ever hit\" from the whole "
                   "comparison:\n"
                   "hit = X >= level\n"
                   "first = np.where(hit.any(axis=1), hit.argmax(axis=1), -1)\n"
                   "and rerun every result that used `{idx}`.")


def _last_col(node):
    for n in ast.walk(node):
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Tuple) and n.slice.elts:
            e = n.slice.elts[-1]
            if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.USub) and isinstance(e.operand, ast.Constant) and e.operand.value == 1:
                return True
    return False


def argmax_hit_notes(code: str, cell_no) -> list[dict]:
    if not ENABLED["argmax_hit"]:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    lines, idx = code.splitlines(), {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            v = n.value
            if (isinstance(v, ast.Call) and getattr(v.func, "attr", "") == "argmax" and v.args
                    and isinstance(v.args[0], ast.Compare)):
                idx[n.targets[0].id] = n.lineno
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript)):
            continue
        t = n.targets[0]
        if isinstance(t.value, ast.Name) and t.value.id in idx and isinstance(t.slice, ast.Compare) and _last_col(t.slice):
            src = lines[n.lineno - 1].strip() if n.lineno <= len(lines) else ""
            out.append({"rule": "argmax_hit", "key": ("argmax-hit", t.value.id),
                        "note": ARGMAX_HIT_NOTE.format(cell=cell_no, line=n.lineno, src=src, idx=t.value.id, aline=idx[t.value.id])})
    return out




ENABLED["partial_row_ffill"] = True
PARTIAL_ROW_NOTE = ("Code check: cell {cell} line {line} `{src}` writes only some columns of `{frame}` on each loop date, "
                    "and `{frame}` is forward-filled afterwards. Columns not written on a rebalance date stay NaN there and "
                    "the forward fill carries their previous values on, so names that left the selection keep their old "
                    "position. Write each rebalance row in full, for example\n"
                    "{frame}.loc[d] = 0.0\n"
                    "{frame}.loc[d, longs] = w_long\n"
                    "{frame}.loc[d, shorts] = -w_short\n"
                    "then forward-fill, and check that the gross exposure on every date matches the sizing rule.")


def _frame_of(target):
    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Attribute) and target.value.attr == "loc" \
            and isinstance(target.value.value, ast.Name):
        key = target.slice
        if isinstance(key, ast.Tuple) and len(key.elts) == 2:
            return target.value.value.id, key.elts[0], key.elts[1]
        return target.value.value.id, key, None
    return None


def _ffilled(tree, frame):
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            base = n.func.value
            while isinstance(base, ast.Call) and isinstance(base.func, ast.Attribute):
                base = base.func.value
            if not (isinstance(base, ast.Name) and base.id == frame):
                continue
            if n.func.attr == "ffill" or (n.func.attr == "fillna" and any(
                    k.arg == "method" and isinstance(k.value, ast.Constant) and k.value.value in ("ffill", "pad") for k in n.keywords)):
                return True
    return False


def partial_row_ffill_notes(code: str, cell_no) -> list[dict]:
    if not ENABLED["partial_row_ffill"]:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    lines, out, seen = code.splitlines(), [], set()
    for loop in (n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))):
        partial, full = {}, set()
        for n in ast.walk(loop):
            if not isinstance(n, ast.Assign):
                continue
            for t in n.targets:
                f = _frame_of(t)
                if not f:
                    continue
                frame, _, col = f
                if col is None or (isinstance(col, ast.Slice) and col.lower is None and col.upper is None):
                    full.add(frame)
                elif not isinstance(col, ast.Slice):
                    partial.setdefault(frame, n.lineno)
        for frame, line in partial.items():
            if frame in full or frame in seen or not _ffilled(tree, frame):
                continue
            seen.add(frame)
            src = lines[line - 1].strip() if line <= len(lines) else ""
            out.append({"rule": "partial_row_ffill", "key": ("partial-row-ffill", frame),
                        "note": PARTIAL_ROW_NOTE.format(cell=cell_no, line=line, src=src, frame=frame)})
    return out




ENABLED["nan_text"] = True
import csv, glob, io, os, re

NAN_WORDS = {"nan", "NaN", "None", "<NA>", "NAN"}
EMPTY_RULE = re.compile(r"empty[ -]string|empty cell|left empty|leave (?:it |them )?empty|blank", re.I)
NAN_TEXT_NOTE = ("Output check: {file} has {n} cell(s) that read `{word}` in {cols}, but the task asks for empty strings "
                 "for missing values. Formatting a float column to text (an f-string or .map / .apply with a format) turns "
                 "NaN into the word. Keep the column numeric and let to_csv write the missing cells empty:\n"
                 "df.to_csv(path, index=False, float_format=f'%.{{n}}f')   # n = the decimals the task states; NaN is written as ''\n"
                 "or replace the words before writing: df[cols] = df[cols].replace({{'nan': ''}}). Integer columns with "
                 "missing cells: df[col] = df[col].astype('Int64').")


def nan_text_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["nan_text"]:
        return []
    if not EMPTY_RULE.search(statement):
        return []
    out = []
    for path in glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True):
        try:
            rows = list(csv.reader(io.StringIO(open(path, errors="replace").read())))
        except Exception:
            continue
        if len(rows) < 2:
            continue
        head, hits, word = rows[0], {}, None
        for r in rows[1:]:
            for i, v in enumerate(r):
                if v.strip() in NAN_WORDS and i < len(head):
                    hits[head[i]] = hits.get(head[i], 0) + 1
                    word = word or v.strip()
        if hits:
            cols = ", ".join(f"`{c}`" for c in list(hits)[:6]) + (" ..." if len(hits) > 6 else "")
            out.append({"rule": "nan_text", "key": ("nan-text", os.path.basename(path)),
                        "note": NAN_TEXT_NOTE.format(file=os.path.basename(path), n=sum(hits.values()), word=word, cols=cols)})
    return out



ENABLED["reread"] = True
REREAD_AT = 3
FULL_TEXT = re.compile(r"Full text of (\S+) \((?:index only; )?\d+ lines")
REREAD_NOTE = ("The full text of `{file}` is already in your first message above, with line numbers. Read it there instead "
               "of printing it again; use your replies to edit a working copy and run it.")
PY_READ = re.compile(r"\.readlines\(\)|\.read\(\)\s*\.splitlines\(\)|\.read\(\)\s*\[|lines\s*\[\s*-?\d*\s*:\s*-?\d*\s*\]|print\(\s*open\(")
SH_READ = re.compile(r"(?:^|[;&|(]\s*|\s)(?:cat|head|tail|nl|less|more)\b|sed\s+-n\b|awk\s+'NR")


def previewed(first_message: str) -> list:
    return sorted({os.path.basename(p) for p in FULL_TEXT.findall(first_message or "")})


def reread_notes(calls: list, first_message: str, shown: set, counts: dict = None, at: int = REREAD_AT) -> list:
    if not ENABLED["reread"]:
        return []
    counts = {} if counts is None else counts
    names = previewed(first_message)
    if not names:
        return []
    out = []
    for kind, text in calls:
        reader = PY_READ if kind == "python" else SH_READ
        if not reader.search(text):
            continue
        for name in names:
            if name in shown or not re.search(r"(?<![\w.-])" + re.escape(name) + r"(?![\w-])", text):
                continue
            if kind == "python" and ("print(" not in text or re.search(r"open\([^)]*,\s*['\"][wa]|\.write\(|write_text\(", text)):
                continue
            if kind == "bash" and re.search(r"\b(?:python3?|bash|sh)\s+\S*" + re.escape(name), text) and not SH_READ.search(text.split(name)[0][-40:]):
                continue
            counts[name] = counts.get(name, 0) + 1
            if counts[name] < at:
                continue
            shown.add(name)
            out.append(REREAD_NOTE.format(file=name))
    return out



ENABLED["template_run"] = True
import difflib, os, re

FIX_TASK = re.compile(r"\b(?:debug|bugs?|buggy|fix|fixed|errors?|incorrect|wrong)\b", re.I)
PATH_LINE = re.compile(r"/app/|/input/|/output\b|/tmp/|OUTPUT_DIR|DATA_DIR|INPUT_DIR|BASE_DIR|os\.environ|Path\(__file__")
TEMPLATE_RUN_NOTE = ("These output files were last written by the unmodified provided script{name}, which the task says "
                     "produces wrong results: {files}. They will be graded as they are unless your fixed copy overwrites them.")
SH_RUN = re.compile(r"(?:\bcd\s+(\S+)\s*(?:&&|;|\n)\s*)?\bpython3?\s+(?:-\S+\s+)*(\S+\.py)\b")
PY_RUN = re.compile(r"(?:run_path|exec\(\s*open)\(\s*['\"]([^'\"]+\.py)['\"]|['\"](?:python3?|sys\.executable)['\"]\s*,\s*['\"]([^'\"]+\.py)['\"]"
                    r"|sys\.executable\s*,\s*['\"]([^'\"]+\.py)['\"]")


def run_targets(kind: str, text: str) -> list:
    out = []
    if kind == "bash":
        for cd, p in SH_RUN.findall(text):
            out.append(p if os.path.isabs(p) or not cd else os.path.join(cd, p))
    else:
        for m in PY_RUN.findall(text):
            out += [p for p in m if p]
    return out


def path_only(original: str, text: str) -> bool:
    changed = [l for l in difflib.unified_diff(original.splitlines(), text.splitlines(), lineterm="", n=0)
               if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    return all(PATH_LINE.search(l) or not l[1:].strip() for l in changed)


def template_run_record(calls: list, scripts: dict, output_dir: str, since: float, statement: str, state: dict) -> None:
    if not ENABLED["template_run"]:
        return []
    if not scripts or not FIX_TASK.search(statement or ""):
        return
    ran = []
    for kind, text in calls:
        for p in run_targets(kind, text):
            try:
                body = open(p, errors="replace").read()
            except OSError:
                ran.append(None)
                continue
            ran.append(next((s for s in scripts if path_only(scripts[s], body)), None))
    unmodified = bool(ran) and all(ran)
    for d, _, fs in os.walk(output_dir):
        for f in fs:
            path = os.path.join(d, f)
            if os.path.getmtime(path) >= since:
                state[os.path.relpath(path, output_dir)] = (ran[0] if unmodified else None)


def template_run_problems(state: dict, output_dir: str) -> list:
    files = sorted(f for f, src in state.items() if src and os.path.exists(os.path.join(output_dir, f)))
    if not files:
        return []
    src = state[files[0]]
    listed = ", ".join(f"`{f}`" for f in files[:8]) + (" ..." if len(files) > 8 else "")
    return [TEMPLATE_RUN_NOTE.format(name=f" ({src})", files=listed)]



ENABLED["lattice_prob"] = True
LATTICE_NOTE = ("Code check: cell {cell} line {line} `{src}`: node prices are built as `{price}`, so index `{j}` counts the "
                "{counts} moves, but the backward step gives the up probability `{p}` to the child with index `{pj}`, which "
                "is the {child} child. With the up probability on the down child the tree prices under the reversed drift "
                "(calls too low, puts too high). Pair `{p}` with the child one more up move away, e.g. for j = number of up "
                "moves\n"
                "cont = disc * ({p} * V[j + 1, i + 1] + (1 - {p}) * V[j, i + 1])\n"
                "and check that the tree reproduces the European price for a European payoff.")


def _name(n):
    return n.id if isinstance(n, ast.Name) else None


def _up_index(tree):
    for a in ast.walk(tree):
        if not (isinstance(a, ast.Assign) and len(a.targets) == 1 and isinstance(a.targets[0], ast.Subscript)
                and isinstance(a.targets[0].slice, ast.Tuple) and len(a.targets[0].slice.elts) == 2):
            continue
        row = _name(a.targets[0].slice.elts[0])
        for n in ast.walk(a.value):
            if not (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow) and _name(n.left) in ("u", "up", "U")):
                continue
            e = n.right
            if _name(e) and _name(e) == row:
                return row, "up", ast.unparse(a.value)
            if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Sub) and _name(e.right) and _name(e.right) == row:
                return row, "down", ast.unparse(a.value)
    return None


def _first_index(sub):
    s = sub.slice
    if not (isinstance(s, ast.Tuple) and len(s.elts) == 2):
        return None
    e = s.elts[0]
    if _name(e):
        return _name(e), 0
    if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add) and _name(e.left) and isinstance(e.right, ast.Constant) and e.right.value == 1:
        return _name(e.left), 1
    return None


def lattice_prob_notes(code: str, cell_no) -> list[dict]:
    if not ENABLED["lattice_prob"]:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    found = _up_index(tree)
    if not found:
        return []
    j, counts, price = found
    lines, out = code.splitlines(), []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add)):
            continue
        for term in (n.left, n.right):
            if not (isinstance(term, ast.BinOp) and isinstance(term.op, ast.Mult)):
                continue
            p, sub = (term.left, term.right) if isinstance(term.right, ast.Subscript) else (term.right, term.left)
            if not (_name(p) and isinstance(sub, ast.Subscript)):
                continue
            idx = _first_index(sub)
            if not idx or idx[0] != j:
                continue
            wrong = (counts == "up" and idx[1] == 0) or (counts == "down" and idx[1] == 1)
            other = n.right if term is n.left else n.left
            if wrong and isinstance(other, ast.BinOp) and isinstance(other.op, ast.Mult) and f"1 - {_name(p)}" in ast.unparse(other):
                src = lines[n.lineno - 1].strip() if n.lineno <= len(lines) else ""
                pj = j if idx[1] == 0 else f"{j} + 1"
                out.append({"rule": "lattice_prob", "key": ("lattice-prob", src),
                            "note": LATTICE_NOTE.format(cell=cell_no, line=n.lineno, src=src, price=price, j=j, counts=counts,
                                                        p=_name(p), pj=pj, child="down" if counts == "up" else "up")})
                return out
    return out



ENABLED["neg_index"] = True
NEG_INDEX_NOTE = ("Code check: cell {cell} line {line} `{src}`: the loop's first value of `{t}` is {a}, so `{expr}` is "
                  "position {neg} there. A negative position counts from the end (`x.iloc[-1]` is the last row), so the "
                  "first {n} iteration(s) silently read the wrong rows instead of failing. Start the loop where every "
                  "position is in range (t >= {c}), or use a value that is missing before the window has filled (for "
                  "example a rolling sum with min_periods and shift), and recompute the affected rows.")


def _const(n):
    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, int) and not isinstance(n.value, bool) else None


def _start(loop, t):
    a = 0
    it = loop.iter
    if isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range" and len(it.args) >= 2:
        if _const(it.args[0]) is None:
            return None
        a = _const(it.args[0])
    elif not (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range"):
        return None
    for st in loop.body[:3]:
        if isinstance(st, ast.If) and isinstance(st.test, ast.Compare) and isinstance(st.test.left, ast.Name) \
                and st.test.left.id == t and len(st.test.ops) == 1 and _const(st.test.comparators[0]) is not None:
            k, op = _const(st.test.comparators[0]), st.test.ops[0]
            skips = bool(st.body) and isinstance(st.body[0], ast.Continue)
            if isinstance(op, ast.GtE) and not skips:
                a = max(a, k)
            elif isinstance(op, ast.Gt) and not skips:
                a = max(a, k + 1)
            elif isinstance(op, ast.Lt) and skips:
                a = max(a, k)
    return a if a >= 1 else None


def _guarded(node, parents, t, loop, c):
    p = parents.get(node)
    while p is not None and p is not loop:
        test = p.test if isinstance(p, (ast.If, ast.IfExp, ast.While)) else None
        if test is not None and any(isinstance(x, ast.Name) and x.id == t for x in ast.walk(test)):
            if (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and test.left.id == t
                    and len(test.ops) == 1 and _const(test.comparators[0]) is not None
                    and isinstance(test.ops[0], (ast.GtE, ast.Gt))):
                k = _const(test.comparators[0]) + (1 if isinstance(test.ops[0], ast.Gt) else 0)
                if k >= c:
                    return True
            else:
                return True
        p = parents.get(p)
    return False


def neg_index_notes(code: str, cell_no) -> list[dict]:
    if not ENABLED["neg_index"]:
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    lines, out, seen = code.splitlines(), [], set()
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    for loop in (n for n in ast.walk(tree) if isinstance(n, ast.For) and isinstance(n.target, ast.Name)):
        t = loop.target.id
        a = _start(loop, t)
        if a is None:
            continue
        for n in ast.walk(loop):
            if not isinstance(n, ast.Subscript):
                continue
            e = n.slice
            if not (isinstance(e, ast.BinOp) and isinstance(e.op, ast.Sub) and isinstance(e.left, ast.Name) and e.left.id == t):
                continue
            c = _const(e.right)
            if c is None or c <= a or _guarded(n, parents, t, loop, c):
                continue
            src = lines[n.lineno - 1].strip() if n.lineno <= len(lines) else ""
            key = ("neg-index", src)
            if key in seen:
                continue
            seen.add(key)
            out.append({"rule": "neg_index", "key": key,
                        "note": NEG_INDEX_NOTE.format(cell=cell_no, line=n.lineno, src=src, t=t, a=a, expr=ast.unparse(n),
                                                      neg=a - c, n=c - a, c=c)})
    return out



ENABLED["momentum_sharpe"] = True
MOM_SHARPE_NOTE = ("Code check: {file} reports {key} = {val} for a momentum strategy. A long-short momentum backtest with an annualized "
                   "Sharpe ratio above 2 almost always means look-ahead: the signal used for the portfolio return of a month contains "
                   "that month's own return, or a window that should stop earlier. Check that every signal window ends before the month "
                   "it is traded in, that the first valid month and the number of signal months follow from the rule the task states, "
                   "and recompute the outputs.")


def momentum_sharpe_notes(output_dir: str, statement: str = "") -> list[dict]:
    if not ENABLED["momentum_sharpe"] or "momentum" not in statement.lower():
        return []
    out = []
    for path in glob.glob(os.path.join(output_dir, "**", "*.json"), recursive=True):
        try:
            data = json.load(open(path))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        for key, val in data.items():
            if re.fullmatch(r"(?i)(annualized_)?sharpe(_ratio)?", str(key)) and isinstance(val, (int, float)) and not isinstance(val, bool) \
                    and math.isfinite(val) and val > 2:
                out.append({"rule": "momentum_sharpe", "key": ("momentum-sharpe", os.path.basename(path)),
                            "note": MOM_SHARPE_NOTE.format(file=os.path.basename(path), key=key, val=round(val, 2))})
    return out
