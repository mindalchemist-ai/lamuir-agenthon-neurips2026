from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "helpers"))
import index_instruction

VERSION = "verifier-agent-v3.1"
SCOPES = ["deliverable_existence"]
ALL_SCOPES = ["deliverable_existence", "structural_validity", "numerical_accuracy", "financial_consistency"]
HERE = pathlib.Path(__file__).resolve().parent
ARM = HERE.parents[1]
REPO = ARM.parent
UNITS = REPO / "agenthon-repo/track1-coding-public/units"
RUNS = ARM / "verifier-runs" / VERSION
HELPER = ARM / "helpers" / "index_instruction.py"
STAGE_ROOT = HERE / ".sandbox-stage"
IMAGE = "finance-bench-sandbox:latest"



SYSTEM = ("You read a coding task and say which files its solution must write. Someone else will "
          "solve the task; you never see their solution. You reply with one ```json block and "
          "nothing else.")

TEMPLATE = """\
Read the task below and list the files its solution must write.

Reply with one ```json block and nothing else:

```json
[
  {"file": "<path under the output directory, as the solution writes it>",
   "source": "<the marker of the section that requires it: S07, or S07:120-126 for the lines>"}
]
```

- Every file the instruction requires, and nothing else: not a file it reads, not a file an example
  writes along the way, not a file the solution may write if it likes. Relative paths only
  ("results.json", "reports/summary.csv"), never an absolute path.
- A file required in one place and a file required in another cite different sections; do not assume
  they are all listed together.
- Cite the place that writes the file name: the runner reads the instruction there, and refuses a
  marker whose text does not write it.
- Do not copy the instruction's words. The runner reads them at the place you cite, so a marker is
  enough, and lines are better when you can give them.
- This stage asks only which files must be there. Formats, columns and values are later stages.

## The task

{statement}

## What the task provides as inputs

{inputs}
"""

REPAIR = """\
Your list was checked. These problems remain:

{errors}

Reply with the whole corrected list in one ```json block, in the same shape.

```json
{previous}
```
"""


@dataclass(frozen=True)
class Prompts:
    system: str
    template: str
    repair: str


PROMPTS = Prompts(system=SYSTEM, template=TEMPLATE, repair=REPAIR)


def extract_json(text: str):
    blocks = re.findall(r"```(?:json)?\n(.*?)```", text, re.S)
    body = (blocks[-1] if blocks else text).strip()
    try:
        return json.loads(body), None
    except json.JSONDecodeError as e:
        return None, f"the reply is not one JSON list: {e.msg} (line {e.lineno})"



SUITE_HEADER = '''\
# The file-existence stage, written by __VERSION__ from the deliverables its agent read out of the
# instruction. Each file is its own parametrized test: one failing, or raising, says nothing about
# the others. Beside each file is where the instruction requires it -- a section marker of the
# instruction as this version numbers it, with the lines when the agent could give them.
import os

import pytest

OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "/app/output")


class TestFileExistence:
    """All required output files must exist."""

    REQUIRED_OUTPUT_FILES = [
__FILES__    ]

    @pytest.mark.parametrize("filename", REQUIRED_OUTPUT_FILES)
    def test_file_exists(self, filename):
        path = os.path.join(OUTPUT_DIR, filename)
        assert os.path.isfile(path), f"Missing output file: {filename}"
'''


def render_suite(named: list[dict], version: str = VERSION) -> str:
    width = max((len(json.dumps(d["file"])) for d in named), default=0)
    files = "".join(("        " + (json.dumps(d["file"]) + ",").ljust(width + 2)
                     + (f"  # {d['source']}" if d.get("source") else "")).rstrip() + "\n" for d in named)
    return SUITE_HEADER.replace("__VERSION__", version).replace("__FILES__", files)


def test_id(file: str) -> str:
    return f"test_file_exists[{file}]"



