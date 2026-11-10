import csv, json, os, re
from pathlib import Path

RAW = Path("/Users/Agenthon/fca-mini-swe/mini-swe/trajectories/raw")
UNITS = Path("/Users/Agenthon/fca-mini-swe/mini-swe/agenthon_units")
OUT = Path(__file__).parent

NUM_RE = re.compile(r"^[-+]?\d+(\.\d+)?([eE][-+]?\d+)?%?$")
DATE_RE = re.compile(r"^\d{4}[-/]?\d{2}([-/]?\d{2})?([ T].*)?$")


def list_runs():
    batches = [b for b in sorted(os.listdir(RAW)) if b.startswith("rag13") and re.search(r"full|final", b)]
    runs = {}
    for b in batches:
        base = b.replace("-r429", "")
        for t in sorted(os.listdir(RAW / b)):
            p = RAW / b / t
            if not t.startswith("t1-") or not (p / "trace" / "mini.traj.json").exists():
                continue
            if (base, t) in runs and "-r429" not in b:
                continue
            runs[(base, t)] = p
    return runs


def verdict(run):
    lines = (run / "grader_output.txt").read_text(errors="ignore").strip().splitlines() if (run / "grader_output.txt").exists() else []
    last = lines[-1] if lines else ""
    ok = "passed" in last and "failed" not in last and "error" not in last
    failed = []
    for l in lines:
        if l.startswith(("FAILED ", "ERROR ")) and "::" in l:
            tid = l.split(" ", 1)[1].split(" - ", 1)[0]
            failed.append(re.sub(r"\[.*$", "", tid.split("::", 1)[1]))
    return ("PASS" if ok else "FAIL"), failed


def exit_info(run):
    try:
        s = json.loads((run / "trace" / "stats.json").read_text())
    except Exception:
        s = {}
    return s.get("exit_status", "unknown")


def clean_output(text):
    return text.replace("\\u0027", "'").replace('\\"', '"').replace("\\n", "\n")


def steps(run):
    msgs = json.loads((run / "trace" / "mini.traj.json").read_text())["messages"]
    out = []
    for i, m in enumerate(msgs):
        if m["role"] != "assistant":
            continue
        code, tool_out, rc, tool_idx = "", None, None, None
        for tc in m.get("tool_calls") or []:
            try:
                args = json.loads(tc["function"]["arguments"])
                code = args.get("code") or args.get("command") or json.dumps(args)
            except Exception:
                code = tc["function"].get("arguments", "")
        if i + 1 < len(msgs) and msgs[i + 1]["role"] == "tool":
            c = msgs[i + 1]["content"]
            try:
                j = json.loads(c)
                tool_out, rc = clean_output(str(j.get("output", ""))), j.get("returncode")
            except Exception:
                tool_out = clean_output(c)
            tool_idx = i + 1
        out.append({"req": len(out) + 1, "msg": i, "tool_msg": tool_idx, "code": code, "out": tool_out, "rc": rc})
    return out, msgs


def instruction(task):
    return (UNITS / task / "instruction.md").read_text(errors="ignore")


def in_text(name, text_low):
    n = name.lower().strip()
    if not n:
        return False
    return re.search(r"(?<![a-z0-9_])" + re.escape(n) + r"(?![a-z0-9_])", text_low) is not None


def json_keys(obj, path="", out=None):
    if out is None:
        out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.append((path, str(k), list(map(str, obj.keys()))))
            json_keys(v, f"{path}/{k}", out)
    elif isinstance(obj, list):
        for v in obj[:50]:
            json_keys(v, f"{path}[]", out)
    return out


def input_names(task):
    names, values, template = {}, set(), set()
    d = UNITS / task / "environment" / "data"
    if not d.exists():
        return names, values, template
    for f in sorted(d.rglob("*")):
        rel = str(f.relative_to(d))
        suf = f.suffix.lower()
        try:
            if suf in (".csv", ".tsv"):
                with open(f, errors="ignore", newline="") as fh:
                    r = csv.reader(fh, delimiter="\t" if suf == ".tsv" else ",")
                    for h in next(r, []):
                        if h.strip():
                            names.setdefault(h.strip(), rel)
                    for i, row in enumerate(r):
                        if i > 2000:
                            break
                        for c in row[:6]:
                            if c and not NUM_RE.match(c) and len(c) < 30:
                                values.add(c.strip())
            elif suf == ".json" and f.stat().st_size < 20_000_000:
                obj = json.loads(f.read_text(errors="ignore"))
                for p, k, _ in json_keys(obj):
                    if p.count("/") <= 2:
                        names.setdefault(k, rel)
            elif suf == ".jsonl":
                with open(f, errors="ignore") as fh:
                    for i, line in enumerate(fh):
                        if i > 50:
                            break
                        for p, k, _ in json_keys(json.loads(line)):
                            names.setdefault(k, rel)
            elif suf == ".py" and "template" in f.name:
                src = f.read_text(errors="ignore")
                template.update(x for x in re.findall(r"[\"']([A-Za-z_][A-Za-z0-9_]{1,60})[\"']", src))
        except Exception:
            pass
    return names, values, template


def is_instance(key, values):
    k = key.strip()
    code_like = re.fullmatch(r"[A-Z0-9]{2,8}|[A-Z0-9]{2,8}[/\-.][A-Z0-9]{2,8}", k) is not None
    return bool(NUM_RE.match(k) or DATE_RE.match(k) or k in values or code_like or not re.search(r"[A-Za-z]", k))
