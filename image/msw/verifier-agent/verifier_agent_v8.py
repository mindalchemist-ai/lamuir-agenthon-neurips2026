from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
ARM = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ARM / "helpers"))

import index_instruction as ins
import ms_ask_house

VERSION = "verifier-agent-v8"
UNITS = ARM.parent / "agenthon-repo/track1-coding-public/units"
RUNS = ARM / "verifier-runs" / VERSION

TYPES = {"int": (int,), "float": (int, float), "str": (str,), "bool": (bool,),
         "list": (list,), "any": (object,)}

SYSTEM = ("You read a coding task and describe the shape of the files its solution must write. "
          "Someone else will solve the task; you never see their solution. You reply with one "
          "```json block and nothing else.")

TEMPLATE = """\
Read the task below and describe the shape of every file its solution must write.

Reply with one ```json block and nothing else:

```json
[
  {"file": "results.json", "format": "json",
   "schema": {"a_key": "int", "a_group": {"a_nested_key": "float"}},
   "source": "S07:120-126"},
  {"file": "trades.csv", "format": "csv",
   "columns": ["ticker", "price"],
   "source": "S09"}
]
```

- Describe shape only: which keys exist, how they nest, and what type each holds. Not the values,
  not how to compute them -- those are later stages.
- A leaf type is one of: int, float, str, bool, list, any. Nest an object by giving an object.
- For a csv, list its columns in the order the task states them. When the task names the first
  columns and then says the rest come from the data -- "`S`, then time values as headers" -- write
  the named ones and end the list with `"<data>"`. Never invent names for those: they are whatever
  the numbers turn out to be, and the checker only has to know where the named part stops.
- Every file the task requires, and nothing else: not a file it reads, not a file an example writes
  along the way. Relative paths only ("results.json", "reports/summary.csv").
- Cite the section that states the shape. The runner reads the instruction there and refuses a
  citation whose text does not name the keys you listed.
- Keep the nesting exactly as the task shows it. A key inside an object is not the same as a key at
  the top level, and that difference is the most common way a solution is wrong.

## The task

{statement}

## What the task provides as inputs

{inputs}
"""

REPAIR = """\
Your description was checked. These problems remain:

{errors}

Reply with the whole corrected description in one ```json block, in the same shape.
"""


def fill(template: str, **parts) -> str:
    for k, v in parts.items():
        template = template.replace("{" + k + "}", v)
    return template


def extract_json(text: str):
    blocks = re.findall(r"```json\s*(.*?)```", text, re.S) or re.findall(r"```\s*(.*?)```", text, re.S)
    raw = (blocks[-1] if blocks else text).strip()
    try:
        return json.loads(raw), ""
    except ValueError as e:
        return None, f"the reply is not JSON: {e}"


def leaves(schema, path=""):
    for k, v in schema.items():
        p = f"{path}.{k}" if path else k
        if isinstance(v, dict):
            yield from leaves(v, p)
        else:
            yield p, v


def cited_text(marker: str, sections: list[dict], statement: str) -> str | None:
    m = re.fullmatch(r"(S\d+)(?::(\d+)(?:-(\d+))?)?", (marker or "").strip())
    if not m:
        return None
    sec = next((s for s in sections if s["id"] == m.group(1)), None)
    if sec is None:
        return None
    lines = statement.splitlines()
    if m.group(2):
        a, b = int(m.group(2)), int(m.group(3) or m.group(2))
        if not (1 <= a <= b <= len(lines)):
            return None
        return "\n".join(lines[a - 1:b])
    return "\n".join(lines[sec["line_start"] - 1:sec["line_end"]])


TEMPLATE_TOKEN = re.compile(r"[A-Za-z0-9_.<>{},]*[{<][A-Za-z0-9_,]+[}>][A-Za-z0-9_.<>{},]*")


def names(key: str, text: str) -> bool:
    if key in text:
        return True
    for token in TEMPLATE_TOKEN.findall(text):
        pattern = ""
        for part in re.split(r"(\{[A-Za-z0-9_,]+\}|<[A-Za-z0-9_]+>)", token):
            if part.startswith("{"):
                pattern += "(?:" + "|".join(re.escape(a.strip()) for a in part[1:-1].split(",")) + ")"
            elif part.startswith("<"):
                pattern += "[A-Za-z0-9_]+"
            else:
                pattern += re.escape(part)
        if re.fullmatch(pattern, key):
            return True
    return False


GLOSS = re.compile(r"\s*\([^)]*\)\s*$")


def strip_glosses(described) -> None:
    for d in described:
        if isinstance(d, dict) and isinstance(d.get("columns"), list):
            d["columns"] = [GLOSS.sub("", c) if isinstance(c, str) else c for c in d["columns"]]


