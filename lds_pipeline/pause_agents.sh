#!/usr/bin/env bash
# Stop orchestrators and task workers (SIGTERM, then SIGKILL if needed).
# Does not stop track_feed.py (read-only viewer) unless PAUSE_TRACK_FEED=1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

_patterns=(
  '[l]ds_pipeline/orchestrate.py'
  '[r]un_orchestrate_forever'
  '[l]ds_pipeline/task_worker.py'
  '[l]ds_pipeline/autonomous_runner.py'
)
if [[ "${PAUSE_TRACK_FEED:-}" == "1" ]]; then
  _patterns+=('[l]ds_pipeline/track_feed.py')
fi

kill_round() {
  local sig=$1
  for pat in "${_patterns[@]}"; do
    pkill -"$sig" -f "$pat" 2>/dev/null || true
  done
}

echo "pause_agents: sending SIGTERM…"
kill_round TERM
sleep 2
echo "pause_agents: sending SIGKILL to stragglers…"
kill_round 9
echo "pause_agents: done. Remaining (if any):"
pgrep -fl 'orchestrate|task_worker|autonomous_runner|run_orchestrate_forever' 2>/dev/null || echo "  (none)"
