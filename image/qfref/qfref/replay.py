import collections, csv, difflib, itertools, json, re, sys
from pathlib import Path
from common import (RAW, UNITS, OUT, list_runs, verdict, exit_info, steps, instruction, in_text, json_keys,
                    input_names, is_instance)
from abbrev import toks, initials, COMMON, GENERIC

sys.path.insert(0, str(OUT.parent / "key_names"))
from file_sections import segments, FILE_RE
from extract import instr_index

PAIRS = json.load(open(OUT / "abbrev_pairs.json"))
GROUPS = ["G0_orig", "G1_full", "G2_initials", "G3_both", "G4_terms"]
GENERIC_TEST = {"test", "is", "has", "are", "the", "of", "and", "in", "exists", "valid", "file", "json", "csv",
                "values", "value", "keys", "key", "columns", "column", "output", "outputs", "correct", "match"}


def sing(t):
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def canon(name):
    return tuple(sing(t) for t in toks(name))


def build_tables(term_only):
    a2f, f2a = collections.defaultdict(set), collections.defaultdict(set)
    for p in PAIRS:
        if term_only and not p["term"]:
            continue
        a2f[p["abbr"]].add(tuple(p["full"].split("_")))
        f2a[tuple(sing(w) for w in p["full"].split("_"))].add(p["abbr"])
    return a2f, f2a


BROAD, TERM = build_tables(False), build_tables(True)


def full_forms(tk, table):
    a2f, _ = table
    alts = [[(t,)] + sorted(a2f.get(t, ())) for t in tk]
    out = set()
    for combo in itertools.islice(itertools.product(*alts), 64):
        out.add(tuple(sing(w) for part in combo for w in part))
    out.discard(tuple(sing(t) for t in tk))
    return out


def contract_forms(tk, table):
    _, f2a = table
    base = [sing(t) for t in tk]
    out = set()
    for L in range(min(5, len(base)), 0, -1):
        for i in range(len(base) - L + 1):
            ph = tuple(base[i:i + L])
            for ab in f2a.get(ph, ()):
                out.add(tuple(base[:i] + [ab] + base[i + L:]))
    out.discard(tuple(base))
    return out


def forms(name):
    tk = toks(name)
    orig = canon(name)
    full = full_forms(tk, BROAD)
    contr = contract_forms(tk, BROAD)
    if len(tk) >= 2:
        contr.add((initials(tk),))
    term = full_forms(tk, TERM) | contract_forms(tk, TERM)
    return {"G0_orig": {orig}, "G1_full": {orig} | full, "G2_initials": {orig} | contr,
            "G3_both": {orig} | full | contr, "G4_terms": {orig} | term}


class Pool:
    def __init__(self, items):
        self.items = items
        self.by_canon = collections.defaultdict(list)
        self.by_minus = collections.defaultdict(list)
        self.by_set = collections.defaultdict(list)
        for it in items:
            c = canon(it[0])
            if not c:
                continue
            self.by_canon[c].append(it)
            s = frozenset(c)
            self.by_set[s].append(it)
            if len(s) >= 2:
                for t in s:
                    self.by_minus[s - {t}].append(it)
        self.joined = [("_".join(canon(it[0])), it) for it in items]

    def match(self, f):
        res = []
        for it in self.by_canon.get(f, ()):
            res.append((it, "norm_eq"))
        s = frozenset(f)
        cont = []
        if len(s) >= 1:
            cont += self.by_minus.get(s, [])
        if len(s) >= 2:
            for t in s:
                cont += self.by_set.get(s - {t}, [])
        for it in cont:
            res.append((it, "contain1"))
        j = "_".join(f)
        for jb, it in self.joined:
            if abs(len(jb) - len(j)) <= 2 and jb[:1] == j[:1] and jb != j:
                sm = difflib.SequenceMatcher(None, j, jb)
                if sm.real_quick_ratio() >= 0.9 and sm.quick_ratio() >= 0.9 and sm.ratio() >= 0.9:
                    res.append((it, "spell"))
        return res


TASK_CACHE = {}


