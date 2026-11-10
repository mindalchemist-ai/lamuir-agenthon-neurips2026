
from __future__ import annotations

import json
import importlib
import inspect
import os
import shutil
import subprocess
import pathlib
import sys
import time

from minisweagent.config import get_config_from_spec
from minisweagent.environments.local import LocalEnvironment
from minisweagent.exceptions import LimitsExceeded
from minisweagent.models.litellm_model import LitellmModel
from minisweagent.utils.serialize import recursive_merge


def _house_base() -> str:
    base = os.environ["MODEL_ENDPOINT"].rstrip("/")
    return base if base.endswith("/v1") else base + "/v1"


def _house_token() -> str:
    token = os.environ.get("MODEL_TOKEN") or os.environ.get("MODEL_API_KEY")
    if not token:
        raise SystemExit("neither MODEL_TOKEN nor MODEL_API_KEY is set")
    return token

WALL_CLOCK_SECONDS = 900
COMMAND_TIMEOUT_SECONDS = 10 ** 7
WORK = pathlib.Path("/tmp/work")
MAX_TOKENS_PER_CALL = int(os.environ.get("MINI_MAX_TOKENS", "24000"))


def _stats(traj: dict) -> dict:
    tokens_in = tokens_out = 0
    commands: list[str] = []
    for message in traj.get("messages", []):
        extra = message.get("extra") or {}
        usage = ((extra.get("response") or {}).get("usage")) or {}
        tokens_in += int(usage.get("prompt_tokens") or 0)
        tokens_out += int(usage.get("completion_tokens") or 0)
        for action in extra.get("actions") or []:
            commands.append(action.get("command", ""))
    info = traj.get("info", {})
    return {
        "turns": int(info.get("model_stats", {}).get("api_calls") or 0),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "exit_status": info.get("exit_status", ""),
        "commands": commands,
    }


def _redacting_model(model):
    original = model.serialize

    def serialize():
        data = original()
        kwargs = (((data.get("info") or {}).get("config") or {}).get("model") or {}).get("model_kwargs")
        if isinstance(kwargs, dict):
            for field in ("api_key", "api_base"):
                if kwargs.get(field):
                    kwargs[field] = "<redacted>"
        return data

    model.serialize = serialize
    return model


REQUESTS_SENT = [0]


def _request_budget(model, budget: int):
    original = model._query

    def _query(*args, **kwargs):
        REQUESTS_SENT[0] += 1
        try:
            return original(*args, **kwargs)
        except Exception as exc:
            status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
            if REQUESTS_SENT[0] > budget and isinstance(status, int) and 400 <= status < 500:
                print(f"[mini_driver] request {REQUESTS_SENT[0]} refused with {status} past the allowance; submitting", flush=True)
                raise LimitsExceeded({"role": "exit", "content": "RequestBudgetExceeded",
                                      "extra": {"exit_status": "RequestBudgetExceeded", "submission": ""}})
            raise

    model._query = _query
    model.abort_exceptions = [LimitsExceeded, KeyboardInterrupt]
    return model


