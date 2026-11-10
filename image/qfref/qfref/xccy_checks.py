import glob, json, math, os, re
import pandas as pd

TENOR_RE = re.compile(r"^(\d+)\s*([DWMY])$", re.I)


def _csvs(d, nrows=5000):
    out = []
    for p in sorted(glob.glob(os.path.join(d, "*.csv"))):
        try:
            if os.path.getsize(p) > 20_000_000:
                continue
            df = pd.read_csv(p, nrows=nrows)
        except Exception:
            continue
        if len(df.columns) and len(df):
            out.append((os.path.basename(p), df))
    return out


def _jsons(d):
    out = []
    for p in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            if os.path.getsize(p) > 5_000_000:
                continue
            out.append((os.path.basename(p), json.load(open(p))))
        except Exception:
            continue
    return out


def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def _leaves(v, path=""):
    if isinstance(v, dict):
        for k, x in v.items():
            yield from _leaves(x, f"{path}.{k}" if path else str(k))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from _leaves(x, f"{path}[{i}]")
    else:
        yield path, v


def k1_tenor_labels(out_csvs, in_csvs):
    labels = set()
    for _, df in in_csvs:
        for c in df.columns:
            if str(c).lower() == "tenor":
                labels |= {str(x).strip().upper() for x in df[c].dropna()}
    if not labels:
        return []
    msgs = []
    for name, df in out_csvs:
        for c in df.columns:
            if str(c).lower() != "tenor":
                continue
            vals = [str(x).strip() for x in df[c].dropna()]
            odd = sorted({v for v in vals if TENOR_RE.match(v) and v.upper() not in labels})
            if odd:
                msgs.append(f"K1 {name}: tenor labels {odd[:4]} do not appear in any input tenor column")
    return msgs


def k3_forward_equals_spot(out_csvs):
    msgs = []
    for name, df in out_csvs:
        cols = [str(c) for c in df.columns]
        sc = [c for c in cols if re.search(r"(^|_)spot($|_)", c.lower()) and "rate" not in c.lower() and pd.api.types.is_numeric_dtype(df[c])]
        fc = [c for c in cols if re.search(r"forward|cip", c.lower()) and not re.search(r"point|rate", c.lower()) and pd.api.types.is_numeric_dtype(df[c])]
        if not any("fx" in c.lower() for c in sc + fc):
            continue
        for s in sc:
            for f in fc:
                a, b = df[s].astype(float), df[f].astype(float)
                ok = a.notna() & b.notna() & (a > 0)
                if ok.sum() < 3:
                    continue
                eq = (abs(a[ok] - b[ok]) <= 1e-12 * a[ok].abs())
                if 0 < eq.sum() < ok.sum():
                    msgs.append(f"K3 {name}: {f} equals {s} on {int(eq.sum())} of {int(ok.sum())} rows")
    return msgs


def k5_stress_pnl(out_csvs, out_jsons):
    msgs = []
    base = {}
    for _, obj in out_jsons:
        for p, v in _leaves(obj):
            x = _num(v)
            if x is not None:
                base.setdefault(p.split(".")[-1].lower(), x)
    for name, df in out_csvs:
        cols = {str(c).lower(): c for c in df.columns}
        pnl = [c for l, c in cols.items() if re.search(r"(^|_)pnl($|_)", l)]
        pvs = [c for l, c in cols.items() if l in base and re.search(r"(^|_)(n?pv|value)($|_)", l)]
        if len(pnl) != 1 or len(pvs) != 1:
            continue
        d = df[pvs[0]].astype(float) - base[str(pvs[0]).lower()] - df[pnl[0]].astype(float)
        scale = max(1.0, float(df[pvs[0]].astype(float).abs().max()))
        bad = int((d.abs() > 1e-6 * scale).sum())
        if bad:
            msgs.append(f"K5 {name}: {pnl[0]} != {pvs[0]} - base on {bad} rows")
    return msgs


