#!/usr/bin/env bash
# Repo-root-friendly wrapper. Same as: python3 lds_pipeline/orchestrate.py "$@"
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec python3 lds_pipeline/orchestrate.py "$@"
