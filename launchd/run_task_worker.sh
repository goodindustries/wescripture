#!/bin/zsh
# Wrapper for task_worker.py — sources env and runs with named agent.
# Usage: run_task_worker.sh [AgentName]

source "$HOME/.zshrc"        2>/dev/null || true
source "$HOME/.zprofile"     2>/dev/null || true
source "$HOME/.zshenv"       2>/dev/null || true
source "$HOME/.profile"      2>/dev/null || true
source "$HOME/.bash_profile" 2>/dev/null || true
source "$HOME/.secrets"      2>/dev/null || true

# Fallback: Keychain
if [[ -z "$ANTHROPIC_API_KEY" ]]; then
    _key="$(security find-generic-password -s ANTHROPIC_API_KEY -a ANTHROPIC_API_KEY -w 2>/dev/null)"
    [[ -n "$_key" ]] && export ANTHROPIC_API_KEY="$_key"
fi

AGENT="${1:-TaskWorker}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO"

# Pull latest before starting work
git pull --ff-only origin main 2>/dev/null || true

exec python3 lds_pipeline/task_worker.py --agent "$AGENT"