def k6_accrual_year_frac(out_csvs):
    msgs = []
    for name, df in out_csvs:
        cols = {str(c).lower(): c for c in df.columns}
        if not {"accrual_start", "accrual_end"} <= set(cols):
            continue
        yc = [c for l, c in cols.items() if l in ("year_frac", "year_fraction", "accrual_fraction", "accrual_factor", "dcf")]
        if not yc:
            continue
        a = pd.to_datetime(df[cols["accrual_start"]], errors="coerce")
        b = pd.to_datetime(df[cols["accrual_end"]], errors="coerce")
        y = pd.to_numeric(df[yc[0]], errors="coerce")
        ok = a.notna() & b.notna() & y.notna() & (b > a)
        if not ok.any():
            continue
        days = (b[ok] - a[ok]).dt.days.astype(float)
        def d30(s, e):
            d1, d2 = min(s.day, 30), e.day if not (s.day >= 30 and e.day == 31) else 30
            return 360 * (e.year - s.year) + 30 * (e.month - s.month) + (d2 - d1)
        t30 = pd.Series([d30(s, e) / 360.0 for s, e in zip(a[ok], b[ok])], index=days.index)
        cands = [days / 360.0, days / 365.0, days / 365.25, t30]
        bad = ~pd.concat([(abs(y[ok] - c) <= 1e-9) for c in cands], axis=1).any(axis=1)
        if bad.any():
            msgs.append(f"K6 {name}: {yc[0]} matches no standard day count of accrual dates on {int(bad.sum())} rows")
    return msgs


def k7_coupon_amount(out_csvs):
    msgs = []
    for name, df in out_csvs:
        cols = {str(c).lower(): c for c in df.columns}
        need = ("notional", "year_frac", "coupon_rate")
        if not all(n in cols for n in need):
            continue
        cf = [c for l, c in cols.items() if re.search(r"cashflow|amount", l) and "ccy" in l and pd.api.types.is_numeric_dtype(df[c])] or \
             [c for l, c in cols.items() if re.search(r"^(signed_)?cash_?flow$|^amount$", l) and pd.api.types.is_numeric_dtype(df[c])]
        tc = [c for l, c in cols.items() if l in ("cashflow_type", "type", "flow_type", "event")]
        if not cf:
            continue
        sub = df if not tc else df[df[tc[0]].astype(str).str.lower().str.contains("coupon")]
        n, y, r = [pd.to_numeric(sub[cols[k]], errors="coerce") for k in need]
        c = pd.to_numeric(sub[cf[0]], errors="coerce")
        ok = n.notna() & y.notna() & r.notna() & c.notna()
        if ok.sum() == 0:
            continue
        exp = (n[ok] * y[ok] * r[ok]).abs()
        bad = (abs(c[ok].abs() - exp) > 1e-6 * exp.clip(lower=1.0)).sum()
        if bad:
            msgs.append(f"K7 {name}: |{cf[0]}| != notional*year_frac*coupon_rate on {int(bad)} coupon rows")
    return msgs


def k8_pv_product(out_csvs):
    msgs = []
    for name, df in out_csvs:
        cols = {str(c).lower(): c for c in df.columns}
        pv = [c for l, c in cols.items() if re.match(r"^pv(_[a-z]{3})?$", l)]
        dfc = [c for l, c in cols.items() if l.startswith("discount_factor") or l in ("df", "df_usd")]
        cf = [c for l, c in cols.items() if re.search(r"cashflow|amount", l) and pd.api.types.is_numeric_dtype(df[c])]
        fx = [c for l, c in cols.items() if re.match(r"^fx(_forward|_rate)?$", l)]
        if len(pv) != 1 or len(dfc) != 1 or len(cf) != 1:
            continue
        p, d, c = (pd.to_numeric(df[x], errors="coerce") for x in (pv[0], dfc[0], cf[0]))
        f = pd.to_numeric(df[fx[0]], errors="coerce") if fx else 1.0
        e1, e2 = c * d * f, c * d
        ok = p.notna() & e1.notna() & e2.notna()
        if ok.sum() == 0:
            continue
        tol = 1e-6 * pd.concat([e1[ok].abs(), e2[ok].abs()], axis=1).max(axis=1).clip(lower=1.0)
        bad = ((abs(p[ok] - e1[ok]) > tol) & (abs(p[ok] - e2[ok]) > tol)).sum()
        if bad:
            msgs.append(f"K8 {name}: {pv[0]} != {cf[0]}*{dfc[0]}{'*' + fx[0] if fx else ''} on {int(bad)} rows")
    return msgs


def k9_reset_rows_zero(out_csvs):
    msgs = []
    for name, df in out_csvs:
        cols = {str(c).lower(): c for c in df.columns}
        tc = [c for l, c in cols.items() if l in ("cashflow_type", "type", "flow_type", "event")]
        cf = [c for l, c in cols.items() if re.search(r"cashflow|amount", l) and pd.api.types.is_numeric_dtype(df[c])]
        if not tc or not cf:
            continue
        m = df[tc[0]].astype(str).str.lower().str.contains("reset")
        if m.sum() >= 2:
            v = pd.to_numeric(df.loc[m, cf[0]], errors="coerce")
            if v.notna().all() and (v == 0).all():
                msgs.append(f"K9 {name}: all {int(m.sum())} reset rows have {cf[0]} == 0")
    return msgs


