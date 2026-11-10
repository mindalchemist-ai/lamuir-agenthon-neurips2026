import csv, glob, math, os, re, sys

START = re.compile(r"^(tau|t|mat|maturity|tenor|start|from)_?1$|^(tau|t|maturity|tenor)_?(start|from|a)$|^start\w*$", re.I)
END = re.compile(r"^(tau|t|mat|maturity|tenor|end|to)_?2$|^(tau|t|maturity|tenor)_?(end|to|b)$|^end\w*$", re.I)
FWD = re.compile(r"(^|_)(fwd|forward)(_|$)", re.I)
TAU = re.compile(r"^(tau|t|maturity|tenor|ttm|years?|time_to_maturity)$", re.I)
PRICE = re.compile(r"(^|_)(zcb|discount|df|bond)?_?(price|factor|df)s?$|^p$|^zcb$|^discount_factor$", re.I)


def rows(path):
    try:
        with open(path, newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def num(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def price_curves(output_dir):
    out = []
    for p in glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True):
        r = rows(p)
        if not r:
            continue
        cols = list(r[0].keys())
        tc = [c for c in cols if TAU.match(c.strip())]
        pc = [c for c in cols if PRICE.search(c.strip()) and not FWD.search(c)]
        for t in tc:
            for c in pc:
                curve = {}
                for row in r:
                    a, b = num(row.get(t)), num(row.get(c))
                    if a is not None and b is not None and 0 < b <= 1.5:
                        curve[round(a, 10)] = b
                if len(curve) >= 2:
                    out.append((os.path.basename(p), c, curve))
    return out


def forward_sign_notes(output_dir):
    curves = price_curves(output_dir)
    notes = []
    if not curves:
        return notes
    for p in glob.glob(os.path.join(output_dir, "**", "*.csv"), recursive=True):
        r = rows(p)
        if not r:
            continue
        cols = list(r[0].keys())
        s = next((c for c in cols if START.match(c.strip())), None)
        e = next((c for c in cols if END.match(c.strip())), None)
        fc = [c for c in cols if FWD.search(c.strip())]
        if not (s and e and fc):
            continue
        for f in fc:
            for cname, pcol, curve in curves:
                hit = tot = 0
                for row in r:
                    a, b, v = num(row.get(s)), num(row.get(e)), num(row.get(f))
                    if None in (a, b, v) or b <= a or round(a, 10) not in curve or round(b, 10) not in curve:
                        continue
                    implied = math.log(curve[round(a, 10)] / curve[round(b, 10)]) / (b - a)
                    if abs(implied) < 1e-12:
                        continue
                    tot += 1
                    if abs(v + implied) <= 1e-6 * abs(implied):
                        hit += 1
                if tot >= 2 and hit == tot:
                    notes.append(
                        f"Output check: every `{f}` in {os.path.basename(p)} equals minus ln({pcol}({s}) / {pcol}({e})) / "
                        f"({e} - {s}) from {cname}. The continuously compounded average forward between two maturities is "
                        f"ln(P(start) / P(end)) / (end - start), which is positive when the price falls with maturity. "
                        f"If the code stores z = -ln(P) (the zero-rate exponent), the forward is (z_end - z_start) / "
                        f"(end - start); putting a further minus in front of that difference flips the sign. "
                        f"If the task defines this quantity with the opposite sign, keep the value and state the convention.")
                    break
    return notes


if __name__ == "__main__":
    for d in sys.argv[1:]:
        for n in forward_sign_notes(d):
            print(d, "\n  ", n)
