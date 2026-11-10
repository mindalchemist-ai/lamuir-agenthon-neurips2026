# Agenthon 2026 Track 1 (Quant-Finance Coding Agents) — Team MindAlchemist

This repository reproduces Team MindAlchemist's Final submission to Track 1 (Quant-Finance Coding Agents) of
[Agenthon 2026: Verifiable AI for Quantitative Finance](https://www.agenthon.net/), part of the
NeurIPS 2026 Competition Track. The submission placed 3rd on the hidden test set, with the same
score as the 1st- and 2nd-place teams.

The agent is a coding agent for quantitative finance. All reasoning and code come from NVIDIA
Nemotron 3 Super (`nvidia/nemotron-3-super-120b-a12b`). It reads a task and its data, writes and runs
Python in a persistent session, and returns the files the task asks for.

## What is in this repository

| Path | Contents |
|---|---|
| `image/` | The code exactly as it sits under `/opt` in the submitted Final image, and the Dockerfile that built that image |
| `MANIFEST.sha256` | SHA-256 of every file in `image/` (excluding the Dockerfile), taken from the submitted image |
| `env/` | The submitted image's Python packages (`pip-freeze-compute.txt` for the interpreter that runs the model's code, `pip-freeze-agent.txt` for the agent's own environment) and its image configuration |
| `base/` | The recipe of the base image the Dockerfile builds on, for reference |
| `scripts/verify_rebuild.sh` | Rebuilds the image from `image/` and checks it against the submitted image |
| `scripts/run_unit.sh` | Runs the agent on one task unit with the platform's container settings |
| `scripts/request_cap_proxy.py` | Reproduces the competition's model limits (25 requests per task, 4,000 output tokens per request) when the model is served by another provider |

### Code layout (`image/`)

| File or folder | Role |
|---|---|
| `solve.py` | Container entry point: `solve --task-dir /input --out /app/output`. Builds the task text and starts the driver |
| `mini_driver.py` | Builds the mini-swe-agent model, environment and agent with the run settings |
| `solver_agent_v205l.py` | The agent: persistent Python session, retrieval of reference cards, output requirements and result checks |
| `peek_data_v7.py` | Data preview shown to the model before its first request |
| `msw/` | Helpers for reading the task text and its output requirements |
| `msw_session/` | Modules importable from the model's Python session (file reading, backtest helpers) |
| `qfref/` | Reference cards (`qfref/qfref/entries/`), library reference material, the retrieval index and output checks |

## Reproducing the submission

### Option 1: run the submitted image (exact)

The Final submission ran this image, pinned by digest. Pulling it by digest gives the same bytes
the organizers ran:

```bash
docker pull --platform linux/amd64 ghcr.io/tidewell-labs/pebble@sha256:2946c4de3fadb6931d8037c455a5911c56cbd6d100089dad96a27c96034066ad
```

### Option 2: rebuild from this repository and verify

```bash
scripts/verify_rebuild.sh
```

The script builds `image/` for `linux/amd64` and checks that:

1. the files in `image/` match `MANIFEST.sha256`;
2. the files under `/opt` in both the submitted image and the rebuilt image match `MANIFEST.sha256`;
3. both Python environments in the rebuilt image match the submitted image and `env/`;
4. the image configuration (entry point, environment variables, labels, working directory) matches.

The rebuilt image's digest differs from the submitted one because build metadata such as timestamps
differs; file contents, packages and configuration are identical. The Dockerfile builds on a base
image pinned by digest (`ghcr.io/tidewell-labs/pebble@sha256:03a64abc…`), which is publicly pullable.
`base/` holds the recipe that base image was built from (`base.Dockerfile`, `requirements.txt`,
`constraints.txt`, `runtime.Dockerfile`). A rebuild of the base from scratch pulls newer operating-system
packages and is not byte-identical, so use the pinned digest to reproduce the submission.

Building `linux/amd64` on an ARM machine runs under emulation. Emulated CPUs may lack AVX, which some
compiled libraries need at import time; run the agent itself on an x86-64 machine.

## Running the agent on a task unit

1. Get the public practice units from the official repository
   [Agenthon-2026/track1-coding-public](https://github.com/Agenthon-2026/track1-coding-public) (`units/`).
   The units are not included here; they are licensed separately and carry contamination canaries.
2. Provide an OpenAI-compatible endpoint serving `nvidia/nemotron-3-super-120b-a12b`. During the
   competition this was the organizers' House route, which is not public. Any provider of the same model
   with an OpenAI-compatible API under `/v1` works; results may differ with a different serving stack.
3. Start the limit proxy. The image does not limit its own requests or output length: on the competition
   platform the House route admitted at most 25 requests per task, retries included, and refused later ones (the
   agent submits its files when that happens), and it applied at most 4,000 output tokens per request (the agent
   sends no `max_tokens`, which the House route read as 4,000). Other providers have no request cap and apply their
   own default output limit, so without the proxy the agent gets more than it could in the competition. The proxy
   refuses requests after the 25th and sets `max_tokens` to at most 4,000 on every request. Start one proxy per task:

```bash
python3 scripts/request_cap_proxy.py --upstream https://<provider-origin> --port 8025 --host 172.17.0.1
```

   `172.17.0.1` is the usual address of the Docker bridge on the host; check yours with
   `docker network inspect bridge --format '{{(index .IPAM.Config 0).Gateway}}'`.

4. Run the task, pointing the agent at the proxy:

```bash
export MODEL_ENDPOINT=http://172.17.0.1:8025       # the proxy; the API is called at $MODEL_ENDPOINT/v1
export MODEL_NAME=nvidia/nemotron-3-super-120b-a12b
export MODEL_TOKEN=<your API key>
scripts/run_unit.sh <path-to-unit> <output-dir>
```

   Stop the proxy after the task and start a fresh one for the next task, so that each task gets its own 25 requests.

The unit's own checks (`checks/` in the official repository) score the output directory. Build the unit image
from the unit's `environment/` folder (it is `FROM finance-bench-sandbox:latest`, built from the official
`docker/sandbox.Dockerfile`), then run the checks with the unit at `/input` and, when the unit has
`checks/reference_data/`, that folder at `/tests/reference_data`; several checks read their reference values
from there and fail or pass vacuously without it:

```bash
docker build -t unit-<name> <path-to-unit>/environment
docker run --rm --network=none -e OUTPUT_DIR=/app/output \
  -v <path-to-unit>:/input:ro -v <path-to-unit>/checks/reference_data:/tests/reference_data:ro \
  -v <output-dir>:/app/output -v <output-dir>:/output \
  unit-<name> bash /input/checks/test.sh
```

Leave out the `/tests/reference_data` mount for units without `checks/reference_data/`. The result is in `<output-dir>/reward.json` (`"reward": 1.0` when every check passes). The official
repository publishes only `docker/sandbox.Dockerfile` (on the floating `python:3.13-slim` tag) and
`docker/requirements-sandbox.txt` with minimum versions (for example `pandas>=2.1`); it publishes no lock file,
no prebuilt sandbox image and no exact versions. A build today therefore installs newer packages than a build
during the competition (on 2026-11-08 it installed pandas 3.1.1 and numpy 2.5.4). `env/pip-freeze-compute.txt`
is the package list of the official sandbox as we built it from that Dockerfile on 2026-09-08, during the
Development phase (pandas 3.0.5, numpy 2.5.3); it matches the submitted image package for package. To score
under the same versions, pin the sandbox to that list, for example by building
`FROM finance-bench-sandbox:latest` with `RUN pip install -r pip-freeze-compute.txt` and uninstalling any package
the list does not contain (on 2026-11-08 that was `tzdata`); `pip list --format=freeze` should then match the file.

### Run settings in the submitted image

These come from `solve.py`, `mini_driver.py` and `solver_agent_v205l.py` and are unchanged:

- temperature 0, `chat_template_kwargs = {"low_effort": true}`;
- at most 25 model requests per task, counted with retries, and at most 4,000 output tokens per request, both
  enforced by the competition's model route rather than by the image (use `scripts/request_cap_proxy.py` elsewhere);
- the time limit is the task card's `[agent].timeout_sec`;
- the container runs with a read-only root, as user 65534, with a 64 MiB non-executable `/tmp`.

## Reproduction check (2026-11-08)

We followed this README on a fresh x86-64 cloud VM (Ubuntu 24.04, 4 vCPUs):

- `scripts/verify_rebuild.sh` passed all nine checks: the rebuilt image matches the submitted image in every
  file under `/opt` that this repository ships, in both Python environments and in its configuration.
- We ran the submitted image on all 86 public practice units with `scripts/run_unit.sh` and the model
  `nvidia/nemotron-3-super-120b-a12b` served by Nebius Token Factory; every run exited normally and wrote its
  deliverables.

## Notes on reproducibility

- **Model output varies between runs.** Even at temperature 0 the served model is not fully
  deterministic, so per-task pass/fail can change between runs of the same image. For Track 1 the
  organizers' rerun requires the same image and program, not the same model answers.
- **Development-time paths.** A few analysis modules under `qfref/qfref/` contain default paths from the
  development machine (`/Users/...`); they are overridable through environment variables and are kept
  unchanged so that this repository stays byte-identical to the submitted image.

## License

Apache License 2.0, see [LICENSE](LICENSE). Third-party components keep their own licenses; see
[NOTICE](NOTICE).

## Team

MindAlchemist: Xiangyu Gong and Maosheng Guo.
