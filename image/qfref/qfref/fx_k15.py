import calendar, datetime as dt, glob, json, math, os, re
import pandas as pd

V2_NOTE = ("Output check: {file} {where}: `{key}` = {v:.6g} cannot come out of covered parity for the input forward quote "
           "of {pair} delivering {dd} with any {other} rate quoted for that tenor (range {lo:.4g} to {hi:.4g} percent). "
           "The base and terms roles of the parity were probably swapped: the unknown base rate is "
           "(S(1+r_terms t_terms)/F - 1)/t_base, the unknown terms rate is ((F/S)(1+r_base t_base) - 1)/t_terms.")


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


def pdate(s):
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


PAIR = re.compile(r"^[A-Z]{6}$")
CCY = re.compile(r"^[A-Z]{3}$")
TOL = 0.001


def _pair_of(path, node):
    if isinstance(node.get("pair"), str) and PAIR.match(node["pair"].replace("/", "")):
        return node["pair"].replace("/", "")
    for part in reversed(re.split(r"[/\[\]]", path)):
        if PAIR.match(part):
            return part
    return None


def _forward_quotes(inp):
    quotes, spots = {}, {}
    for f, js in inp.items():
        for path, node in walk(js):
            for k, v in node.items():
                if PAIR.match(str(k)) and isinstance(v, list) and len(v) == 2 and all(num(x) for x in v):
                    spots.setdefault(k, (v[0] + v[1]) / 2)
                if PAIR.match(str(k)) and isinstance(v, dict) and num(v.get("spot_mid")):
                    spots[k] = v["spot_mid"]
    for f, js in inp.items():
        for path, node in walk(js):
            fb = next((node[k] for k in node if "forward" in k.lower() and "bid" in k.lower() and num(node[k])), None)
            fo = next((node[k] for k in node if "forward" in k.lower() and ("offer" in k.lower() or "ask" in k.lower()) and num(node[k])), None)
            dd = pdate(node.get("delivery_date"))
            pair = _pair_of(path, node)
            if fb is None or fo is None or dd is None or pair is None:
                continue
            s = node.get("spot_mid") if num(node.get("spot_mid")) else spots.get(pair)
            if s is None:
                continue
            tenor = path.rsplit("/", 1)[-1]
            quotes[(pair, dd)] = (s, fb, fo, tenor)
    return quotes


def _rates(inp, ccy, tenor):
    vals = []
    for f, js in inp.items():
        found, big = [], False
        for path, node in walk(js):
            for k, v in node.items():
                xs = v if isinstance(v, list) else [v]
                if not all(num(x) for x in xs) or not xs:
                    continue
                parts = set(re.split(r"[/\[\]]", path)) | {k}
                if ccy in parts and tenor in parts:
                    found += [float(x) for x in xs]
                    big = big or any(abs(float(x)) > 1 for x in xs)
        if found:
            vals += [x / 100 if big else x for x in found]
    return vals


def k15(jsons, inp, text):
    if not (re.search(r"\bimplied\b", text, re.I) and re.search(r"\bforwards?\b", text, re.I)):
        return []
    quotes = _forward_quotes(inp)
    if not quotes:
        return []
    out = []
    for f, js in jsons.items():
        for path, node in walk(js):
            keys = [k for k in node if k.lower().startswith("implied") and ("rate" in k.lower() or "yield" in k.lower()) and num(node[k])]
            dd, sd = pdate(node.get("delivery_date")), pdate(node.get("spot_date"))
            ccy = next((v for k, v in node.items() if isinstance(v, str) and CCY.match(v) and "currency" in k.lower()), None)
            pair = _pair_of(path, node)
            if not keys or dd is None or sd is None or ccy is None or pair is None or (pair, dd) not in quotes or ccy not in (pair[:3], pair[3:]):
                continue
            s, fb, fo, tenor = quotes[(pair, dd)]
            other = pair[3:] if ccy == pair[:3] else pair[:3]
            rd = _rates(inp, other, tenor)
            if not rd:
                continue
            days = (dd - sd).days
            hull = []
            for F in (fb, fo):
                for r in (min(rd), max(rd)):
                    for bc in (360.0, 365.0):
                        for bo in (360.0, 365.0):
                            tc, to = days / bc, days / bo
                            if ccy == pair[:3]:
                                hull.append((s * (1 + r * to) / F - 1) / tc)
                            else:
                                hull.append(((F / s) * (1 + r * to) - 1) / tc)
            lo, hi = min(hull) - TOL, max(hull) + TOL
            for k in keys:
                v = float(node[k])
                if not (lo <= v / 100 <= hi or lo <= v <= hi):
                    out.append(V2_NOTE.format(file=f, where=path, key=k, v=v, pair=pair, dd=dd, other=other, lo=lo * 100, hi=hi * 100))
    return out


def k15_notes(output_dir, data_dirs, text):
    for d in data_dirs:
        if os.path.isdir(d):
            inp = read_inputs(d)[0]
            break
    else:
        return []
    _, jsons = read_out(output_dir)
    return k15(jsons, inp, text)
