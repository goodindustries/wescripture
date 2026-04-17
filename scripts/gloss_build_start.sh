#!/usr/bin/env bash
# Start the deep gloss pipeline in the background (Ollama + build_shared_gloss.py).
# Idempotent: if a PID in diagnostics/gloss-build.pid is still alive, exits 0 and prints tail hint.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
LOG="${ROOT}/diagnostics/gloss-build-run.log"
PIDF="${ROOT}/diagnostics/gloss-build.pid"
STATE="${ROOT}/diagnostics/gloss-build-state.json"
PUBLIC_STATE="${ROOT}/library/assets/gloss/_build_state.json"

mkdir -p "${ROOT}/diagnostics"

if [[ -f "$PIDF" ]]; then
  OLD="$(cat "$PIDF" 2>/dev/null || true)"
  if [[ -n "${OLD:-}" ]] && kill -0 "$OLD" 2>/dev/null; then
    echo "Gloss build already running (PID $OLD)."
    echo "  tail -f $LOG"
    echo "  cat $STATE"
    exit 0
  fi
fi

# Refuse a second copy even if gloss-build.pid was overwritten (prevents shard races).
if pgrep -f "lds_pipeline/build_shared_gloss.py" >/dev/null 2>&1; then
  echo "Another build_shared_gloss.py is already running:"
  pgrep -lf "lds_pipeline/build_shared_gloss.py" || true
  echo "Stop it first (or wait for completion) before starting again."
  exit 1
fi

if ! curl -s --max-time 4 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Ollama not reachable at 127.0.0.1:11434. Start: ollama serve &"
  exit 1
fi

export OLLAMA_NUM_PARALLEL="${OLLAMA_NUM_PARALLEL:-1}"
export OLLAMA_MAX_LOADED_MODELS="${OLLAMA_MAX_LOADED_MODELS:-1}"

MODEL="${GLOSS_MODEL:-qwen3:1.7b}"
set -- --model "$MODEL"
[[ "${GLOSS_FORCE:-}" == "1" ]] && set -- "$@" --force
[[ -n "${GLOSS_LIMIT:-}" ]] && set -- "$@" --limit "$GLOSS_LIMIT"

{
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) starting gloss build model=$MODEL ==="
} >>"$LOG"

nohup python3 -u "${ROOT}/lds_pipeline/build_shared_gloss.py" "$@" >>"$LOG" 2>&1 &
echo $! >"$PIDF"
echo "Started PID $(cat "$PIDF") (model $MODEL)"
echo "  Log:        $LOG"
echo "  State:      $STATE"
echo "  Web state:  $PUBLIC_STATE"
echo "  Monitor:    open repo root gloss-monitor.html or /gloss-monitor after deploy"
echo "  Follow:     tail -f $LOG"
