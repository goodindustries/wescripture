#!/usr/bin/env bash
# Start N task_worker.py jobs in parallel, each with a unique ledger agent name.
#
# Prereqs: repo root, git pulled, ANTHROPIC_API_KEY, `claude` on PATH.
#
# Usage:
#   ./lds_pipeline/run_parallel_task_workers.sh        # default 3 workers
#   ./lds_pipeline/run_parallel_task_workers.sh 5
#
# Logs: diagnostics/task-worker-<Agent>.out / .err
#
# Only *pending* tasks are claimable. Stale claims block the queue; reopen with:
#   python3 lds_pipeline/task_ledger.py reopen --task-id T-XXXX --notes "return to pool"

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

N="${1:-3}"
# Extend this list if you need more than 8 parallel Claude workers.
NAMES=(WorkerC WorkerD WorkerE WorkerF WorkerG WorkerH WorkerI WorkerJ)

if ! [[ "$N" =~ ^[0-9]+$ ]] || [ "$N" -lt 1 ]; then
  echo "usage: $0 [count]   # positive integer, default 3, max ${#NAMES[@]}" >&2
  exit 1
fi
if [ "$N" -gt "${#NAMES[@]}" ]; then
  echo "count $N > ${#NAMES[@]} predefined agents — edit NAMES in $0" >&2
  exit 1
fi

mkdir -p diagnostics
echo "Starting $N workers from $ROOT …"
for ((i = 0; i < N; i++)); do
  AG="${NAMES[$i]}"
  OUT="diagnostics/task-worker-${AG}.out"
  ERR="diagnostics/task-worker-${AG}.err"
  echo "  $AG  → $OUT"
  (
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) start $AG ===" >>"$OUT"
    python3 lds_pipeline/task_worker.py --agent "$AG" >>"$OUT" 2>>"$ERR"
    ec=$?
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) exit $ec $AG ===" >>"$OUT"
  ) &
done
wait
echo "All $N workers finished."