def seg_names(seg):
    names = set()
    spans = re.findall(r"`([^`\n]+)`", seg) + re.findall(r"```.*?```", seg, re.S)
    spans += re.findall(r"\"([A-Za-z_][A-Za-z0-9_ ]*)\"\s*:", seg)
    for m in re.finditer(r"(?i)\b(?:columns?|keys?|fields?|headers?)\b[^:\n]{0,40}:\s*([^\n]+)", seg):
        spans.append(m.group(1))
    for l in seg.splitlines():
        if re.fullmatch(r"(?: {4,}|\t)[A-Za-z0-9_,./\- ]+", l):
            spans.append(l)
    for sp in spans:
        for x in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", sp):
            if not FILE_RE.fullmatch(x):
                names.add(x)
    return names


def task_ctx(task, delivered):
    if task in TASK_CACHE:
        return TASK_CACHE[task]
    text = instruction(task)
    low = text.lower()
    lines = text.splitlines()
    mentioned = {f for f in set(FILE_RE.findall(text)) if f in delivered}
    attrib = collections.defaultdict(set)
    for f in mentioned:
        for seg in segments(lines, f, mentioned):
            for n in seg_names(seg):
                attrib[n].add(f)
    names, values, template = input_names(task)
    templates = instr_index(text)[2]
    ctx = {"text": text, "low": low, "templates": templates, "attrib": attrib, "inputs": names, "values": values, "template": template}
    TASK_CACHE[task] = ctx
    return ctx


def output_names(run, values):
    res = collections.defaultdict(set)
    od = run / "output"
    if not od.exists():
        return res
    for f in sorted(od.rglob("*")):
        rel = f.name
        try:
            if f.suffix == ".json":
                for _, k, _ in json_keys(json.loads(f.read_text(errors="ignore"))):
                    res[rel].add(k)
            elif f.suffix == ".csv":
                with open(f, errors="ignore", newline="") as fh:
                    res[rel].update(next(csv.reader(fh), []))
        except Exception:
            continue
    return {k: {n for n in v if n and len(n) <= 60 and not is_instance(n, values)} for k, v in res.items()}


def test_tokens(failed):
    return [set(toks(t)) for t in failed]


def maps_to(failed_tok, fname, names):
    stem = [sing(t) for t in toks(Path(fname).stem) if t not in GENERIC_TEST]
    ft = [{sing(t) for t in tt} for tt in failed_tok]
    file_hit = any(stem and set(stem) <= tt for tt in ft)
    key_hit = False
    for n in names:
        nt = [sing(t) for t in toks(n) if t not in GENERIC_TEST]
        if nt and any(set(nt) <= tt for tt in ft):
            key_hit = True
    return file_hit, key_hit


def named_by_task(a, ctx):
    return in_text(a, ctx["low"]) or any(t.match(a.lower()) for t in ctx["templates"])


def consistency(run, task, ctx, verdict_, failed, onames, stress=False):
    flags = []
    ftok = test_tokens(failed)
    low = ctx["low"]
    eligible = []
    for F, names in onames.items():
        eligible += [(F, a) for a in sorted(names) if not named_by_task(a, ctx) and re.search(r"[A-Za-z]", a)]
        other_task = [(b, "task_other_file", ",".join(sorted(fs))) for b, fs in ctx["attrib"].items() if F not in fs]
        tmpl = [(b, "template", "template.py") for b in ctx["template"]]
        model_other = [(b, "model_other_file", G) for G, ns in onames.items() if G != F for b in ns
                       if F not in ctx["attrib"].get(b, set())]
        pool2 = Pool([x for x in other_task + tmpl + model_other if x[0] not in names])
        pool3 = Pool([(b, "input", src) for b, src in ctx["inputs"].items() if b not in names])
        for a in sorted(names):
            if (named_by_task(a, ctx) and not stress) or not re.search(r"[A-Za-z]", a):
                continue
            fm = forms(a)
            for kind, pool in (("V2", pool2), ("V3", pool3)):
                if kind == "V3" and a in ctx["inputs"]:
                    continue
                hits = collections.defaultdict(set)
                orig = set(canon(a))
                for g in GROUPS:
                    for f in fm[g]:
                        introduced = set(f) - orig
                        for it, cat in pool.match(f):
                            if it[0] == a:
                                continue
                            if cat == "contain1":
                                shared = set(f) & set(canon(it[0]))
                                cb = canon(it[0])
                                if introduced & shared:
                                    if len(cb) == 1 and (cb[0] in COMMON or cb[0] in GENERIC):
                                        continue
                                    cat = "term_swap"
                                elif not any(len(x) >= 3 for x in shared):
                                    continue
                            hits[(it[0], it[1], it[2], cat)].add(g)
                if not hits:
                    continue
                fh, kh = maps_to(ftok, F, [a] + [h[0] for h in hits]) if verdict_ == "FAIL" else (False, False)
                flags.append({"check": kind, "file": F, "name": a, "file_hit": fh, "key_hit": kh,
                              "matches": [{"other": h[0], "source": h[1], "where": h[2], "cat": h[3], "groups": sorted(gs)}
                                          for h, gs in sorted(hits.items())]})
    return flags, eligible


