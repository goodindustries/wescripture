#!/usr/bin/env bash
# Local web UI: start/stop workers, ledger + process counts. Binds 127.0.0.1:8765 by default.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 lds_pipeline/agent_ui_server.py "$@"
