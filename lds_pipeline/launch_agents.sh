#!/usr/bin/env bash
# Default: multi-worker orchestration (pull → scout → parallel waves). See lds_pipeline/orchestrate.py
# Legacy single-threaded loop (one task_worker per iteration): ./lds_pipeline/launch_agents.sh --legacy …
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ "${1:-}" == "--legacy" ]]; then
  shift
  exec python3 lds_pipeline/autonomous_runner.py "$@"
fi
exec python3 lds_pipeline/orchestrate.py "$@"