def source_evidence(marker, sections: list[dict], statement: str) -> dict | None:
    where, problem = index_instruction.resolve(marker, sections, statement) if marker else (None, "none given")
    return None if problem else {**where, "text": where["text"][:2000]}


def citation_errors(cited_by: dict, sections: list[dict], statement: str) -> list[str]:
    errors = []
    for what, marker in cited_by.items():
        where, problem = index_instruction.resolve(marker, sections, statement)
        if problem:
            errors.append(f"{what}: {problem}")
        elif not re.search(r"(?<![\w.-])" + re.escape(pathlib.PurePosixPath(str(what)).name) + r"(?![\w-])",
                           where["text"]):
            named = marker if where["level"] == "lines" else f"{marker} ({where['path']})"
            errors.append(f"{what}: {named} does not write that name; cite the place that does")
    return errors



def named_files(value, statement: str = "") -> tuple[list[dict], list[str]]:
    if not isinstance(value, list) or not value:
        return [], ['reply with a non-empty JSON list of {"file": ..., "source": ...}']
    named, errors, seen = [], [], set()
    for i, entry in enumerate(value):
        where = f"entry {i + 1}"
        if not isinstance(entry, dict) or not isinstance(entry.get("file"), str) or not entry["file"].strip():
            errors.append(f'{where}: give {{"file": "<path>", "source": "<S07 or S07:120-126>"}}')
            continue
        path = entry["file"].strip()
        if path.startswith("/") or ".." in pathlib.PurePosixPath(path).parts:
            errors.append(f"{where}: {path} must be relative to the output directory")
            continue
        if path in seen:
            errors.append(f"{where}: {path} is listed twice")
            continue
        seen.add(path)
        written = as_written(path, statement) if statement else None
        corrected = {"corrected_from": path} if written and written != path else {}
        final_path = written if corrected else path
        if any(d["file"] == final_path for d in named):
            errors.append(f"{where}: {final_path} is listed twice after path normalization")
            continue
        named.append({"file": final_path, "source": entry.get("source"), **corrected})
    return named, errors


OUTPUT_DIR_PREFIX = re.compile(r"^(?:\./)?(?:/?app/)?output/", re.I)


def as_written(file: str, statement: str) -> str | None:
    if "/" in file and not OUTPUT_DIR_PREFIX.match(file):
        return file
    name = pathlib.PurePosixPath(file).name
    found = re.findall(r"[\w./-]*" + re.escape(name) + r"(?![\w-])", statement)
    paths = {OUTPUT_DIR_PREFIX.sub("", path.lstrip("/")) for path in found if "/" in path}
    paths.discard("")
    if len(paths) == 1:
        return paths.pop()
    return name if found else None


def grounding_errors(named: list[dict], sections: list[dict], statement: str) -> list[str]:
    errors, cite_for = [], {}
    for d in named:
        name = pathlib.PurePosixPath(d["file"]).name
        if not re.search(r"(?<![\w.-])" + re.escape(name) + r"(?![\w-])", statement):
            errors.append(f"{d['file']} is not named anywhere in the instruction; do not invent an output")
        elif d.get("source") is None:
            errors.append(f'{d["file"]}: give a source, "S07" or "S07:120-126"')
        else:
            cite_for[d["file"]] = d["source"]
    return errors + citation_errors(cite_for, sections, statement)



class SandboxFailed(RuntimeError):
    pass


_RESULT = re.compile(r"^\S*test_outputs\.py::\S*?(test_file_exists\[[^\]]*\])\s+(PASSED|FAILED|ERROR)", re.M)
_MESSAGE = re.compile(r"^(?:FAILED|ERROR) \S*?(test_file_exists\[[^\]]*\])(?: - (.*))?$", re.M)
_COUNT = re.compile(r"(\d+) (passed|failed|error)")