def acceptance_errors(described, sections, statement) -> list[str]:
    errs = []
    if not isinstance(described, list) or not described:
        return ["the reply is not a non-empty list of files"]
    for i, d in enumerate(described):
        where = f"entry {i + 1}"
        if not isinstance(d, dict):
            errs.append(f"{where}: not an object"); continue
        name, fmt = d.get("file"), d.get("format")
        where = f"`{name}`" if name else where
        if not isinstance(name, str) or not name:
            errs.append(f"{where}: `file` is missing")
        if fmt not in ("json", "csv"):
            errs.append(f"{where}: `format` must be \"json\" or \"csv\"")
        text = cited_text(d.get("source", ""), sections, statement)
        if text is None:
            errs.append(f"{where}: `source` {d.get('source')!r} does not resolve to a section of "
                        f"the instruction")
        if fmt == "json":
            schema = d.get("schema")
            if not isinstance(schema, dict) or not schema:
                errs.append(f"{where}: `schema` must be a non-empty object"); continue
            for path, typ in leaves(schema):
                if not isinstance(typ, str) or typ not in TYPES:
                    errs.append(f"{where}: `{path}` has type {typ!r}, not one of {sorted(TYPES)}")
                if text is not None and not names(path.split(".")[-1], text):
                    errs.append(f"{where}: the cited text does not name `{path.split('.')[-1]}`")
        elif fmt == "csv":
            cols = d.get("columns")
            if not isinstance(cols, list) or not cols or not all(isinstance(c, str) for c in cols):
                errs.append(f"{where}: `columns` must be a non-empty list of names"); continue
            for c in cols:
                if c == DATA_COLUMNS:
                    continue
                if text is not None and not names(c, text):
                    errs.append(f"{where}: the cited text does not name column `{c}`")
            if DATA_COLUMNS in cols and cols[-1] != DATA_COLUMNS:
                errs.append(f"{where}: `{DATA_COLUMNS}` stands for the rest of the columns, so it "
                            f"can only be the last entry")
    return errs


DATA_COLUMNS = "<data>"

PLACEHOLDER_KEY = re.compile(r"<[A-Za-z_][A-Za-z0-9_]*>")


def compare_json(spec, got, path="") -> list[str]:
    if not isinstance(got, dict):
        return [f"{path or 'the top level'} should be an object, found {type(got).__name__}"]
    out = []
    for key, want in spec.items():
        if PLACEHOLDER_KEY.fullmatch(str(key)):
            here = f"{path}.{key}" if path else key
            if not got:
                out.append(f"{here}: nothing is reported at this level")
            elif isinstance(want, dict):
                for actual in got:
                    out += compare_json(want, got[actual], f"{path}.{actual}" if path else actual)
            continue
        here = f"{path}.{key}" if path else key
        if key not in got:
            found = ", ".join(list(got)[:8]) or "nothing"
            out.append(f"missing key `{here}` (found at this level: {found})")
        elif isinstance(want, dict):
            out += compare_json(want, got[key], here)
        elif want in TYPES and not isinstance(got[key], TYPES[want]):
            if not (want == "any" or got[key] is None):
                out.append(f"`{here}` should be {want}, found {type(got[key]).__name__}")
    return out


def deliverable(out_dir: pathlib.Path, name: str) -> pathlib.Path:
    return out_dir / pathlib.PurePosixPath(name).name


def compare_csv(columns: list[str], path: pathlib.Path) -> list[str]:
    with path.open(newline="") as fh:
        header = next(csv.reader(fh), [])
    header = [h.strip() for h in header]
    open_ended = DATA_COLUMNS in columns
    named = [c for c in columns if c != DATA_COLUMNS]
    missing = [c for c in named if c not in header]
    out = [f"missing column `{c}` (found: {', '.join(header[:8]) or 'nothing'})" for c in missing]
    if not missing and header[:len(named)] != named:
        out.append(f"columns start {', '.join(header[:len(named) + 1])}; the task states "
                   + ", ".join(named) + (", then columns the data decides" if open_ended else ""))
    return out


def load_statement(unit_dir: pathlib.Path) -> str:
    return (unit_dir / "instruction.md").read_text()


def describe_inputs(unit_dir: pathlib.Path) -> str:
    data = unit_dir / "environment" / "data"
    names = sorted(p.relative_to(data).as_posix() for p in data.rglob("*") if p.is_file()) \
        if data.is_dir() else []
    return "\n".join(f"- {n}" for n in names) or "(this task provides no input files)"


