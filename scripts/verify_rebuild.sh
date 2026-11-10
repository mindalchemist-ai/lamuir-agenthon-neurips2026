#!/usr/bin/env bash
# Rebuild the agent image from image/ and check it against the submitted Final image:
# every file under /opt that this repository ships, both Python environments, and the image config.
set -euo pipefail

ORIGINAL="ghcr.io/tidewell-labs/pebble@sha256:2946c4de3fadb6931d8037c455a5911c56cbd6d100089dad96a27c96034066ad"
REBUILT="${REBUILT:-agenthon2026-track1-rebuild:local}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PATHS="solve.py mini_driver.py solver_agent_v205l.py peek_data_v7.py msw msw_session qfref"

docker pull --platform linux/amd64 "$ORIGINAL" >/dev/null
docker build --platform linux/amd64 -t "$REBUILT" "$ROOT/image"

opt_hashes() {
  docker run --rm --platform linux/amd64 --entrypoint sh "$1" -c \
    "cd /opt && find $PATHS -type f | xargs sha256sum" | LC_ALL=C sort -k2
}
freeze() {
  docker run --rm --platform linux/amd64 --entrypoint "$2" "$1" -m pip list --format=freeze | LC_ALL=C sort -f
}
config() {
  docker image inspect "$1" --format '{{json .Config}}' | python3 -c \
    'import json,sys; c=json.load(sys.stdin); print(json.dumps({k: c.get(k) for k in ["Entrypoint","Cmd","Env","Labels","WorkingDir","User","Volumes"]}, indent=1, sort_keys=True))'
}

status=0
check() {
  if diff -u "$2" "$3" >"$WORK/diff.txt"; then
    echo "PASS  $1"
  else
    echo "FAIL  $1"; head -40 "$WORK/diff.txt"; status=1
  fi
}

LC_ALL=C sort -k2 "$ROOT/MANIFEST.sha256" >"$WORK/manifest"
for name in original rebuilt; do
  image=$([ "$name" = original ] && echo "$ORIGINAL" || echo "$REBUILT")
  opt_hashes "$image" >"$WORK/$name.opt"
  freeze "$image" /usr/local/bin/python >"$WORK/$name.compute"
  freeze "$image" /opt/agent/bin/python >"$WORK/$name.agent"
  config "$image" >"$WORK/$name.config"
done
python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])), indent=1, sort_keys=True))' \
  "$ROOT/env/image-config.json" >"$WORK/recorded.config"

check "repository files match MANIFEST.sha256"            "$WORK/manifest"                 <(cd "$ROOT/image" && find . -type f ! -name Dockerfile | sed 's|^\./||' | LC_ALL=C sort | while read -r f; do shasum -a 256 "$f"; done | LC_ALL=C sort -k2)
check "original image /opt matches MANIFEST.sha256"       "$WORK/manifest"                 "$WORK/original.opt"
check "rebuilt image /opt matches MANIFEST.sha256"        "$WORK/manifest"                 "$WORK/rebuilt.opt"
check "compute environment (pip) matches the original"    "$WORK/original.compute"         "$WORK/rebuilt.compute"
check "compute environment matches env/pip-freeze-compute.txt" "$ROOT/env/pip-freeze-compute.txt" "$WORK/rebuilt.compute"
check "agent environment (pip) matches the original"      "$WORK/original.agent"           "$WORK/rebuilt.agent"
check "agent environment matches env/pip-freeze-agent.txt" "$ROOT/env/pip-freeze-agent.txt" "$WORK/rebuilt.agent"
check "image config matches the original"                 "$WORK/original.config"          "$WORK/rebuilt.config"
check "image config matches env/image-config.json"        "$WORK/recorded.config"          "$WORK/rebuilt.config"

[ "$status" = 0 ] && echo "All checks passed: the rebuilt image is equivalent to the submitted Final image." || echo "Some checks failed."
exit "$status"