def read_report(output: str, returncode: int) -> dict:
    status = {test: state for test, state in _RESULT.findall(output)}
    messages = {test: (msg or "").strip() for test, msg in _MESSAGE.findall(output)}
    for test, state in status.items():
        if state == "PASSED":
            continue
        name = test[len("test_file_exists["):-1]
        told = [ln.strip().removeprefix("E").strip() for ln in output.splitlines()
                if name in ln and ("Missing output file" in ln or "Error" in ln)]
        if told:
            messages[test] = told[0]
    counts = {kind: int(n) for n, kind in _COUNT.findall(output)}
    return {"status": status, "messages": messages, "counts": counts, "returncode": returncode,
            "collected": len(status), "usable": bool(status), "output": output[-4000:]}


def run_suite(suite: pathlib.Path, candidate_dir: pathlib.Path, image: str | None = None,
              timeout: int = 300) -> dict:
    image = image or ensure_image()
    stage = STAGE_ROOT / secrets.token_hex(6)
    try:
        (stage / "suite").mkdir(parents=True)
        shutil.copyfile(suite, stage / "suite" / "test_outputs.py")
        shutil.copytree(candidate_dir, stage / "candidate", symlinks=True)
        cmd = ["docker", "run", "--rm", "--network", "none", "--read-only", "--tmpfs", "/tmp:size=64m",
               "--cpus", "1", "--memory", "1g", "--pids-limit", "128", "--cap-drop", "ALL",
               "--security-opt", "no-new-privileges",
               "-v", f"{stage / 'suite'}:/suite:ro", "-v", f"{stage / 'candidate'}:/app/output:ro",
               "-e", "OUTPUT_DIR=/app/output", image,
               "sh", "-c", "cd /suite && python -m pytest test_outputs.py -v --no-header "
                           "-p no:cacheprovider -o addopts= --tb=line"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise SandboxFailed(f"the suite exceeded {timeout}s") from e
        return read_report(p.stdout + p.stderr, p.returncode)
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def ensure_image() -> str:
    probe = subprocess.run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
                           capture_output=True, text=True)
    if probe.returncode != 0:
        raise SandboxFailed(f"the sandbox image {IMAGE} is not built")
    return probe.stdout.strip()


def suite_errors(suite: pathlib.Path, files: list[str], image: str | None = None) -> list[str]:
    stage = STAGE_ROOT / secrets.token_hex(6)
    errors = []
    try:
        cases = []
        for name, holds in (("empty", "nothing"), ("full", "every file"), ("dirs", "directories")):
            d = stage / name
            d.mkdir(parents=True)
            cases.append((d, holds))
        for f in files:
            (stage / "full" / f).parent.mkdir(parents=True, exist_ok=True)
            (stage / "full" / f).write_text("x")
            (stage / "dirs" / f).mkdir(parents=True, exist_ok=True)
        for candidate, holds in cases:
            try:
                run = run_suite(suite, candidate, image)
            except SandboxFailed as e:
                return [f"the suite could not be run: {e}"]
            if run["collected"] != len(files):
                errors.append(f"on an output directory holding {holds} the suite ran "
                              f"{run['collected']} of {len(files)} tests: {run['output'][-300:]}")
                continue
            for f in files:
                state = run["status"].get(test_id(f))
                want = "PASSED" if holds == "every file" else "FAILED"
                if state != want:
                    errors.append(f"on an output directory holding {holds}, {test_id(f)} was "
                                  f"{state}, and should have been {want}")
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return errors



class BudgetExhausted(RuntimeError):
    pass


class CountedAsk:

    def __init__(self, ask, limit: int):
        self.ask, self.limit, self.requests = ask, limit, 0
        self.tokens_in = self.tokens_out = 0
        self.failures: list[str] = []

    @property
    def remaining(self) -> int:
        return self.limit - self.requests

    def __call__(self, system: str, user: str) -> tuple[str, dict]:
        if self.requests >= self.limit:
            raise BudgetExhausted(f"the request limit of {self.limit} is spent")
        self.requests += 1
        try:
            text, usage = self.ask(system, user)
        except Exception as e:
            self.failures.append(f"request {self.requests}: {type(e).__name__}: {e}"[:200])
            raise BudgetExhausted(str(e)) from e
        self.tokens_in += usage.get("tokens_in", 0)
        self.tokens_out += usage.get("tokens_out", 0)
        return text, usage

    def summary(self) -> dict:
        return {"requests": self.requests, "limit": self.limit, "tokens_in": self.tokens_in,
                "tokens_out": self.tokens_out, "failures": self.failures}



