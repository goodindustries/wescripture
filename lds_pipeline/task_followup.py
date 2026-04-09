#!/usr/bin/env python3
"""
task_followup.py
================
After a task completes, propose ONE follow-on task from git + ledger context
using a local Ollama model (default gemma4:e2b). Appends task_queued and optionally
pushes the ledger.

    python3 lds_pipeline/task_followup.py --task-id T-0123 --commit abc1234 --push
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from task_ledger import _append, _load_events, _project, _push_ledger, utc_now

REPO = Path(__file__).resolve().parent.parent
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "gemma4:e2b"
TIMEOUT_S = 120

SYSTEM = """You are the task planner for a scripture library codebase (wescripture).
Given what was just completed and what changed in git, output exactly ONE JSON object, no markdown fences:
{"title":"<short actionable title under 110 chars>","notes":"<specific next step: files, scripts, acceptance>"}

Rules:
- Ground the task in what you observed in the diff or task text — not generic advice.
- One task only. Title must be unique-ish (name a file, book, or subsystem).
- Prefer MISSION.md north star: clean text, clicks, semantic links, plain English, entity registries.
- If nothing concrete is left to do, use title "Scout: run task_scout.py" and notes explaining why."""

PROMPT = """Completed task:
Title: {title}
Notes: {notes}

Git commit: {commit}
---
git show --stat:
{stat}
---
Patch excerpt (truncated):
{patch}
"""


def ollama_json(model: str, prompt: str) -> dict | None:
    payload = json.dumps(
        {
            "model": model,
            "prompt": f"{SYSTEM}\n\n{prompt}",
            "stream": False,
            "options": {"temperature": 0.35, "num_predict": 400},
        }
    ).encode()
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            raw = json.loads(resp.read()).get("response", "")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"task_followup: Ollama error: {e}", file=sys.stderr)
        return None

    raw = raw.strip()
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL | re.I)
    i = raw.find("{")
    if i < 0:
        print("task_followup: could not find JSON object in model output", file=sys.stderr)
        return None
    depth = 0
    blob = None
    for j in range(i, len(raw)):
        if raw[j] == "{":
            depth += 1
        elif raw[j] == "}":
            depth -= 1
            if depth == 0:
                blob = raw[i : j + 1]
                break
    if not blob:
        print("task_followup: unbalanced JSON in model output", file=sys.stderr)
        return None
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        print("task_followup: invalid JSON", file=sys.stderr)
        return None


def open_titles() -> set[str]:
    tasks = _project(_load_events())
    return {
        t["title"]
        for t in tasks.values()
        if t.get("status") in ("pending", "claimed") and t.get("title")
    }


def next_task_id() -> int:
    nums = [
        int(t[2:])
        for t in {e.get("task_id") for e in _load_events()}
        if isinstance(t, str) and t.startswith("T-") and t[2:].isdigit()
    ]
    return (max(nums) + 1) if nums else 1


def git_text(argv: list[str]) -> str:
    r = subprocess.run(
        ["git"] + argv,
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    return (r.stdout or "") + (r.stderr or "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task-id", required=True)
    ap.add_argument("--commit", default="", help="Short or full commit hash (optional)")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tasks = _project(_load_events())
    t = tasks.get(args.task_id)
    if not t:
        print(f"task_followup: unknown task {args.task_id}", file=sys.stderr)
        sys.exit(1)

    commit = args.commit or git_text(["rev-parse", "--short", "HEAD"]).strip() or "HEAD"
    stat = git_text(["show", "-s", "--format=fuller", commit])
    stat += "\n" + git_text(["show", "--stat", commit])
    patch = git_text(["show", "-p", "--max-count=1", commit])
    if len(patch) > 14000:
        patch = patch[:14000] + "\n… [truncated]"

    prompt = PROMPT.format(
        title=t.get("title", ""),
        notes=(t.get("notes") or "")[:2000],
        commit=commit,
        stat=stat[:8000],
        patch=patch,
    )

    if args.dry_run:
        print(prompt[:6000])
        return

    data = ollama_json(args.model, prompt)
    if not data:
        sys.exit(2)

    title = (data.get("title") or "").strip()
    notes = (data.get("notes") or "").strip()
    if not title:
        print("task_followup: empty title", file=sys.stderr)
        sys.exit(2)

    ot = open_titles()
    if title in ot:
        title = f"{title} (follow-up)"

    entry = {
        "ts": utc_now(),
        "event": "task_queued",
        "task_id": f"T-{next_task_id():04d}",
        "title": title,
        "notes": notes or f"Spawned after {args.task_id} (commit {commit}).",
    }
    _append(entry)
    print(f"task_followup: queued {entry['task_id']}: {title[:90]}")
    if args.push:
        _push_ledger()


if __name__ == "__main__":
    main()
