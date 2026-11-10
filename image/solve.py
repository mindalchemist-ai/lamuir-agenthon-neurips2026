import argparse
import os
import pathlib
import subprocess
import sys

WORK = pathlib.Path("/tmp/work")
CFG = pathlib.Path("/tmp/cfg")
TRACE = pathlib.Path("/tmp/trace")
VERSION = "solver-agent-v205l"


def path_map(task_dir):
    env = task_dir / "environment"
    pairs = []
    dockerfile = env / "Dockerfile"
    if dockerfile.is_file():
        for line in dockerfile.read_text(errors="replace").splitlines():
            parts = [p for p in line.split() if not p.startswith("--")]
            if len(parts) != 3 or parts[0].upper() not in ("COPY", "ADD"):
                continue
            src = env / parts[1].rstrip("/")
            if not src.exists():
                continue
            dst = parts[2]
            if src.is_dir():
                pairs.append((dst.rstrip("/") + "/", f"{src}/"))
            else:
                pairs.append((dst + src.name if dst.endswith("/") else dst, str(src)))
    data = env / "data"
    if data.is_dir() and not any(d == "/app/data/" for d, _ in pairs):
        pairs.append(("/app/data/", f"{data}/"))
    return pairs


def path_notes(task_dir):
    lines = [f"  {dst} -> {src}" for dst, src in path_map(task_dir)]
    if lines:
        where = ("Where the task names an input path under /app, read it from here instead:\n"
                 + "\n".join(lines) + "\n")
    else:
        where = "No input-path mapping was inferred. Follow the task text and inspect it as needed.\n"
    return (
        "\n\nPath notes:\n"
        f"- The task's files are mounted read-only under {task_dir}. {where}"
        "- /app is read-only except /app/output, where the deliverables go. "
        f"Save scripts and scratch files in {WORK} (small; keep large files out of it).\n"
    )


def version_settings(path):
    import ast
    out = {}
    for node in ast.parse(pathlib.Path(path).read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ("ENTRY_LINE", "ENTRY_FILE"):
                out[node.targets[0].id] = ast.literal_eval(node.value)
    return out


def make_readable(out_dir):
    for root, dirs, files in os.walk(out_dir, followlinks=False):
        for name in dirs + files:
            path = os.path.join(root, name)
            try:
                if os.path.islink(path):
                    continue
                os.chmod(path, 0o755 if os.path.isdir(path) else 0o644)
            except OSError as exc:
                print(f"[solve] chmod {path}: {exc}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("verb")
    ap.add_argument("--task-dir", default="/input", type=pathlib.Path)
    ap.add_argument("--out", default="/app/output", type=pathlib.Path)
    args = ap.parse_args()
    if args.verb != "solve":
        print(f"[solve] unknown verb {args.verb!r}", flush=True)
        return 0
    if str(args.task_dir) != "/input" or not pathlib.Path("/input/instruction.md").is_file():
        print(f"[solve] warning: task dir {args.task_dir}, /input/instruction.md present: "
              f"{pathlib.Path('/input/instruction.md').is_file()}", flush=True)
    try:
        for d in (WORK, CFG, TRACE):
            d.mkdir(parents=True, exist_ok=True)
        solver = version_settings("/opt/" + VERSION.replace("-", "_") + ".py")
        task = (args.task_dir / "instruction.md").read_text()
        task += path_notes(args.task_dir)
        task += "\n\n" + solver["ENTRY_LINE"]
        (CFG / "task.txt").write_text(task)
        env = os.environ | {
            "HOME": "/tmp", "MINI_CFG": str(CFG), "MINI_TRACE": str(TRACE),
            "MINI_STEP_LIMIT": "25", "MINI_AGENT": VERSION, "MINI_GATE": "", "MINI_GATE_ROUNDS": "1",
            "MINI_ENTRY_FILE": solver.get("ENTRY_FILE") or "","MINI_CWD": str(WORK), "MINI_WORKFLOW": "",
            "MINI_TEMPERATURE": "0", "MINI_MAX_TOKENS": "4000", "MINI_WALL_CLOCK": "card",
            "MINI_REQUEST_BUDGET": "25", "MINI_TEMPLATE_KWARGS": "", "MINI_DELIVERABLE_EXISTENCE_VERIFIER": "",
            "MINI_REVIEWER": "v3", "MINI_REVIEWER_WHEN_SILENT": "0", "MINI_REL_ERROR_LIMIT": "1.0",
            "MINI_DISTINCT_PAIRS": "", "MINI_FINDINGS_PER_ROUND": "2", "MINI_NULL_CHECK": "0",
            "MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT": "1000000000",
        }
        cwd = "/app" if os.path.isdir("/app") else str(WORK)
        rc = subprocess.run(["/opt/agent/bin/python", "/opt/mini_driver.py"], env=env, cwd=cwd).returncode
        print(f"[solve] mini_driver exited {rc}", flush=True)
    except Exception as exc:
        print(f"[solve] {type(exc).__name__}: {exc}", flush=True)
    finally:
        make_readable(str(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
