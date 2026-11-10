import csv
import glob
import json
import math
import os
import re

csv.field_size_limit(10**9)


NAT_PRELOAD = r'''
import pandas as _k1_pd
_K1_LOG = []
_k1_orig = _k1_pd.to_datetime
def _k1_to_datetime(arg, *a, **k):
    res = _k1_orig(arg, *a, **k)
    if k.get("errors") == "coerce" and k.get("format") != "mixed":
        try:
            s = _k1_pd.Series(arg).astype("string")
            r = _k1_pd.Series(_k1_pd.DatetimeIndex(res) if not isinstance(res, _k1_pd.Series) else res.values)
            lost = s[r.isna().values & s.notna().values & (s.str.strip().fillna("").str.len() > 0).values]
            lost = lost[~lost.str.strip().str.lower().isin(["nat", "nan", "none", "null", "na"])]
            if len(lost):
                ok = _k1_orig(lost, errors="coerce", format="mixed").notna()
                if ok.any():
                    _K1_LOG.append({"lost": int(len(lost)), "mixed_ok": int(ok.sum()),
                                    "samples": list(dict.fromkeys(lost[ok.values].tolist()))[:3],
                                    "format": k.get("format")})
        except Exception:
            pass
    return res
_k1_pd.to_datetime = _k1_to_datetime
'''
NAT_READ = 'import json as _k1j; print("K1LOG", _k1j.dumps(_K1_LOG)); _K1_LOG.clear()'


def nat_note(entry: dict) -> str:
    fmt = f" with format={entry['format']!r}" if entry.get("format") else ""
    return (f"Code note: pd.to_datetime(..., errors='coerce'){fmt} in this cell turned {entry['lost']} non-empty date "
            f"strings into NaT, and {entry['mixed_ok']} of them are valid dates in another layout, for example "
            f"{', '.join(repr(x) for x in entry['samples'])}. Rows dropped for NaT later would be valid rows. Parse the "
            "column with format='mixed' (or the explicit format of each layout) and keep errors='coerce' only for "
            "strings that are not dates.")


def nat_log_entries(probe_output: str) -> list[dict]:
    m = re.search(r"K1LOG (\[.*\])", probe_output)
    try:
        return json.loads(m.group(1)) if m else []
    except ValueError:
        return []


_K1_CALL = re.compile(r"to_datetime\(\s*(\w+)\s*\[\s*['\"]([^'\"]+)['\"]\s*\][^)]*errors\s*=\s*['\"]coerce['\"]")


def nat_replay_entries(code: str, data_files: list[str]) -> list[dict]:
    import pandas as pd
    out = []
    for m in _K1_CALL.finditer(code):
        col = m.group(2).strip()
        tail = code[m.start(): code.find(")", m.end() - 1) + 1]
        if re.search(r"format\s*=\s*['\"]mixed['\"]", tail):
            continue
        fm = re.search(r"format\s*=\s*['\"]([^'\"]+)['\"]", tail)
        for f in data_files:
            try:
                raw = pd.read_csv(f, dtype=str, nrows=200000)
            except Exception:
                continue
            raw.columns = [c.strip() for c in raw.columns]
            if col not in raw.columns:
                continue
            s = raw[col]
            r = pd.to_datetime(s, errors="coerce", **({"format": fm.group(1)} if fm else {}))
            lost = s[r.isna() & s.notna() & (s.fillna("").str.strip().str.len() > 0)]
            lost = lost[~lost.str.strip().str.lower().isin(["nat", "nan", "none", "null", "na"])]
            if len(lost):
                ok = pd.to_datetime(lost, errors="coerce", format="mixed").notna()
                if ok.any():
                    out.append({"lost": int(len(lost)), "mixed_ok": int(ok.sum()),
                                "samples": list(dict.fromkeys(lost[ok].tolist()))[:3],
                                "format": fm.group(1) if fm else None, "column": col, "file": os.path.basename(f)})
    return out