KE_RE = re.compile(r"^KeyError: (.+)$", re.M)


def keyerror_names(out):
    names, other = set(), 0
    for m in KE_RE.finditer(out or ""):
        v = m.group(1).strip()
        if re.search(r"not in index|None of|do not exist|not found", v):
            inner = re.findall(r"'([^'\n]{1,80})'", v)
            names.update(inner)
            if not inner:
                other += 1
        elif re.fullmatch(r"'[^'\n]{1,80}'|\"[^\"\n]{1,80}\"", v):
            names.add(v[1:-1])
        else:
            other += 1
    return {n for n in names if re.search(r"[A-Za-z]", n) and not re.fullmatch(r"\d{4}-\d{2}.*", n)}, other


def printed_names(out):
    res = set()
    for blob in re.findall(r"Index\(\[(.*?)\]", out or "", re.S) + re.findall(r"dict_keys\(\[(.*?)\]\)", out or "", re.S) \
            + re.findall(r"Columns: \[(.*?)\]", out or "", re.S):
        res.update(re.findall(r"'([^'\n]{1,80})'", blob[:20000]))
    res.update(re.findall(r"^\s*\d+\s+(\S+)\s+\d+\s+non-null", out or "", re.M))
    for blob in re.findall(r"\[((?:'[^'\n]{1,60}',\s*){2,}'[^'\n]{1,60}')\]", out or ""):
        res.update(re.findall(r"'([^'\n]{1,60})'", blob))
    return res


def code_keys(code):
    res = set(re.findall(r"\[\s*['\"]([^'\"\n]{1,60})['\"]\s*\]", code))
    res.update(re.findall(r"['\"]([A-Za-z_][A-Za-z0-9_ \-./%]{0,60})['\"]\s*:", code))
    res.update(re.findall(r"\.get\(\s*['\"]([^'\"\n]{1,60})['\"]", code))
    return res


def sim_score(a, b):
    ta, tb = set(toks(a)), set(toks(b))
    if canon(a) == canon(b):
        return 1.0
    c = len(ta & tb) / min(len(ta), len(tb)) if ta and tb else 0.0
    r = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
    return 0.5 * c + 0.5 * r


def suggest(n, pool):
    sc = sorted(((sim_score(n, b), b, src) for b, src in pool.items() if b != n), key=lambda x: (-x[0], x[1]))
    return [(round(s, 3), b, src) for s, b, src in sc if s >= 0.5][:3]


def offending_line(code, n):
    for l in code.splitlines():
        if f"'{n}'" in l or f'"{n}"' in l:
            return l.strip()
    return None


def best_line(code, L):
    best, bl = 0.0, None
    for l in code.splitlines():
        r = difflib.SequenceMatcher(None, l.strip(), L).ratio()
        if r > best:
            best, bl = r, l.strip()
    return best, bl


