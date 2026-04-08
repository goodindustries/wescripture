#!/usr/bin/env python3
"""
task_worker.py
==============
Autonomous agent that claims the next pending task from the ledger,
delegates it to `claude -p` (Claude Code non-interactive), commits
the result, and marks the task complete.

Designed to run as a one-shot process (cron, launchd, or manually).
Run multiple instances for parallelism — the ledger handles contention.

Usage:
    python3 lds_pipeline/task_worker.py
    python3 lds_pipeline/task_worker.py --agent WorkerB --model sonnet
    python3 lds_pipeline/task_worker.py --dry-run   # claim + print prompt, don't execute

Environment:
    ANTHROPIC_API_KEY  — required by claude CLI
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

REPO   = Path(__file__).resolve().parent.parent
LEDGER = REPO / "lds_pipeline" / "task_ledger.py"
LOG_DIR = REPO / "diagnostics"

DEFAULT_AGENT = "TaskWorker"
DEFAULT_MODEL = "sonnet"   # claude-sonnet-4-6 — strong enough for code tasks
MAX_BUDGET    = "2.00"     # USD cap per task


WORKER_SYSTEM = """\
You are an autonomous task worker for the wescripture project — a scripture
study platform with a large pipeline and a single-file production web app.

Repository layout:
  library/          — deployed web assets (index.html SPA, chapters/, donaldson/, etc.)
  lds_pipeline/     — Python pipeline scripts
  task-ledger.jsonl — append-only task ledger (do NOT edit directly)

Your job:
1. Read the task description carefully.
2. Explore the codebase as needed to understand context before acting.
3. Make the changes required to complete the task.
4. Run any relevant pipeline scripts or tests to verify your work.
5. Stage and commit your changes with a clear commit message.
6. Do NOT mark the task complete in the ledger — the worker script handles that.
7. Do NOT push to origin — the worker script handles that.

If the task is ambiguous or blocked, write a file `diagnostics/task-{task_id}-notes.txt`
explaining what you found and what decision you made, then proceed with your best judgment.

Work precisely and minimally — only change what the task requires.
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run(cmd: list, cwd=None, check=True, capture=False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=cwd or str(REPO),
        capture_output=capture, text=True,
        check=check,
    )


def ledger(args: list, capture=False) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(LEDGER)] + args,
        cwd=str(REPO), capture_output=capture, text=True,
    )


def claim_next(agent):
    result = ledger(["next", "--agent", agent], capture=True)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    # stdout may include "[ledger] pushed to origin" before the JSON line
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith('{'):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
    return None


def build_prompt(task: dict) -> str:
    tid   = task.get("task_id", "")
    title = task.get("title", "")
    desc  = task.get("description", "")
    notes = task.get("notes", "")

    prompt = textwrap.dedent(f"""\
        {WORKER_SYSTEM}

        ---

        TASK {tid}: {title}
        """)

    if desc and desc != title:
        prompt += f"\nDescription:\n{desc}\n"
    if notes:
        prompt += f"\nAdditional context:\n{notes}\n"

    prompt += textwrap.dedent(f"""
        ---

        Complete this task now. Explore the codebase first if needed.
        Stage and commit your changes when done.
        Task ID for your commit message: {tid}
        """)
    return prompt


def git_commit_for_task(task_id, title):
    """Return the hash of any new commit made since the task was claimed, or None."""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=str(REPO), capture_output=True, text=True, check=True,
        )
        return result.stdout.split()[0] if result.stdout.strip() else None
    except Exception:
        return None


def push_origin():
    try:
        run(["git", "push", "origin", "main"])
        print("  pushed to origin", flush=True)
    except subprocess.CalledProcessError as e:
        print(f"  push failed (non-fatal): {e}", flush=True)


def log_run(task_id: str, agent: str, outcome: str, notes: str = ""):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    path = LOG_DIR / f"task-worker-{agent}.log"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "ts":      utc_now(),
            "task_id": task_id,
            "agent":   agent,
            "outcome": outcome,
            "notes":   notes,
        }) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Autonomous task worker for wescripture.")
    parser.add_argument("--agent",     default=DEFAULT_AGENT, help="Agent name for ledger")
    parser.add_argument("--model",     default=DEFAULT_MODEL, help="Claude model alias or full ID")
    parser.add_argument("--budget",    default=MAX_BUDGET,    help="Max USD spend per task")
    parser.add_argument("--dry-run",   action="store_true",   help="Claim task, print prompt, don't run claude")
    args = parser.parse_args()

    # ── Claim next task ───────────────────────────────────────────────────────
    print(f"[{args.agent}] checking for pending tasks…", flush=True)
    task = claim_next(args.agent)
    if not task:
        print(f"[{args.agent}] no pending tasks — exiting.", flush=True)
        sys.exit(0)

    tid   = task["task_id"]
    title = task["title"]
    print(f"[{args.agent}] claimed {tid}: {title}", flush=True)

    # ── Build prompt ──────────────────────────────────────────────────────────
    prompt = build_prompt(task)

    if args.dry_run:
        print("\n── PROMPT ──────────────────────────────────────────────────")
        print(prompt)
        print("── END PROMPT ──────────────────────────────────────────────")
        print("\n[dry-run] not executing claude.", flush=True)
        # Release the claim so it stays pending
        ledger(["reopen", "--task-id", tid, "--notes", "dry-run: claim released"])
        sys.exit(0)

    # ── Record commit hash before execution ───────────────────────────────────
    pre_commit = git_commit_for_task(tid, title)

    # ── Run claude -p ─────────────────────────────────────────────────────────
    print(f"[{args.agent}] running claude --model {args.model} …", flush=True)
    claude_result = subprocess.run(
        [
            "claude", "-p",
            "--model", args.model,
            "--max-budget-usd", args.budget,
            "--dangerously-skip-permissions",
            prompt,
        ],
        cwd=str(REPO),
        text=True,
    )

    success = claude_result.returncode == 0

    # ── Check if a new commit was made ────────────────────────────────────────
    post_commit = git_commit_for_task(tid, title)
    new_commit  = post_commit if post_commit != pre_commit else ""

    # ── Mark complete in ledger ───────────────────────────────────────────────
    complete_args = [
        "complete", "--task-id", tid,
        "--agent", args.agent,
    ]
    if new_commit:
        complete_args += ["--commit", new_commit]
    complete_args += ["--notes", "completed by task_worker" + ("" if success else " (non-zero exit)")]

    ledger(complete_args)

    # ── Push ──────────────────────────────────────────────────────────────────
    push_origin()

    outcome = "success" if success else "error"
    log_run(tid, args.agent, outcome, f"commit={new_commit}")
    print(f"[{args.agent}] {tid} {outcome}. commit={new_commit}", flush=True)


if __name__ == "__main__":
    main()