def _json_leaves(obj, path, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _json_leaves(v, path + [str(k)], out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:2000]):
            _json_leaves(v, path + [f"[{i}]"], out)
    else:
        keys = [p for p in path if not p.startswith("[")]
        name = keys[-1] if keys else ""
        if name.lower() in {"value", "val", "estimate"} and len(keys) > 1:
            name = keys[-2]
        out.append((".".join(path), name, obj))


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _out_files(output_dir, ext):
    return sorted(glob.glob(os.path.join(output_dir, "**", "*" + ext), recursive=True))


def _csv_rows(path, limit=20000):
    with open(path, newline="", errors="replace") as f:
        rd = csv.reader(f)
        hdr = next(rd, None) or []
        rows = []
        for i, r in enumerate(rd):
            if i >= limit:
                break
            rows.append(r)
    return [h.strip() for h in hdr], rows



_M1_TOK = re.compile(r"(?:^|_)(mean|median)(?=_|$)")


def mean_median_notes(output_dir: str) -> list[str]:
    by = {}
    for fp in _out_files(output_dir, ".json"):
        try:
            leaves = []
            _json_leaves(json.load(open(fp)), [], leaves)
        except Exception:
            continue
        rel = os.path.relpath(fp, output_dir)
        for path, name, v in leaves:
            if not _is_num(v):
                continue
            m = list(_M1_TOK.finditer(name.lower()))
            if len(m) != 1:
                continue
            stem = (name.lower()[:m[0].start()] + "_" + name.lower()[m[0].end():]).strip("_")
            by.setdefault(stem, {}).setdefault(m[0].group(1), []).append((rel, path, v))
    out = []
    for stem, d in by.items():
        if not stem or "mean" not in d or "median" not in d:
            continue
        for fm, pm, vm in d["mean"]:
            hit = next(((fd, pd_, vd) for fd, pd_, vd in d["median"] if float(vm) == float(vd)
                        and not float(vm).is_integer()), None)
            if hit:
                out.append(f"Output check: {fm} `{pm}` = {vm!r} and {hit[0]} `{hit[1]}` = {hit[2]!r} are exactly equal. A "
                           "mean and a median of the same sample coincide only for a symmetric sample; equal values to the "
                           "last digit usually mean one statistic was assigned to both fields. Recompute each from its own "
                           "formula and write it again.")
                break
    return out[:2]