def load_statement(unit_dir: pathlib.Path) -> tuple[str, str]:
    raw = (unit_dir / "instruction.md").read_text()
    return raw, raw


def describe_inputs(unit_dir: pathlib.Path) -> str:
    data = unit_dir / "environment" / "data"
    names = sorted(p.relative_to(data).as_posix() for p in data.rglob("*") if p.is_file()) if data.is_dir() else []
    return "\n".join(f"- {n}" for n in names) or "(this task provides no input files)"


def input_hashes(unit_dir: pathlib.Path) -> dict:
    data = unit_dir / "environment" / "data"
    if not data.is_dir():
        return {}
    return {p.relative_to(data).as_posix(): _sha(p.read_bytes()) for p in sorted(data.rglob("*")) if p.is_file()}


def _sha(data: bytes | str) -> str:
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()


def _git_commit() -> str:
    p = subprocess.run(["git", "-C", str(HERE), "rev-parse", "HEAD"], capture_output=True, text=True)
    return p.stdout.strip() or "unknown"



def first_request(prompts: Prompts, sections: list[dict], statement: str, inputs: str) -> str:
    return (prompts.template.replace("{statement}", index_instruction.render(sections, statement))
            .replace("{inputs}", inputs))


def build(unit_dir: pathlib.Path, out_dir: pathlib.Path, ask, prompts: Prompts = PROMPTS,
          limit: int = 25, model_config: dict | None = None, calls_dir: pathlib.Path | None = None,
          record: bool = False, reply_transform=None, version: str = VERSION):
    started = time.time()
    run_dir = out_dir / f"{time.strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(3)}"
    grader = run_dir / "grader"
    grader.mkdir(parents=True)
    raw, statement = load_statement(unit_dir)
    sections = index_instruction.sections(statement)
    counted = CountedAsk(ask, limit)
    image = ensure_image()
    first = first_request(prompts, sections, statement, describe_inputs(unit_dir))
    rounds, named, errors, reply = [], [], ["no reply yet"], "[]"
    user = first
    while True:
        try:
            text, usage = counted(prompts.system, user)
        except BudgetExhausted:
            break
        value, error = extract_json(text)
        transformed, transform_errors = (reply_transform(value, statement) if reply_transform and not error
                                         else (value, []))
        named, errors = ([], [error]) if error else named_files(transformed, statement)
        errors = transform_errors + errors
        reply = json.dumps(value if value is not None else text[:2000], indent=1, ensure_ascii=False)
        if named and not errors:
            errors = grounding_errors(named, sections, statement)
        if named and not errors:
            (grader / "test_outputs.py").write_text(render_suite(named, version))
            errors = suite_errors(grader / "test_outputs.py", [d["file"] for d in named], image)
        rounds.append({"request": counted.requests, "finish_reason": usage.get("finish_reason"),
                       "files": [d["file"] for d in named], "errors": errors})
        if named and not errors:
            break
        user = first + "\n\n" + (prompts.repair.replace("{errors}", "\n".join(f"- {e}" for e in errors))
                                  .replace("{previous}", reply))
    status = "OK" if named and not errors else "CONSTRUCTION_FAILED"
    suite = render_suite(named, version) if status == "OK" else ""
    (grader / "test_outputs.py").write_text(suite)
    deliverables = [{"file": d["file"], "test": test_id(d["file"]), "source": d.get("source"),
                     "source_evidence": source_evidence(d.get("source"), sections, statement),
                     **({"corrected_from": d["corrected_from"]} if d.get("corrected_from") else {})}
                    for d in named]
    made = {
        "version": version, "unit": unit_dir.name, "scopes": SCOPES, "status": status,
        "files": [d["file"] for d in named], "deliverables": deliverables,
        "errors_left": errors if status != "OK" else [],
        "rounds": rounds, "cost": counted.summary(), "seconds": round(time.time() - started, 2),
        "config": {**(model_config or {}), "request_limit": limit, "sandbox_image": image,
                   "system_prompt_sha256": _sha(prompts.system),
                   "template_prompt_sha256": _sha(prompts.template),
                   "repair_prompt_sha256": _sha(prompts.repair),
                   "suite_template_sha256": _sha(SUITE_HEADER),
                   "index_helper_sha256": _sha(pathlib.Path(HELPER).read_bytes())},
        "hashes": {"instruction_raw": _sha(raw), "instruction_sent": _sha(statement),
                   "inputs": input_hashes(unit_dir), "test_outputs_py": _sha(suite),
                   "executor_sha256": _sha(pathlib.Path(__file__).read_bytes()),
                   "executor_commit": _git_commit()},
    }
    if record:
        (run_dir / "construction.json").write_text(json.dumps(made, indent=1, ensure_ascii=False))
        if calls_dir and calls_dir.exists():
            calls_dir.rename(run_dir / "calls")
    elif calls_dir and calls_dir.exists():
        shutil.rmtree(calls_dir, ignore_errors=True)
    return run_dir



