import csv, json, os, re, sys
from pathlib import Path

RAW = Path("/Users/Agenthon/fca-mini-swe/mini-swe/trajectories/raw")
BATCHES = [f"rag13zv212oc{v}-full-{i}" for v in (7, 9, 10) for i in (1, 2)]
OUT = Path(__file__).parent

DATE_RE = re.compile(r"^\d{4}[-/]?\d{2}([-/]?\d{2})?([ T].*)?$")
NUM_RE = re.compile(r"^[-+]?\d+(\.\d+)?([eE][-+]?\d+)?%?$")


def norm(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def verdict(run):
    lines = (run / "grader_output.txt").read_text(errors="ignore").strip().splitlines()
    last = lines[-1] if lines else ""
    ok = "passed" in last and "failed" not in last and "error" not in last
    failed = [l.split("::", 1)[1].split(" ")[0] for l in lines if l.startswith("FAILED ") and "::" in l]
    return ("PASS" if ok else "FAIL"), failed


def instr_index(text):
    low = text.lower()
    spans = re.findall(r"```.*?```", text, re.S) + re.findall(r"`([^`\n]+)`", text)
    spans += re.findall(r"\"([^\"\n]{1,80})\"", text) + re.findall(r"'([^'\n]{1,60})'", text)
    spans += [c for c in re.findall(r"\|([^|\n]+)", text) if re.fullmatch(r"\s*`?[A-Za-z0-9_./%-]+`?\s*", c)]
    spans += [l for l in text.splitlines() if re.fullmatch(r"(?: {4,}|\t)[A-Za-z0-9_,./\- ]+", l) and ("," in l or " " not in l.strip())]
    for m in re.finditer(r"(?i)\b(?:columns?|keys?|fields?|headers?)\b[^:\n]{0,40}:\s*([^\n]+)", text):
        spans += [re.sub(r"\(.*?\)", "", x).strip(" .*") for x in m.group(1).split(",")]
    for m in re.finditer(r":\s*((?:[A-Za-z0-9_./%-]{1,30}\s*,\s*){2,}[A-Za-z0-9_./%-]{1,30})", text):
        spans += [x.strip() for x in m.group(1).split(",")]
    code_tok = set()
    code_str = set()
    for sp in spans:
        code_tok.update(t.lower() for t in re.findall(r"[A-Za-z0-9_]+", sp))
        code_str.add(norm(sp))
    templates = []
    for m in re.finditer(r"[A-Za-z0-9_]*(?:(?:\{[^}\s]{1,40}\}|<[A-Za-z_]{1,30}>)[A-Za-z0-9_]*)+", text):
        tok = m.group(0)
        rx = ""
        for part in re.split(r"(\{[^}]+\}|<[^>]+>)", tok):
            if not part:
                continue
            if part[0] in "{<":
                inner = part[1:-1]
                rx += "(" + "|".join(re.escape(x.strip().lower()) for x in inner.split(",")) + ")" if "," in inner else r"[a-z0-9_.\-]+"
            else:
                rx += re.escape(part.lower())
        if re.search(r"[a-z]", re.sub(r"\{[^}]*\}|<[^>]*>", "", tok.lower())):
            templates.append(re.compile("^" + rx + "$"))
    idents = set(re.findall(r"[a-z0-9_]+", low))
    phrase = " " + re.sub(r"[^a-z0-9]+", " ", low) + " "
    return code_tok, code_str, templates, idents, phrase


def in_instr(key, idx):
    code_tok, code_str, templates, idents, phrase = idx
    nk = norm(key)
    if not nk:
        return "empty"
    if key.lower() in code_tok or nk in code_tok or nk in code_str:
        return "code"
    if any(t.match(key.lower()) or t.match(nk) for t in templates):
        return "template"
    if "_" in key and key.lower() in idents:
        return "code"
    if key.lower() in idents or nk in idents or " " + nk.replace("_", " ") + " " in phrase:
        return "prose"
    return "no"


def key_kind(key, data_values):
    k = key.strip()
    if NUM_RE.match(k) or DATE_RE.match(k):
        return "data"
    if k in data_values:
        return "data"
    return "name"


def json_keys(obj, path="", depth=0, out=None):
    if out is None:
        out = []
    if isinstance(obj, dict):
        sib = list(obj.keys())
        for k, v in obj.items():
            out.append((path, str(k), depth, sib))
            json_keys(v, f"{path}/{k}", depth + 1, out)
    elif isinstance(obj, list):
        for v in obj[:50]:
            json_keys(v, f"{path}[]", depth, out)
    return out


def input_names(task_dir):
    names, values = set(), set()
    d = task_dir / "staged" / "environment" / "data"
    if not d.exists():
        return names, values
    for f in d.rglob("*"):
        if f.suffix.lower() in (".csv", ".tsv"):
            try:
                with open(f, errors="ignore", newline="") as fh:
                    r = csv.reader(fh, delimiter="\t" if f.suffix.lower() == ".tsv" else ",")
                    hdr = next(r, [])
                    names.update(h.strip() for h in hdr if h.strip())
                    for i, row in enumerate(r):
                        if i > 2000:
                            break
                        for c in row[:6]:
                            if c and not NUM_RE.match(c) and len(c) < 30:
                                values.add(c.strip())
            except Exception:
                pass
        elif f.suffix.lower() == ".json" and f.stat().st_size < 20_000_000:
            try:
                obj = json.loads(f.read_text(errors="ignore"))
                for _, k, depth, _ in json_keys(obj):
                    if depth <= 2:
                        names.add(k)
            except Exception:
                pass
    return names, values


def output_keys(run):
    rows = []
    od = run / "output"
    if not od.exists():
        return rows
    for f in sorted(od.rglob("*")):
        rel = str(f.relative_to(od))
        if f.suffix == ".json":
            try:
                obj = json.loads(f.read_text(errors="ignore"))
            except Exception:
                continue
            seen = set()
            for path, k, depth, sib in json_keys(obj):
                if (path, k) in seen:
                    continue
                seen.add((path, k))
                rows.append((rel, path, k, depth, sib))
        elif f.suffix == ".csv":
            try:
                with open(f, errors="ignore", newline="") as fh:
                    hdr = next(csv.reader(fh), [])
            except Exception:
                continue
            for h in hdr:
                rows.append((rel, "", h, 0, hdr))
    return rows


def main():
    records = []
    tasks = {}
    for b in BATCHES:
        for run in sorted((RAW / b).glob("t1-*")):
            t = run.name
            if t not in tasks:
                text = (run / "staged" / "instruction.md").read_text(errors="ignore")
                names, values = input_names(run)
                tasks[t] = {"idx": instr_index(text), "inputs": sorted(names), "values": values}
            v, failed = verdict(run)
            for rel, path, k, depth, sib in output_keys(run):
                records.append({
                    "batch": b, "task": t, "verdict": v, "file": rel, "path": path, "key": k,
                    "depth": depth, "siblings": [s for s in sib if s != k][:40],
                    "in_instr": in_instr(k, tasks[t]["idx"]),
                    "kind": key_kind(k, tasks[t]["values"]),
                    "in_input": k in tasks[t]["inputs"],
                })
            records.append({"batch": b, "task": t, "verdict": v, "file": None, "failed_tests": failed})
    with open(OUT / "keys.jsonl", "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
    meta = {t: {"inputs": d["inputs"], "idents": sorted(d["idx"][0])} for t, d in tasks.items()}
    json.dump(meta, open(OUT / "task_meta.json", "w"))
    print(len(records), len(tasks))


if __name__ == "__main__":
    main()
