#!/usr/bin/env bash
# Run the agent on one Track 1 unit the way the Agenthon 2026 platform did:
# read-only root, unprivileged user, a small non-executable /tmp, the unit mounted at /input.
# Usage: MODEL_ENDPOINT=... MODEL_NAME=... MODEL_TOKEN=... scripts/run_unit.sh <unit_dir> <output_dir> [image]
set -euo pipefail

UNIT="$(cd "$1" && pwd)"
mkdir -p "$2"
OUT="$(cd "$2" && pwd)"
IMAGE="${3:-ghcr.io/tidewell-labs/pebble@sha256:2946c4de3fadb6931d8037c455a5911c56cbd6d100089dad96a27c96034066ad}"
: "${MODEL_ENDPOINT:?set MODEL_ENDPOINT, the origin of an OpenAI-compatible API served under /v1}"
: "${MODEL_NAME:?set MODEL_NAME, e.g. nvidia/nemotron-3-super-120b-a12b}"
: "${MODEL_TOKEN:?set MODEL_TOKEN, the bearer token for MODEL_ENDPOINT}"
chmod 777 "$OUT"

docker run --rm --platform linux/amd64 \
  --read-only --user 65534:65534 --cap-drop=ALL --pids-limit 256 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m \
  -e MODEL_ENDPOINT -e MODEL_NAME -e MODEL_TOKEN \
  -v "$UNIT:/input:ro" -v "$OUT:/app/output" -v "$OUT:/output" \
  "$IMAGE" solve --task-dir /input --out /app/output
