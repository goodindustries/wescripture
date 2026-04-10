#!/usr/bin/env bash
# Start N task_worker.py jobs in parallel, each with a unique ledger agent name.
#
# Prereqs: repo root, git pulled. For --backend hybrid|claude: ANTHROPIC_API_KEY + `claude`.
# Optional: export TASK_WORKER_BACKEND=hybrid  (dispatch + Claude fallback)
#
# Usage:
#   ./lds_pipeline/run_parallel_task_workers.sh           # default wave size (see below)
#   ./lds_pipeline/run_parallel_task_workers.sh 12         # exactly 12 workers
#
# Env:
#   TASK_WORKER_BACKEND   hybrid | dispatch | claude  (default: claude)
#   MAX_PARALLEL_WORKERS  upper cap (default: 16)
#   DEFAULT_PARALLEL_WORKERS  when $1 omitted (default: min(2*CPUs, MAX_PARALLEL_WORKERS))
#
# Logs: diagnostics/task-worker-<Agent>.out / .err
#
# Only *pending* tasks are claimable. Stale claims block the queue; reopen with:
#   python3 lds_pipeline/task_ledger.py reopen --task-id T-XXXX --notes "return to pool"

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MAX="${MAX_PARALLEL_WORKERS:-16}"
CPUS="$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)"
DEF=$(( CPUS * 2 ))
if [ "$DEF" -gt "$MAX" ]; then DEF=$MAX; fi
if [ "$DEF" -lt 1 ]; then DEF=1; fi

N="${1:-$DEF}"

if ! [[ "$N" =~ ^[0-9]+$ ]] || [ "$N" -lt 1 ]; then
  echo "usage: $0 [count]   # positive integer" >&2
  exit 1
fi
if [ "$N" -gt "$MAX" ]; then
  echo "count $N > MAX_PARALLEL_WORKERS=$MAX — raise env MAX_PARALLEL_WORKERS or pass lower count" >&2
  exit 1
fi

mkdir -p diagnostics
BACKEND="${TASK_WORKER_BACKEND:-claude}"
OLLAMA="${OLLAMA_MODEL:-${GENERATE_CHRIST_MODEL:-gemma4:e2b}}"
echo "Starting $N workers from $ROOT (backend=$BACKEND, max=$MAX, OLLAMA_MODEL=$OLLAMA) …"
for ((i = 0; i < N; i++)); do
  AG="$(printf 'Worker%03d' "$i")"
  OUT="diagnostics/task-worker-${AG}.out"
  ERR="diagnostics/task-worker-${AG}.err"
  echo "  $AG  → $OUT"
  (
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) start $AG ===" >>"$OUT"
    python3 lds_pipeline/task_worker.py --backend "$BACKEND" --agent "$AG" >>"$OUT" 2>>"$ERR"
    ec=$?
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) exit $ec $AG ===" >>"$OUT"
  ) &
done
wait
echo "All $N workers finished."