def _build_gate():
    if gate_mode := os.environ.get("MINI_GATE", ""):
        sys.path.insert(0, "/opt")
        import ms_gate
        return ms_gate.build(deadline=time.monotonic() + WALL_CLOCK_SECONDS,
                             entry_file=os.environ.get("MINI_ENTRY_FILE") or None,
                             mode=gate_mode)

    checks = pathlib.Path("/cfg/checks.py")
    if not checks.is_file():
        return None

    sys.path.insert(0, "/opt")
    import ms_verify

    trace = pathlib.Path("/trace")
    rounds = {"n": 0}

    def gate(agent):
        rounds["n"] += 1
        report_path = trace / f"gate_{rounds['n']}.json"
        cmd = ["python", "/opt/ms_check_runner.py", str(checks), "/app/data", "/app/output",
               str(report_path), "/cfg/task.txt"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        except (subprocess.TimeoutExpired, OSError) as exc:
            print(f"[gate] round {rounds['n']}: checks did not run ({type(exc).__name__})", flush=True)
            return None
        report = {}
        if report_path.is_file():
            try:
                report = json.loads(report_path.read_text())
            except json.JSONDecodeError:
                report = {}
        outcome = report.get("outcome")
        if outcome != "VIOLATION":
            print(f"[gate] round {rounds['n']}: {outcome or 'no report'} "
                  f"(rc={p.returncode}) — letting it through", flush=True)
            return None
        n = len(report.get("violations") or [])
        print(f"[gate] round {rounds['n']}: {n} finding(s) — handing them back", flush=True)
        return ms_verify.build_feedback(
            type("V", (), {"violations": report["violations"], "report": ""})())

    return gate


WORKFLOW_START = "## Recommended Workflow"
WORKFLOW_END = "## Command Execution Rules"


def with_workflow(template: str, workflow: str) -> str:
    start, end = template.find(WORKFLOW_START), template.find(WORKFLOW_END)
    if start < 0 or end < 0 or end < start:
        raise SystemExit(f"cannot find {WORKFLOW_START!r}..{WORKFLOW_END!r} in mini's template; "
                         f"mini-swe-agent's prompt changed and this needs revisiting")
    return template[:start] + WORKFLOW_START + "\n\n" + workflow.strip() + "\n\n" + template[end:]


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    seed = pathlib.Path(os.environ.get("MINI_CFG", "/cfg"), "seed")
    if seed.is_dir():
        for f in sorted(seed.iterdir()):
            shutil.copy2(f, WORK / f.name)
        print(f"[mini_driver] seeded {WORK} with: {', '.join(f.name for f in sorted(seed.iterdir()))}",
              flush=True)

    task = pathlib.Path(os.environ.get("MINI_CFG", "/cfg"), "task.txt").read_text()
    trace = pathlib.Path(os.environ.get("MINI_TRACE", "/trace"))
    trace.mkdir(parents=True, exist_ok=True)
    traj_path = trace / "mini.traj.json"

    version = os.environ.get("MINI_AGENT", "solver-agent-v0")
    version = {"stock": "solver-agent-v0", "ms-agent-v0": "solver-agent-v0",
               "ms-agent-v1": "solver-agent-v1", "ms-agent-v2": "solver-agent-v2",
               "ms-agent-v2-gated": "solver-agent-v2"}.get(version, version)
    try:
        module = importlib.import_module(version.replace("-", "_"))
    except ModuleNotFoundError:
        raise SystemExit(f"unknown MINI_AGENT {version!r} — expected a module agent/{version.replace('-', '_')}.py")

    step_limit = getattr(module, "STEP_LIMIT", int(os.environ.get("MINI_STEP_LIMIT", "0")))
    max_tokens = getattr(module, "MAX_TOKENS_PER_CALL", MAX_TOKENS_PER_CALL)
    env_wall = os.environ.get("MINI_WALL_CLOCK", "")
    wall_clock = "card" if env_wall == "card" else getattr(module, "WALL_CLOCK_SECONDS", int(env_wall or WALL_CLOCK_SECONDS))
    margin = 0 if env_wall == "card" else int(getattr(module, "WALL_CLOCK_MARGIN_SECONDS", 0))
    if wall_clock == "card":
        try:
            import tomllib
            card = float(tomllib.loads(pathlib.Path("/input/card.toml").read_text())["agent"]["timeout_sec"])
        except Exception:
            card = 1800.0
        wall_clock = max(60, int(card) - margin)
    request_budget = int(os.environ.get("MINI_REQUEST_BUDGET", "0") or 0)
    template_kwargs = getattr(module, "TEMPLATE_KWARGS", None)
    if template_kwargs is None and os.environ.get("MINI_TEMPLATE_KWARGS"):
        template_kwargs = json.loads(os.environ["MINI_TEMPLATE_KWARGS"])
    if hasattr(module, "RETRY_ATTEMPTS"):
        os.environ["MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT"] = str(module.RETRY_ATTEMPTS)
    if request_budget:
        os.environ["MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT"] = str(10 ** 9)
    print(f"[mini_driver] limits: step_limit={step_limit} request_budget={request_budget or 'off'} max_tokens={max_tokens} wall_clock={wall_clock} "
          f"retry_attempts={os.environ.get('MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT', 'default')} template_kwargs={template_kwargs}", flush=True)

    base = get_config_from_spec("mini.yaml")
    if system_template := getattr(module, "SYSTEM_TEMPLATE", ""):
        base["agent"]["system_template"] = system_template
        print(f"[mini_driver] system template: {version}'s own, replacing mini's", flush=True)
    if instance_template := getattr(module, "INSTANCE_TEMPLATE", ""):
        base["agent"]["instance_template"] = instance_template
        print(f"[mini_driver] instance template: {version}'s own, replacing mini's", flush=True)
        workflow = ""
    else:
        workflow = getattr(module, "WORKFLOW", "") if os.environ.get("MINI_WORKFLOW") != "stock" else ""
    if workflow:
        base["agent"]["instance_template"] = with_workflow(
            base["agent"]["instance_template"], workflow)
        print(f"[mini_driver] workflow: {version}'s own", flush=True)
    else:
        print("[mini_driver] workflow: mini-swe-agent's own", flush=True)

    config = recursive_merge(
        base,
        {
            "agent": {
                "wall_time_limit_seconds": wall_clock,
                "cost_limit": 0.0,
                "step_limit": step_limit,
                **({"max_consecutive_format_errors": 0} if request_budget else {}),
                "output_path": str(traj_path),
            },
            "environment": {
                "cwd": os.environ.get("MINI_CWD") or "/app",
                "timeout": COMMAND_TIMEOUT_SECONDS,
                "env": {"MODEL_API_KEY": "", "MODEL_TOKEN": "", "MODEL_ENDPOINT": "", "MODEL_NAME": ""},
            },
            "model": {
                "model_name": f"openai/{os.environ['MODEL_NAME']}",
                "model_kwargs": {
                    "api_base": _house_base(),
                    "api_key": _house_token(),
                    "temperature": float(os.environ.get("MINI_TEMPERATURE", "0")),
                    **({"extra_body": {"chat_template_kwargs": template_kwargs}} if template_kwargs else {}),
                    **({"max_retries": 0} if request_budget else {}),
                },
            },
        },
    )
    agent_config = {k: v for k, v in config["agent"].items() if k != "mode"}

    extra = {}
    if "gate" in inspect.signature(module.build).parameters and (gate := _build_gate()):
        extra["gate"] = gate
        extra["max_gate_rounds"] = int(os.environ.get("MINI_GATE_ROUNDS", "1"))
        extra["final_verdict_call"] = os.environ.get("MINI_GATE", "") not in ("reviewer", "outputs", "grader")
    if version == "solver-agent-v1":
        extra["keep_observations"] = int(os.environ.get("MS_KEEP_OBS", module.DEFAULT_KEEP_OBSERVATIONS))
    from minisweagent.agents import default as _mini_default
    _mini_query = _mini_default.DefaultAgent.query

    def _query_without_step_stop(self):
        limit = self.config.step_limit
        self.config.step_limit = 0
        try:
            return _mini_query(self)
        finally:
            self.config.step_limit = limit

    _mini_default.DefaultAgent.query = _query_without_step_stop
    if hasattr(module, "WALL_CLOCK_MARGIN_SECONDS"):
        module.WALL_CLOCK_MARGIN_SECONDS = 0
    model = _redacting_model(LitellmModel(**config["model"]))
    agent = module.build(model,
                         LocalEnvironment(**config["environment"]), **extra, **agent_config)
    if request_budget:
        _request_budget(agent.model, request_budget)
    print(f"[mini_driver] agent version: {version}", flush=True)
    history = pathlib.Path(os.environ.get("MINI_CFG", "/cfg"), "history.json")
    try:
        if history.exists():
            print(f"[mini_driver] resuming from {history}", flush=True)
            REQUESTS_SENT[0] = sum(1 for m in json.loads(history.read_text()) if (m.get("extra") or {}).get("response"))
            agent.resume(task, json.loads(history.read_text()))
        else:
            agent.run(task)
    except Exception as exc:
        print(f"mini-swe-agent raised: {type(exc).__name__}: {exc}", file=sys.stderr)

    print(f"[mini_driver] requests sent: {REQUESTS_SENT[0]} (budget {request_budget or 'off'})", flush=True)
    traj = json.loads(traj_path.read_text()) if traj_path.exists() else {}
    (trace / "stats.json").write_text(json.dumps(_stats(traj), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
