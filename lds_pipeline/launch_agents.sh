#!/usr/bin/env bash
# Start the autonomous agent loop from repo root (pull → scout refill → hybrid worker).
# Example: ./lds_pipeline/launch_agents.sh
# Example: ./lds_pipeline/launch_agents.sh --once --no-followup
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 lds_pipeline/autonomous_runner.py "$@"
