import collections, os, re, sys
from pathlib import Path

KN = os.environ.get("KEY_NAMES_V2_DIR", "/Users/Agenthon/fca-mini-swe/mini-swe/analysis/v212-90pct/research_1026/key_names_v2")
sys.path.insert(0, KN)
import common
import replay as kn

CATS = {"norm_eq", "term_swap"}


def _ctx(statement: str, data_dir: str, delivered: set):
    low = statement.lower()
    lines = statement.splitlines()
    mentioned = {f for f in set(kn.FILE_RE.findall(statement)) if f in delivered}
    attrib = collections.defaultdict(set)
    for f in mentioned:
        for seg in kn.segments(lines, f, mentioned):
            for n in kn.seg_names(seg):
                attrib[n].add(f)
    p = Path(data_dir)
    common.UNITS = p.parents[2] if len(p.parents) > 2 else p.parent
    names, values, template = common.input_names(p.parents[1].name if len(p.parents) > 1 else p.name)
    return {"text": statement, "low": low, "templates": kn.instr_index(statement)[2], "attrib": attrib, "inputs": names,
            "values": values, "template": template}


def key_name_sites(output_dir: str, statement: str, data_dir: str) -> list[dict]:
    onames = kn.output_names(Path(output_dir).parent, set())
    delivered = set(onames)
    ctx = _ctx(statement, data_dir, delivered)
    onames = {F: {n for n in ns if not common.is_instance(n, ctx["values"])} for F, ns in onames.items()}
    sites = []
    for F, names in onames.items():
        other_task = [(b, "task_other_file", ",".join(sorted(fs))) for b, fs in ctx["attrib"].items() if F not in fs]
        tmpl = [(b, "template", "template.py") for b in ctx["template"]]
        model_other = [(b, "model_other_file", G) for G, ns in onames.items() if G != F for b in ns
                       if F not in ctx["attrib"].get(b, set())]
        pool = kn.Pool([x for x in other_task + tmpl + model_other if x[0] not in names])
        for a in sorted(names):
            if kn.named_by_task(a, ctx) or not re.search(r"[A-Za-z]", a):
                continue
            orig = kn.canon(a)
            for f in sorted(kn.forms(a)["G4_terms"] - {orig}):
                introduced = set(f) - set(orig)
                hit = None
                for it, cat in pool.match(f):
                    if it[0] == a:
                        continue
                    if cat == "contain1":
                        cb = kn.canon(it[0])
                        if not (introduced & (set(f) & set(cb))) or (len(cb) == 1 and (cb[0] in kn.COMMON or cb[0] in kn.GENERIC)):
                            continue
                        cat = "term_swap"
                    if cat in CATS:
                        hit = (it, cat)
                        break
                if hit:
                    removed = [t for t in orig if t not in f]
                    added = [t for t in f if t not in orig]
                    sites.append({"file": F, "key": a, "target": "_".join(f), "other": hit[0][0], "source": hit[0][1],
                                  "where": hit[0][2], "cat": hit[1], "long": "_".join(removed), "short": "_".join(added)})
                    break
    return sites


def key_name_note(site: dict, output_dir: str) -> str:
    F, a, t = site["file"], site["key"], site["target"]
    where = (f"the task's names for {site['where'].replace(',', ', ')}" if site["source"] == "task_other_file"
             else site["where"] if site["source"] == "model_other_file" else "the supplied template")
    path = os.path.join(output_dir, F)
    if F.endswith(".csv"):
        code = (f"import pandas as pd; p = {path!r}\n"
                f"pd.read_csv(p).rename(columns={{{a!r}: {t!r}}}).to_csv(p, index=False)")
    else:
        code = (f"import json; p = {path!r}\n"
                f"def _rn(o): return {{({t!r} if k == {a!r} else k): _rn(v) for k, v in o.items()}} if isinstance(o, dict) "
                f"else [_rn(x) for x in o] if isinstance(o, list) else o\n"
                f"d = _rn(json.load(open(p))); json.dump(d, open(p, 'w'), indent=2)")
    return (f"In your next cell change only this one key name; leave every value and every other file as it is. {F} stores "
            f"'{a}', while {where} write the same statistic as '{site['other']}'; '{site['long']}' and '{site['short']}' "
            f"are the long and short spelling of one term, so the matching key here is '{t}'. Run:\n{code}")
