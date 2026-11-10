import json, re, collections
from pathlib import Path
from extract import RAW, BATCHES, OUT

FILE_RE = re.compile(r"[A-Za-z0-9_\-]+\.(?:json|csv)\b")
LIST_RE = re.compile(r"(?i)\b(?:columns?|keys?|fields?|headers?)\b[^:\n]{0,40}:\s*\S")
CSV_LIST_RE = re.compile(r"(?:[A-Za-z_][A-Za-z0-9_./%-]{0,30}\s*,\s*){2,}[A-Za-z_][A-Za-z0-9_./%-]{0,30}")
JSON_KEY_RE = re.compile(r"\"[A-Za-z_][A-Za-z0-9_ ]*\"\s*:")


def output_files(task):
    fs = set()
    for b in BATCHES:
        od = RAW / b / task / "output"
        if od.exists():
            fs.update(p.name for p in od.rglob("*") if p.suffix in (".json", ".csv"))
    return fs


def segments(lines, fname, outfiles):
    segs = []
    for i, l in enumerate(lines):
        if fname not in FILE_RE.findall(l):
            continue
        pos = l.find(fname)
        seg = [l[pos + len(fname):]]
        for l2 in lines[i + 1:]:
            if l2.lstrip().startswith("#") or any(f != fname and f in outfiles for f in FILE_RE.findall(l2)):
                if re.search(r"(?i)same (?:structure|format|layout|schema|columns) as", l2):
                    seg.append(l2)
                break
            seg.append(l2)
        segs.append("\n".join(seg))
    return segs


def has_names(seg):
    for sp in re.findall(r"`([^`\n]+)`", seg):
        if re.search(r"[A-Za-z_]", sp) and not FILE_RE.fullmatch(sp.strip()) and not sp.strip().startswith("/"):
            return "backtick"
    if "```" in seg or re.search(r"^(?: {4,}|\t)\S", seg, re.M) and CSV_LIST_RE.search(seg):
        return "code_block"
    if re.search(r"(?i)same (?:structure|format|layout|schema|columns) as", seg):
        return "same_as_reference"
    if re.search(r"\"[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)+\"", seg):
        return "quoted_key_pattern"
    if JSON_KEY_RE.search(seg):
        return "json_key"
    if LIST_RE.search(seg):
        return "column_list"
    if CSV_LIST_RE.search(seg):
        return "comma_list"
    return None


def main():
    rows = []
    tasks = sorted(p.name for p in (RAW / BATCHES[0]).glob("t1-*"))
    for t in tasks:
        text = (RAW / BATCHES[0] / t / "staged" / "instruction.md").read_text(errors="ignore")
        lines = text.splitlines()
        outs = output_files(t)
        mentioned = {f for f in set(FILE_RE.findall(text)) if f in outs}
        for f in sorted(mentioned):
            segs = segments(lines, f, mentioned)
            kinds = [has_names(s) for s in segs]
            rows.append({"task": t, "file": f, "n_mentions": len(segs), "evidence": sorted({k for k in kinds if k}),
                         "unnamed": not any(kinds), "first_segment": segs[0][:300] if segs else ""})
    json.dump(rows, open(OUT / "file_detection.json", "w"), indent=1)
    un = [r for r in rows if r["unnamed"]]
    print(f"tasks {len(tasks)}  output files mentioned {len(rows)}  unnamed {len(un)} in {len({r['task'] for r in un})} tasks")
    print(collections.Counter(e for r in rows for e in r["evidence"]))
    for r in un:
        print("UNNAMED", r["task"], r["file"], repr(r["first_segment"][:160]))


if __name__ == "__main__":
    main()
