#!/usr/bin/env bash
# Run pending corpus-related dispatch tasks one worker at a time (avoids parallel correlate).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
# Usage: ./run_corpus_dispatch_wave.sh [max_iterations]   (default 12)
MAX="${1:-12}"
for ((i = 1; i <= MAX; i++)); do
  pending="$(python3 lds_pipeline/task_ledger.py pending-count)"
  if [[ "$pending" -eq 0 ]]; then
    echo "No pending tasks."
    exit 0
  fi
  echo "--- wave $i pending=$pending ---"
  python3 lds_pipeline/task_worker.py \
    --agent "CorpusDispatch-$i" \
    --backend dispatch \
    --no-followup || true
done