NOTE = ("No violation found does not establish that the output is correct: this stage checks only "
        "that the required files are there, and which files those are was extracted by a model.")
EXIT_CODE = {"NO_VIOLATION_FOUND": 0, "VIOLATION": 1, "INCONCLUSIVE": 2,
             "CONSTRUCTION_FAILED": 3, "EXECUTION_FAILED": 4}


def failed(run_status: str, detail: str) -> dict:
    return {"run_status": run_status, "detail": detail, "scope": SCOPES, "verdict": None,
            "failing_tests": {}, "findings": [], "checked": [], "not_run": [], "note": NOTE}


def deliverables_of(run_dir: pathlib.Path) -> list[dict]:
    suite = (run_dir / "grader" / "test_outputs.py").read_text()
    block = re.search(r"REQUIRED_OUTPUT_FILES\s*=\s*\[(.*?)\n    \]", suite, re.S)
    cited = re.findall(r'"([^"]+)",\s*(?:#\s*(\S+))?', block.group(1) if block else "")
    kept = run_dir / "construction.json"
    known = {}
    if kept.is_file():
        known = {d["file"]: d for d in json.loads(kept.read_text()).get("deliverables", [])}
    return [{"file": f, "test": test_id(f), "source": known.get(f, {}).get("source") or (source or None),
             "source_evidence": known.get(f, {}).get("source_evidence")} for f, source in cited]