def v1(run, task, ctx, st):
    trig, episodes = [], []
    pool = {b: "input_file" for b in ctx["inputs"]}
    seen = set()
    for i, s in enumerate(st):
        names, _ = keyerror_names(s["out"])
        cur_pool = dict(pool)
        for b in code_keys(s["code"]):
            cur_pool.setdefault(b, "code_literal")
        for n in sorted(names):
            sug = suggest(n, cur_pool)
            trig.append({"req": s["req"], "msg": s["msg"], "tool_msg": s["tool_msg"], "name": n,
                         "in_task_text": in_text(n, ctx["low"]), "suggest": sug})
            if n in seen:
                continue
            seen.add(n)
            L = offending_line(s["code"], n)
            fix, weak, repl, rounds_ke = None, None, None, 1
            for s2 in st[i + 1:]:
                if s2["out"] is None:
                    continue
                n2, _ = keyerror_names(s2["out"])
                if n in n2:
                    rounds_ke += 1
                    continue
                if weak is None and s2["rc"] == 0:
                    weak = s2["req"]
                if L is None:
                    continue
                r, bl = best_line(s2["code"], L)
                if r >= 0.6 or f"'{n}'" in s2["code"] or f'"{n}"' in s2["code"]:
                    fix = s2["req"]
                    if bl and r >= 0.6:
                        new = set(re.findall(r"['\"]([^'\"\n]{1,80})['\"]", bl)) - set(re.findall(r"['\"]([^'\"\n]{1,80})['\"]", L))
                        repl = sorted(new) if new else ([n] if n in bl else [])
                    break
            note = re.findall(r"^Similar names in this object: (.+)$", s["out"] or "", re.M)
            note_names = re.findall(r"'([^'\n]+)'", note[-1]) if note else []
            episodes.append({"existing_note": bool(note), "note_names": note_names,
                             "note_correct": bool(repl and any(x in repl for x in note_names)) if fix else False,
                             "name": n, "req": s["req"], "msg": s["msg"], "tool_msg": s["tool_msg"],
                             "in_task_text": in_text(n, ctx["low"]), "offending_line": L, "fix_req": fix,
                             "weak_fix_req": weak, "replacement": repl, "keyerror_rounds": rounds_ke,
                             "suggest": sug, "hint_correct": bool(repl and any(x[1] in repl for x in sug))})
        if s["out"]:
            for b in printed_names(s["out"]):
                pool.setdefault(b, "printed")
        for b in code_keys(s["code"]):
            pool.setdefault(b, "code_literal")
    return trig, episodes


def main():
    runs = list_runs()
    delivered = collections.defaultdict(set)
    for (b, t), p in runs.items():
        if (p / "output").exists():
            delivered[t].update(x.name for x in (p / "output").rglob("*") if x.suffix in (".json", ".csv"))
    detail = []
    for (b, t), p in sorted(runs.items()):
        if not (UNITS / t / "instruction.md").exists():
            continue
        ctx = task_ctx(t, delivered[t])
        v, failed = verdict(p)
        st, _ = steps(p)
        onames = output_names(p, ctx["values"])
        trig, eps = v1(p, t, ctx, st)
        flags, eligible = consistency(p, t, ctx, v, failed, onames)
        stress, _ = consistency(p, t, ctx, v, failed, onames, stress=True)
        stress = [{"check": f["check"], "file": f["file"], "name": f["name"], "file_hit": f["file_hit"], "key_hit": f["key_hit"],
                   "gc": sorted({f"{g}|{m['cat']}" for m in f["matches"] for g in m["groups"]}),
                   "ex": [(m["other"], m["source"], m["cat"]) for m in f["matches"] if m["cat"] != "contain1"][:4]} for f in stress]
        detail.append({"batch": b, "task": t, "path": str(p.relative_to(RAW)), "verdict": v, "exit": exit_info(p),
                       "n_requests": len(st), "failed_tests": failed, "v1_triggers": trig, "v1_episodes": eps,
                       "flags": flags, "stress_flags": stress, "eligible": eligible, "n_output_names": sum(len(x) for x in onames.values())})
    with open(OUT / "replay_detail.jsonl", "w") as fh:
        for d in detail:
            fh.write(json.dumps(d) + "\n")
    print(len(detail))


if __name__ == "__main__":
    main()
