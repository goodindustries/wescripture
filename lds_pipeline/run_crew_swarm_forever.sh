#!/usr/bin/env bash
# Loop: run Crew swarm on pending tasks in diagnostics/crew_events.jsonl
# Optional first: python3 lds_pipeline/ledger_to_crew_feeder.py  (bridge one dispatch-friendly T-* task from task-ledger.jsonl)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="${CREW_PYTHON:-}"
if [[ -z "$PY" && -x "$ROOT/.venv/bin/python" ]]; then PY="$ROOT/.venv/bin/python"; fi
if [[ -z "$PY" ]]; then PY="python3"; fi
exec "$PY" "$ROOT/lds_pipeline/crew_swarm/runner.py" --loop --sleep "${CREW_SWARM_SLEEP:-30}"
