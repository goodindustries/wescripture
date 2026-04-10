#!/usr/bin/env bash
# Keep feeding the queue: run orchestrate in a loop. When the ledger is empty,
# sleep and try again (pull + scout may refill from other machines).
# Usage: ./lds_pipeline/run_orchestrate_forever.sh
#        ORCHESTRATE_LOOP_SLEEP=180 ./lds_pipeline/run_orchestrate_forever.sh --backend dispatch --wave-size 8
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
SLEEP="${ORCHESTRATE_LOOP_SLEEP:-120}"
while true; do
  python3 lds_pipeline/orchestrate.py "$@" || true
  echo "$(date -u +"%Y-%m-%dT%H:%M:%SZ") orchestrate exited — sleeping ${SLEEP}s" >> diagnostics/orchestrate-run.out
  sleep "$SLEEP"
done