def verify(run_dir: pathlib.Path, input_dir: pathlib.Path, candidate_dir: pathlib.Path) -> dict:
    suite = run_dir / "grader" / "test_outputs.py"
    kept = run_dir / "construction.json"
    made = json.loads(kept.read_text()) if kept.is_file() else None
    if not suite.is_file() or not deliverables_of(run_dir):
        return failed("CONSTRUCTION_FAILED", "the build has no validated deliverable list")
    if made and made["status"] != "OK":
        return failed("CONSTRUCTION_FAILED", json.dumps(made.get("errors_left"))[:1000])
    image = None
    if made:
        frozen = made["hashes"]
        if _sha(suite.read_text()) != frozen["test_outputs_py"]:
            return failed("EXECUTION_FAILED", "the frozen suite does not match its recorded hash")
        now = {p.relative_to(input_dir).as_posix(): _sha(p.read_bytes())
               for p in sorted(pathlib.Path(input_dir).rglob("*")) if p.is_file()} if input_dir.is_dir() else {}
        if now != frozen["inputs"]:
            return failed("EXECUTION_FAILED", "the task inputs differ from the ones the suite was built with")
        image = made["config"].get("sandbox_image")
        if not image or subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode != 0:
            return failed("EXECUTION_FAILED", f"the frozen sandbox image {image} is not available")
    try:
        run = run_suite(suite, candidate_dir, image)
    except SandboxFailed as e:
        return failed("EXECUTION_FAILED", str(e))
    expected = {d["test"] for d in deliverables_of(run_dir)}
    if not run["usable"] or set(run["status"]) != expected:
        return failed("EXECUTION_FAILED", run["output"][-1000:])
    findings, checked, not_run = [], [], []
    for r in deliverables_of(run_dir):
        state = run["status"].get(r["test"])
        entry = {"test": r["test"], "artifact": r["file"], "source": r.get("source"),
                 "source_evidence": r.get("source_evidence")}
        if state == "PASSED":
            checked.append({**entry, "status": "PASS"})
        elif state == "FAILED":
            findings.append({**entry, "status": "FAIL", "location": None,
                             "observed": run["messages"].get(r["test"]) or "the path is not a file",
                             "expected": "a file at that path"})
        else:
            not_run.append({**entry, "status": state or "NOT_RUN",
                            "reason": run["messages"].get(r["test"]) or "the test produced no result"})
    verdict = "VIOLATION" if findings else ("INCONCLUSIVE" if not_run else "NO_VIOLATION_FOUND")
    return {"run_status": "OK", "scope": SCOPES, "verdict": verdict, "counts": run["counts"],
            "conditions_checked": bool(made),
            "failing_tests": {t: run["messages"].get(t, "") for t, s in run["status"].items() if s != "PASSED"},
            "findings": findings, "checked": checked, "not_run": not_run,
            "not_checked": [s for s in ALL_SCOPES if s not in SCOPES], "note": NOTE}



def cmd_build(unit: str, limit: int, record: bool) -> int:
    from dotenv import load_dotenv

    sys.path.insert(0, str(ARM / "verifier-agent"))
    import ms_ask_house

    load_dotenv(REPO / ".env")
    out = RUNS / unit
    out.mkdir(parents=True, exist_ok=True)
    calls = out / "_calls_pending"
    ask = ms_ask_house.build_ask(record_dir=calls)
    run_dir = build(UNITS / unit, out, ask, PROMPTS, limit, calls_dir=calls, record=record,
                    model_config={"model": os.environ.get("MODEL_NAME"),
                                  "temperature": ms_ask_house.TEMPERATURE,
                                  "max_tokens": ms_ask_house.MAX_TOKENS})
    files = [d["file"] for d in deliverables_of(run_dir)]
    print(json.dumps({"run_dir": str(run_dir), "suite": str(run_dir / "grader" / "test_outputs.py"),
                      "files": files}, indent=1))
    return 0 if files else 3


def cmd_verify(run_dir: str, unit: str, candidate: str, out: str | None) -> int:
    report = verify(pathlib.Path(run_dir), UNITS / unit / "environment" / "data", pathlib.Path(candidate))
    text = json.dumps(report, indent=1, ensure_ascii=False)
    if out:
        pathlib.Path(out).write_text(text)
    print(text)
    return EXIT_CODE[report["verdict"] or report["run_status"]]


def main() -> int:
    ap = argparse.ArgumentParser(prog=VERSION, description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("unit")
    b.add_argument("--max-requests", type=int, default=25)
    b.add_argument("--record", action="store_true",
                   help="also keep construction.json and the calls: the hashes that let judging "
                        "refuse a changed suite, the place each file was required, and the cost")
    v = sub.add_parser("verify")
    v.add_argument("run_dir")
    v.add_argument("unit")
    v.add_argument("candidate")
    v.add_argument("--report")
    a = ap.parse_args()
    return cmd_build(a.unit, a.max_requests, a.record) if a.cmd == "build" else \
        cmd_verify(a.run_dir, a.unit, a.candidate, a.report)


if __name__ == "__main__":
    raise SystemExit(main())