_F1_TICK = re.compile(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`")
_F1_NEAR = re.compile(r"\breported as\b|\breport(?:ed)? (?:it )?(?:in|under|as)\b|\bintermediates?\b|\b(?:key|field|column)s?\b", re.I)
_F1_COND = re.compile(r"\bif\b.{0,160}?\b(?:does not|do not|doesn't|not include|absent|missing|unavailable)\b", re.I)
_F1_VERB = re.compile(r"\b(report(?:ed|s)?|intermediates?|output(?:s|ted)?|write|written|include[sd]?|key|field|column)\b", re.I)


def _input_names(data_dirs):
    names = set()
    for d in data_dirs:
        for fp in glob.glob(os.path.join(d, "**", "*"), recursive=True):
            names.add(os.path.splitext(os.path.basename(fp))[0].lower())
            try:
                if fp.endswith((".csv", ".tsv")):
                    with open(fp, newline="", errors="replace") as f:
                        names |= {h.strip().lower() for h in next(csv.reader(f, delimiter="\t" if fp.endswith(".tsv") else ","), [])}
                elif fp.endswith((".parquet", ".pqt")):
                    import pyarrow.parquet as pq
                    names |= {c.lower() for c in pq.read_schema(fp).names}
                elif fp.endswith(".json") and os.path.getsize(fp) < 5_000_000:
                    leaves = []
                    _json_leaves(json.load(open(fp)), [], leaves)
                    names |= {p.lower() for path, _, _ in leaves for p in path.split(".")}
            except Exception:
                continue
    return names


def _output_names(output_dir):
    names, strings = set(), set()
    for fp in _out_files(output_dir, ".json"):
        try:
            leaves = []
            _json_leaves(json.load(open(fp)), [], leaves)
        except Exception:
            continue
        for path, _, v in leaves:
            names |= {p.lower() for p in path.split(".")}
            if isinstance(v, str):
                strings.add(v.strip().lower())
    for fp in _out_files(output_dir, ".csv"):
        try:
            hdr, rows = _csv_rows(fp, 2000)
        except Exception:
            continue
        names |= {h.lower() for h in hdr}
        for r in rows:
            strings |= {c.strip().lower() for c in r[:3]}
    return names, strings


def named_field_notes(output_dir: str, statement: str, data_dirs: list[str]) -> list[str]:
    if not statement:
        return []
    inputs = _input_names(data_dirs)
    names, strings = _output_names(output_dir)
    missing = []
    for sent in re.split(r"(?<=[.!?])\s+|\n\s*\n|\n\s*[-*\d]+[.)]?\s", statement):
        if not _F1_VERB.search(sent) or _F1_COND.search(sent):
            continue
        for m in _F1_TICK.finditer(sent):
            tok = m.group(1)
            if len(tok) < 5:
                continue
            after = sent[m.end(): m.end() + 2]
            near = sent[max(0, m.start() - 40): m.end() + 40]
            if not _F1_NEAR.search(near) or "=" in sent[m.end(): m.end() + 4]:
                continue
            if after.startswith("(") or tok in inputs or tok in names or tok in strings or tok in missing:
                continue
            missing.append(tok)
    if not missing:
        return []
    return [f"Output check: the task names `{t}` as a value to report, but no output file has a key, column or label "
            f"`{t}`. Find the sentence that defines it, compute it, and add it where that sentence puts it (an "
            "intermediate, a summary key or a column)." for t in missing[:3]]



_D1_COL = re.compile(r"^(?P<a>.+?)_(?P<op>minus|plus|over|div|times)_(?P<b>.+)$")
_D1_SYM = {"minus": "-", "plus": "+", "times": "*", "over": "/", "div": "/"}
_D1_OPS = {"minus": lambda a, b: a - b, "plus": lambda a, b: a + b, "times": lambda a, b: a * b,
           "over": lambda a, b: a / b if b != 0 else None, "div": lambda a, b: a / b if b != 0 else None}


def _decimals(s):
    s = s.strip()
    if "e" in s.lower():
        return None
    return len(s.split(".")[1]) if "." in s else 0


def _stated_decimals(statement):
    m = re.search(r"\b(\d)\s+decimal(?:\s+places?)?\b", statement or "")
    return int(m.group(1)) if m else None


def _operand_pairs(a, b, idx):
    pairs = [(a, b)] if a in idx and b in idx else []
    for h in idx:
        if h.startswith(a + "_") and b + h[len(a):] in idx:
            pairs.append((h, b + h[len(a):]))
    return pairs


def _identity_misses(rows, ia, ib, ic, op):
    from decimal import Decimal, InvalidOperation
    checked, bad, first = 0, 0, None
    for n, r in enumerate(rows):
        try:
            sa, sb, sc = r[ia].strip(), r[ib].strip(), r[ic].strip()
            a, b, c = Decimal(sa), Decimal(sb), Decimal(sc)
        except (IndexError, InvalidOperation):
            continue
        if not all(x.is_finite() for x in (a, b, c)) or (op in ("over", "div") and b == 0):
            continue
        want = {"minus": lambda: a - b, "plus": lambda: a + b, "times": lambda: a * b}.get(op, lambda: a / b)()
        half = Decimal(5) * Decimal(10) ** (c.as_tuple().exponent - 1)
        noise = Decimal("1e-12") * max(abs(a), abs(b), abs(c), Decimal(1))
        if op in ("over", "div", "times"):
            ua = Decimal(5) * Decimal(10) ** (a.as_tuple().exponent - 1)
            ub = Decimal(5) * Decimal(10) ** (b.as_tuple().exponent - 1)
            half += abs(want) * (ua / max(abs(a), Decimal("1e-300")) + ub / max(abs(b), Decimal("1e-300")))
        checked += 1
        if abs(c - want) > half + noise:
            bad += 1
            if first is None:
                first = (n + 1, sa, sb, sc, want)
    return checked, bad, first


def derived_identity_notes(output_dir: str, statement: str) -> list[str]:
    out = []
    for fp in _out_files(output_dir, ".csv"):
        try:
            hdr, rows = _csv_rows(fp)
        except Exception:
            continue
        idx = {h: i for i, h in enumerate(hdr)}
        for h in hdr:
            m = _D1_COL.match(h)
            if not m:
                continue
            op = m.group("op")
            best = None
            for ca, cb in _operand_pairs(m.group("a"), m.group("b"), idx):
                if h in (ca, cb):
                    continue
                checked, bad, first = _identity_misses(rows, idx[ca], idx[cb], idx[h], op)
                if checked and (best is None or bad < best[3]):
                    best = (ca, cb, checked, bad, first)
            if not best or best[3] == 0 or best[3] == best[2]:
                continue
            ca, cb, checked, bad, (n, sa, sb, sc, want) = best
            rel = os.path.relpath(fp, output_dir)
            decs = {_decimals(r[idx[h]]) for r in rows if len(r) > idx[h] and r[idx[h]].strip()}
            fixed = (f" Every row of `{h}` is written with exactly {next(iter(decs))} decimals, so the file uses fixed-decimal "
                     "formatting.") if len(decs) == 1 and None not in decs else ""
            out.append(f"Output check: {rel}: `{h}` differs from `{ca}` {op} `{cb}` on {bad} of {checked} rows "
                       f"(row {n}: {sc} vs {sa} {op} {sb} = {float(want):.12g}).{fixed} A derived column must equal the "
                       "identity its name states on the values as written. First choice: write the floats themselves, "
                       "with no fixed-decimal formatting (no f\"{x:.Nf}\", round() or float_format), so pandas writes "
                       f"full precision and `{h}` as written matches `{ca}` {_D1_SYM[op]} `{cb}` as written up to float rounding. Second choice, "
                       "if a fixed number of decimals is required: round the operands to those decimals first and compute "
                       "the derived column from the rounded operands.")
            if len(out) >= 2:
                return out
    return out



_S1_UNION = re.compile(r"\bunion of\b", re.I)
_S1_TOPN = re.compile(r"\btop[- ]?(\d{1,4})\b", re.I)
_TRUE, _FALSE = {"true", "1", "1.0", "yes", "y", "t"}, {"false", "0", "0.0", "no", "n", "f", ""}


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
        for i in flags:
            vals = [r[i].strip().lower() if i < len(r) else "" for r in rows]
            if not all(v in _TRUE | _FALSE for v in vals):
                continue
            k = sum(v in _TRUE for v in vals)
            if k > n:
                rel = os.path.relpath(fp, output_dir)
                out.append(f"Output check: {rel}: `{hdr[i]}` is true on {k} of {len(rows)} rows, but the task builds this "
                           f"table from top-{n} lists, so membership of one list can be true on at most {n} rows. The flag "
                           "should mark membership of that list's top-{n} (the list used to build the union), not every "
                           "holding of the source.".replace("top-{n}", f"top-{n}"))
    return out[:2]



P6_INTRO = ("Ownership footnotes in the Form 4 inputs, as written in the files: each ownership field that points to a "
            "footnote (with the element path of its footnoteId), the transaction or holding rows that carry it, then the "
            "text of those footnotes. Form 4 General Instruction 4(b)(iii) has each form of indirect ownership reported "
            "on its own line, with its nature stated specifically (a named trust, entity or relative); when the nature "
            "field only points to a footnote, that footnote carries the statement, and rows pointing to different "
            "footnotes are different indirect holdings.")
_P6_ROWS = ("nonDerivativeTransaction", "nonDerivativeHolding", "derivativeTransaction", "derivativeHolding")


def _p6_val(el, path):
    x = el.find(path)
    if x is None:
        return None
    v = x.find("value")
    return (((v.text if v is not None else x.text) or "").strip()) or None


def form4_footnote_preview(data_dirs: list[str], max_note: int = 300) -> str:
    import xml.etree.ElementTree as ET
    blocks, seen = [], set()
    for d in data_dirs:
        for fp in sorted(glob.glob(os.path.join(d, "**", "*.xml"), recursive=True)):
            name = os.path.basename(fp)
            if name in seen:
                continue
            try:
                root = ET.parse(fp).getroot()
            except Exception:
                continue
            if root.tag.split("}")[-1] != "ownershipDocument":
                continue
            seen.add(name)
            notes = {f.get("id"): " ".join((f.text or "").split()) for f in root.iter("footnote")}
            groups = {}
            n = 0
            for kind in _P6_ROWS:
                for row in root.iter(kind):
                    n += 1
                    for fld in ("directOrIndirectOwnership", "natureOfOwnership"):
                        el = row.find(f"ownershipNature/{fld}")
                        if el is None:
                            continue
                        for ref in [f.get("id") for f in el.iter("footnoteId")]:
                            groups.setdefault((fld, _p6_val(row, f"ownershipNature/{fld}"), ref), []).append(n)
            if not groups:
                continue
            lines = [f"== {name} ({n} transaction and holding rows)"]
            for fld in dict.fromkeys(f for f, _, _ in groups):
                lines.append(f"  {fld}: value at ownershipNature/{fld}/value, footnote reference at "
                             f"ownershipNature/{fld}/footnoteId/@id")
            for (fld, val, ref), rows in groups.items():
                shown = f'"{val}"' if val else "(no value)"
                lines.append(f"  {fld} = {shown} -> {ref} [rows {', '.join(map(str, rows))}]")
            for ref in dict.fromkeys(r for _, _, r in groups):
                body = notes.get(ref, "")
                lines.append(f"  {ref}: {body[:max_note]}{'...' if len(body) > max_note else ''}")
            blocks.append("\n".join(lines))
    return P6_INTRO + "\n" + "\n".join(blocks) if blocks else ""



_P7_FIELD = re.compile(r"(entity|owner|holder|beneficial|nature|name)", re.I)
_P7_PLACEHOLDER = re.compile(r"^\s*(see\s+(the\s+)?(footnotes?|note)\b.*|by\s+trust|\(?\d{1,2}\)?|f\d{1,2})\s*$", re.I)


def _p7_xml_refs(data_dirs):
    import xml.etree.ElementTree as ET
    refs = {}
    for d in data_dirs:
        for fp in sorted(glob.glob(os.path.join(d, "**", "*.xml"), recursive=True)):
            try:
                root = ET.parse(fp).getroot()
            except Exception:
                continue
            if root.tag.split("}")[-1] != "ownershipDocument":
                continue
            stem = os.path.splitext(os.path.basename(fp))[0]
            notes = {f.get("id"): " ".join((f.text or "").split()) for f in root.iter("footnote")}
            n = 0
            for kind in _P6_ROWS:
                for row in root.iter(kind):
                    n += 1
                    el = row.find("ownershipNature/natureOfOwnership")
                    val = _p6_val(row, "ownershipNature/natureOfOwnership")
                    if el is None or not val:
                        continue
                    for ref in [f.get("id") for f in el.iter("footnoteId")]:
                        lst = refs.setdefault((stem, val.lower()), [])
                        hit = next((x for x in lst if x[0] == ref), None)
                        if hit is None:
                            lst.append((ref, notes.get(ref, ""), [n]))
                        else:
                            hit[2].append(n)
    return refs


def _p7_values(output_dir):
    out = []
    for fp in _out_files(output_dir, ".csv"):
        try:
            hdr, rows = _csv_rows(fp)
        except Exception:
            continue
        fid = next((i for i, h in enumerate(hdr) if h.lower() in ("filing_id", "accession", "filing", "source_file")), None)
        for i, h in enumerate(hdr):
            if _P7_FIELD.search(h):
                for r in rows:
                    if len(r) > i:
                        out.append((fp, h, r[i], r[fid] if fid is not None and len(r) > fid else None))
    for fp in _out_files(output_dir, ".json"):
        try:
            leaves = []
            _json_leaves(json.load(open(fp)), [], leaves)
        except Exception:
            continue
        for _, name, v in leaves:
            if isinstance(v, str) and _P7_FIELD.search(name):
                out.append((fp, name, v, None))
    return out


def _p7_same_filing(stem, xml_stem):
    a, b = os.path.splitext(str(stem).strip().lower())[0], xml_stem.lower()
    return a == b or b.endswith("_" + a) or b.endswith("-" + a)


def owner_placeholder_notes(output_dir: str, data_dirs: list[str]) -> list[str]:
    refs = _p7_xml_refs(data_dirs)
    if not refs:
        return []
    found = {}
    for fp, field, val, stem in _p7_values(output_dir):
        if not _P7_PLACEHOLDER.match(val or ""):
            continue
        hits = tuple((k[0], tuple((r, t, tuple(rows)) for r, t, rows in v)) for k, v in refs.items()
                     if k[1] == val.strip().lower() and (stem is None or _p7_same_filing(stem, k[0])))
        if hits:
            where = found.setdefault((val.strip(), hits), [])
            if (os.path.relpath(fp, output_dir), field) not in where:
                where.append((os.path.relpath(fp, output_dir), field))
    out = []
    for (val, hits), where in list(found.items())[:2]:
        lines = [f"Output check: \"{val}\" is written as an owner value in " +
                 ", ".join(f"{f} `{c}`" for f, c in where[:6]) + (f" and {len(where) - 6} more" if len(where) > 6 else "") +
                 ". In the input, the rows whose natureOfOwnership is this text point to footnotes, so the owner of each "
                 "such row is written in the footnote it points to:"]
        for xml_stem, lst in hits:
            for ref, text, rows in lst:
                lines.append(f"  {xml_stem}.xml rows {', '.join(map(str, rows))} -> {ref}: {text}")
        fields = ", ".join(dict.fromkeys(f"`{c}`" for _, c in where))
        refs_shown = ", ".join(dict.fromkeys(ref for _, lst in hits for ref, _, _ in lst))
        one = fields.count("`") == 2
        lines.append(f"{fields} {'itself still holds' if one else 'still hold'} the placeholder \"{val}\"; the owner of these "
                     f"rows is the one described in the footnote each row points to ({refs_shown}), so "
                     f"{'this field' if one else 'these fields'} (not a separate column) should identify that owner. Only the rows "
                     "holding the placeholder change: a row whose nature of ownership already names its holder (for "
                     "example \"By X Trust\") keeps that value, even when it also points to a footnote, because "
                     "different indirect holdings stay on separate lines.")
        lines.append("The reference sits at ownershipNature/natureOfOwnership/footnoteId/@id of each transaction or holding "
                     "element; the same element also has footnoteId children elsewhere (price, transaction coding) that "
                     "point to other footnotes, so `.//footnoteId` or ownershipNature/footnoteId picks the wrong one or "
                     "none. For example: `ref = row.find('ownershipNature/natureOfOwnership/footnoteId'); "
                     "fid = ref.get('id') if ref is not None else None; text = root.find(f\"footnotes/footnote[@id='{fid}']\").text`, "
                     "with `row` the nonDerivativeTransaction or nonDerivativeHolding element and `root` the "
                     "ownershipDocument element.")
        out.append("\n".join(lines))
    return out



_D2_SUFFIX = re.compile(r"['`\"](_{1,2}[A-Za-z][A-Za-z0-9]*)['`\"]")
_D2_ARITH = re.compile(r"\b(difference|less|minus|subtract\w*|sum|plus|ratio|divided|change between)\b|[−-]\s*[A-Z]\b", re.I)
_D2_SCHEMA_KEY = re.compile(r'"([^"\n]{2,200})"\s*:')
_D2_MINUS = re.compile(r"^(?P<a>.+?)_(?P<op>minus|plus|over|div|times)_(?P<b>.+)$")


def _d2_derived_suffixes(statement):
    out = {}
    for para in re.split(r"\n\s*\n", statement):
        sufs = list(dict.fromkeys(_D2_SUFFIX.findall(para)))
        if len(sufs) < 3:
            continue
        flat = " ".join(para.split())
        marks = [(m.start(), m.end(), m.group(1)) for m in _D2_SUFFIX.finditer(flat)]
        for k, (a, b, s) in enumerate(marks):
            stop = marks[k + 1][0] if k + 1 < len(marks) else len(flat)
            seg = flat[b: min(stop, b + 160)]
            if _D2_ARITH.search(seg):
                start = max(flat.rfind(". ", 0, a) + 2, 0)
                out.setdefault(s, ([x for x in sufs if x != s], flat[start: b + 160].strip()))
    return out


def _d2_num(v):
    return _is_num(v)


def derived_missing_notes(output_dir: str, statement: str) -> list[str]:
    if not statement:
        return []
    derived = _d2_derived_suffixes(statement)
    schema = set(_D2_SCHEMA_KEY.findall(statement))
    out = []
    for fp in _out_files(output_dir, ".json"):
        try:
            obj = json.load(open(fp))
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        rel = os.path.relpath(fp, output_dir)
        empty = []
        for s, (ops, sent) in derived.items():
            stems = {k[: -len(s)] for k in schema if k.endswith(s)}
            for stem in sorted(stems):
                vals = [obj.get(stem + o) for o in ops if stem + o in obj or stem + o in schema]
                nums = [v for v in vals if _d2_num(v)]
                if len(nums) >= 2 and obj.get(stem + s) is None:
                    empty.append((stem + s, "absent" if stem + s not in obj else "null", sent))
        for k, v in obj.items():
            m = _D2_MINUS.match(k)
            if m and v is None and _d2_num(obj.get(m.group("a"))) and _d2_num(obj.get(m.group("b"))):
                empty.append((k, "null", f"`{k}` = `{m.group('a')}` {m.group('op')} `{m.group('b')}`"))
        if empty:
            names = ", ".join(f"`{k}` ({how})" for k, how, _ in empty[:6])
            more = f" and {len(empty) - 6} more" if len(empty) > 6 else ""
            out.append(f"Output check: {rel}: {names}{more} are empty although both values they are defined from are "
                       f"written. The task defines them as: \"{empty[0][2][:240]}\". Compute each from its two written "
                       "operands and write it.")
    return out[:2]



_C8_REPR = re.compile(r"(?:\bdtype: \w+|\bName: [^,\n]{0,80}, dtype|\bLength: \d+, dtype|\[\d+ rows x \d+ columns\])")


def csv_shape_notes(output_dir: str) -> list[str]:
    out = []
    for fp in _out_files(output_dir, ".csv"):
        try:
            hdr, rows = _csv_rows(fp, 5000)
        except Exception:
            continue
        rel = os.path.relpath(fp, output_dir)
        dup = sorted({h for h in hdr if hdr.count(h) > 1})
        if dup:
            out.append(f"Output check: {rel}: the header repeats column {', '.join(f'`{h}`' for h in dup[:3])}. Two columns "
                       "with one name usually come from concatenating frames that both carry it; keep one column per name "
                       "with the values the task defines.")
        hit = next(((hdr[j] if j < len(hdr) else f"column {j + 1}", c) for r in rows for j, c in enumerate(r)
                    if _C8_REPR.search(c)), None)
        if hit:
            sample = " ".join(hit[1].split())[:120]
            out.append(f"Output check: {rel}: column `{hit[0]}` holds the printed form of a pandas object, for example "
                       f"\"{sample}\". A cell was given a whole Series or DataFrame instead of one value; select the scalar "
                       "(for example with .iloc[0] or .item()) before writing.")
    return out[:2]



_C9_SEL = re.compile(r"(?:^|_)(selected|best|chosen|winning)(?:_|$)", re.I)


def _c9_bad(v):
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip().lower() in ("", "nan", "inf", "-inf", "infinity", "-infinity", "none", "null")
    return isinstance(v, float) and not math.isfinite(v)


def selected_param_notes(output_dir: str) -> list[str]:
    out = []
    for fp in _out_files(output_dir, ".csv"):
        try:
            hdr, rows = _csv_rows(fp)
        except Exception:
            continue
        sel = [j for j, h in enumerate(hdr) if _C9_SEL.search(h)]
        if not sel:
            continue
        bad, total, first = 0, 0, None
        for n, r in enumerate(rows):
            for j in sel:
                x = r[j].strip().lower() if j < len(r) else ""
                if not x:
                    continue
                cols = [k for k, h in enumerate(hdr) if h.lower().startswith(x + "_")]
                if len(cols) < 2:
                    continue
                vals = {hdr[k]: (r[k] if k < len(r) else "") for k in cols}
                good = [h for h, v in vals.items() if not _c9_bad(v)]
                missing = [h for h, v in vals.items() if _c9_bad(v)]
                if x and good:
                    total += 1
                if good and missing:
                    bad += 1
                    if first is None:
                        first = (n + 1, x, missing, good)
        if first:
            n, x, missing, good = first
            out.append(f"Output check: {os.path.relpath(fp, output_dir)}: on {bad} of {total} rows the selected model is "
                       f"`{x}` while its parameter {', '.join(f'`{m}`' for m in missing[:3])} is empty or not finite "
                       f"(row {n}; `{good[0]}` is set). A candidate whose parameters could not be estimated should not take "
                       "part in the selection; exclude it when its estimate is invalid (for example a mean-reversion map "
                       "that needs a log of a non-positive coefficient) and select among the valid candidates.")
    for fp in _out_files(output_dir, ".json"):
        try:
            leaves = []
            _json_leaves(json.load(open(fp)), [], leaves)
        except Exception:
            continue
        for path, name, v in leaves:
            parts = path.split(".")
            if any(_C9_SEL.search(p) for p in parts[:-1]) and isinstance(v, float) and not math.isfinite(v):
                out.append(f"Output check: {os.path.relpath(fp, output_dir)} `{path}` = {v} inside the selected model. A "
                           "selected model must have finite parameters; exclude candidates whose estimates are invalid "
                           "before selecting.")
                break
    return out[:2]


_C9_NEGLOG = re.compile(r"-\s*(?:np|numpy|math)\.log\(\s*([A-Za-z_]\w*)\s*\)")


def neglog_names(code: str) -> list[str]:
    return list(dict.fromkeys(_C9_NEGLOG.findall(code)))


def neglog_probe(names: list[str]) -> str:
    return ("import numpy as _c9n\nfor _c9k in %r:\n    try:\n        _c9v = _c9n.asarray(globals()[_c9k], dtype=float)\n"
            "        if (_c9v <= 0).any(): print('C9NEG', _c9k, float(_c9v.min()))\n    except Exception:\n        pass" % names)



_C10_NAME = re.compile(r"(?:^|_)(start|initial|init|opening|beginning|at_start|begin)(?:_|$)", re.I)
_C10_VALUE = re.compile(r"(?:^|_)(cash|value|wealth|capital|price|prices|nav|balance|equity|position|positions|holdings|"
                        r"notional|pv|level|inventory|exposure)(?:_|$)", re.I)
_C10_WRITE = re.compile(r"\.to_csv\(|\.to_parquet\(|json\.dump\(|\.write_text\(|open\([^)]*['\"]w")


def unused_start_names(code: str, later: str = "", require_write: bool = False) -> list[tuple[str, str]]:
    import ast
    if require_write and not _C10_WRITE.search(code):
        return []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    assigned = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for x in ast.walk(t):
                    if isinstance(x, ast.Name) and _C10_NAME.search(x.id) and _C10_VALUE.search(x.id):
                        src = ast.get_source_segment(code, node) or ""
                        if re.search(r"=\s*(?:params|config|cfg|settings)\b|=\s*-?[\d.]+\s*(?:#|$)", src):
                            continue
                        assigned.setdefault(x.id, node.lineno)
    if not assigned:
        return []
    loads = {x.id for x in ast.walk(tree) if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load)}
    out = []
    lines = code.splitlines()
    for name, ln in assigned.items():
        if name in loads or re.search(r"\b%s\b" % re.escape(name), later):
            continue
        out.append((name, lines[ln - 1].strip() if 0 < ln <= len(lines) else name))
    return out


def unused_start_note(name: str, line: str) -> str:
    return (f"Code note: `{line}` defines `{name}` in this cell, but nothing in this cell or later reads it. A value "
            "taken at the start of a period is usually needed by a later formula (a return, a drawdown, a capacity or "
            "cash measure); check whether the formula that should use it uses something else instead.")