def build(unit: str, limit: int = 25) -> dict:
    unit_dir = UNITS / unit
    statement = load_statement(unit_dir)
    sections = ins.index(statement)["sections"]
    run_dir = RUNS / unit / f"{time.strftime('%Y%m%dT%H%M%S')}-{hashlib.sha256(statement.encode()).hexdigest()[:6]}"
    (run_dir / "calls").mkdir(parents=True, exist_ok=True)
    ask = ms_ask_house.build_ask(record_dir=run_dir / "calls")

    numbered, inputs = ins.index(statement)["numbered"], describe_inputs(unit_dir)
    user = fill(TEMPLATE, statement=numbered, inputs=inputs)
    requests, cost, described, errs = 0, {"tokens_in": 0, "tokens_out": 0}, None, ["not asked yet"]
    while errs and requests < limit:
        text, usage = ask(SYSTEM, user)
        requests += 1
        cost["tokens_in"] += usage["tokens_in"]
        cost["tokens_out"] += usage["tokens_out"]
        value, err = extract_json(text)
        errs = [err] if err else acceptance_errors(value, sections, statement)
        if not errs:
            described = value
            break
        user = fill(TEMPLATE, statement=numbered, inputs=inputs) + "\n" + \
            fill(REPAIR, errors="\n".join(f"- {e}" for e in errs))

    if not described and isinstance(value, list) and value:
        keep = [f for f in value
                if isinstance(f, dict) and not acceptance_errors([f], sections, statement)]
        if keep:
            described = keep
            kept_files = {f.get("file") for f in keep}
            errs = [e for e in errs if not any(f"`{n}`" in e for n in kept_files)]
            print(f"[v8] kept {len(keep)} of {len(value)} file(s); the rest could not be justified "
                  f"against the statement", flush=True)

    record = {"version": VERSION, "unit": unit,
              "status": "OK" if described else "REJECTED",
              "partial": bool(described) and bool(errs),
              "scope": ["structural_validity"], "files": described or [],
              "unresolved": [] if described else errs,
              "statement_sha256": hashlib.sha256(statement.encode()).hexdigest(),
              "cost": {"requests": requests, "limit": limit, **cost}}
    strip_glosses(described or [])
    (run_dir / "schema.json").write_text(json.dumps(described or [], indent=1, ensure_ascii=False))
    (run_dir / "construction.json").write_text(json.dumps(record, indent=1, ensure_ascii=False))
    return {"run_dir": str(run_dir), **{k: record[k] for k in ("status", "cost", "unresolved")}}


def verify(run_dir: pathlib.Path, candidate: pathlib.Path) -> dict:
    described = json.loads((run_dir / "schema.json").read_text())
    if not described:
        return {"verdict": "INCONCLUSIVE", "reason": "the frozen run has no skeleton"}
    findings, missing = [], []
    for d in described:
        path = candidate / d["file"]
        if not path.is_file():
            missing.append(d["file"]); continue
        try:
            if d["format"] == "json":
                problems = compare_json(d["schema"], json.loads(path.read_text()))
            else:
                problems = compare_csv(d["columns"], path)
        except ValueError as e:
            problems = [f"could not be read as {d['format']}: {e}"]
        findings += [{"file": d["file"], "problem": p, "source": d.get("source")} for p in problems]
    verdict = "VIOLATION" if (findings or missing) else "NO_VIOLATION_FOUND"
    return {"verdict": verdict, "scope": ["deliverable_existence", "structural_validity"],
            "not_checked": ["numerical_accuracy", "financial_consistency"],
            "missing_files": missing, "findings": findings,
            "feedback": feedback(missing, findings)}


def feedback(missing: list[str], findings: list[dict]) -> str:
    lines = [f"- {f} was required but not written" for f in missing]
    lines += [f"- {f['file']}: {f['problem']}" for f in findings]
    return ("The files you wrote do not match the shapes the task states:\n" + "\n".join(lines)) \
        if lines else ""


def main() -> int:
    from dotenv import load_dotenv
    load_dotenv(ARM.parent / ".env")
    ap = argparse.ArgumentParser(prog=VERSION, description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("unit"); b.add_argument("--max-requests", type=int, default=25)
    v = sub.add_parser("verify"); v.add_argument("run_dir"); v.add_argument("unit")
    v.add_argument("candidate"); v.add_argument("--report")
    a = ap.parse_args()
    if a.cmd == "build":
        out = build(a.unit, a.max_requests)
    else:
        out = verify(pathlib.Path(a.run_dir), pathlib.Path(a.candidate))
        if a.report:
            pathlib.Path(a.report).write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(json.dumps(out, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
