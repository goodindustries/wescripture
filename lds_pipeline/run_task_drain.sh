#!/usr/bin/env bash
# Drain the ledger: run waves of parallel workers until no pending tasks remain.
# Does not run task_scout — use autonomous_runner or task_scout separately to refill.
#
# Usage:
#   ./lds_pipeline/run_task_drain.sh              # wave size = DEFAULT_PARALLEL_WORKERS logic via parallel script
#   ./lds_pipeline/run_task_drain.sh 12           # 12 workers per wave
#
# Env: TASK_WORKER_BACKEND, MAX_PARALLEL_WORKERS (see run_parallel_task_workers.sh)

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

WAVE="${1:-}"
if [ -z "${WAVE}" ]; then
  WAVE=""
fi

wave=0
while true; do
  pending="$(python3 lds_pipeline/task_ledger.py pending-count)"
  if [ "${pending}" -eq 0 ]; then
    echo "Queue empty — no pending tasks. Done."
    exit 0
  fi
  wave=$((wave + 1))
  echo ""
  echo "=== drain wave ${wave} — ${pending} pending ==="
  if [ -n "${WAVE}" ]; then
    ./lds_pipeline/run_parallel_task_workers.sh "${WAVE}"
  else
    ./lds_pipeline/run_parallel_task_workers.sh
  fi
done
