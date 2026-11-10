import argparse
import hashlib
import json
import pathlib
import re
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verifier_agent_v8 as v8
import output_contracts

VERSION = "verifier-agent-v8.1"
RUNS = v8.ARM / "verifier-runs" / VERSION
V31_RUNS = v8.ARM / "verifier-runs" / "verifier-agent-v3.1"

def sha(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def v31_source(unit: str, statement: str) -> tuple[pathlib.Path, list[str]]:
    records = sorted((V31_RUNS / unit).glob("*/construction.json"))
    if not records:
        raise ValueError(f"{unit}: no recorded v3.1 construction")
    record_path = records[-1]
    record = json.loads(record_path.read_text())
    suite_path = record_path.parent / "grader" / "test_outputs.py"
    if record.get("unit") != unit or record.get("status") != "OK":
        raise ValueError(f"{unit}: latest v3.1 construction is not successful")
    hashes = record.get("hashes", {})
    if hashes.get("instruction_raw") != sha(statement):
        raise ValueError(f"{unit}: v3.1 instruction hash differs from the current instruction")
    if not suite_path.is_file() or hashes.get("test_outputs_py") != sha(suite_path.read_text()):
        raise ValueError(f"{unit}: v3.1 suite differs from its frozen record")
    files = record.get("files")
    if (not isinstance(files, list) or not files
            or any(not isinstance(name, str) for name in files)
            or len(files) != len(set(files))):
        raise ValueError(f"{unit}: v3.1 file list is empty or has duplicates")
    for name in files:
        p = pathlib.PurePosixPath(name)
        if not name or p.is_absolute() or ".." in p.parts:
            raise ValueError(f"{unit}: unsafe v3.1 path {name!r}")
    return record_path, files

def cites_name(name: str, text: str) -> bool:
    if re.search(rf"(?<![\w-]){re.escape(name)}(?![\w-])", text):
        return True
    for token in v8.TEMPLATE_TOKEN.findall(text):
        pattern = ""
        for part in re.split(r"(\{[A-Za-z0-9_,]+\}|<[A-Za-z0-9_]+>)", token):
            if part.startswith("{"):
                pattern += "(?:" + "|".join(re.escape(a.strip()) for a in part[1:-1].split(",")) + ")"
            elif part.startswith("<"):
                pattern += "[A-Za-z0-9_]+"
            else:
                pattern += re.escape(part)
        if re.fullmatch(pattern, name):
            return True
    return False

def build(unit: str) -> dict:
    statement = v8.load_statement(v8.UNITS / unit)
    source, required = v31_source(unit, statement)
    contracts = output_contracts.extract(statement, v8.ins.index(statement)["sections"], required,
                                         matches_name=cites_name)
    run_dir = RUNS / unit / f"{time.strftime('%Y%m%dT%H%M%S')}-{time.time_ns()}"
    contracts.update(unit=unit, instruction_sha256=sha(statement), v31_record=str(source))
    output_contracts.write_artifacts(run_dir, contracts)
    generation = output_contracts.generate_json_pytest(run_dir, contracts)
    record = {"version": VERSION, "unit": unit, "status": "GENERATED", "required_files": required,
              "structure_copied": [f["file"] for f in contracts["files"] if f["status"] == "STRUCTURE_COPIED"],
              "no_explicit_structure": [f["file"] for f in contracts["files"] if f["status"] != "STRUCTURE_COPIED"],
              "statement_sha256": sha(statement), "v31_record": str(source),
              "contracts_sha256": sha((run_dir / "output_contracts.json").read_text()),
              "schema_generation": generation,
              "pytest_sha256": sha((run_dir / "test_schema.py").read_text()),
              "cost": {"requests": 0}}
    (run_dir / "construction.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return {"run_dir": str(run_dir), **record}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build"])
    parser.add_argument("unit")
    args = parser.parse_args()
    print(json.dumps(build(args.unit), indent=2, ensure_ascii=False))
