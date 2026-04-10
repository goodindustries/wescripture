"""Append-only JSONL queue for Crew swarm (separate from task-ledger.jsonl)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent.parent
CREW_EVENTS = REPO / "diagnostics" / "crew_events.jsonl"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _append(entry: dict) -> None:
    CREW_EVENTS.parent.mkdir(parents=True, exist_ok=True)
    if "ts" not in entry:
        entry["ts"] = utc_now()
    with CREW_EVENTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_events() -> list[dict]:
    if not CREW_EVENTS.is_file():
        return []
    out: list[dict] = []
    for line in CREW_EVENTS.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def project_tasks(events: list[dict]) -> dict[str, dict[str, Any]]:
    """Derive latest state per task_id from events."""
    tasks: dict[str, dict[str, Any]] = {}
    for ev in events:
        tid = ev.get("task_id")
        if not tid:
            continue
        cur = tasks.setdefault(tid, {"task_id": tid})
        kind = ev.get("event", "")
        if kind == "task_queued":
            cur["status"] = "pending"
            cur["title"] = ev.get("title", "")
            cur["notes"] = ev.get("notes", "")
            cur["queued_ts"] = ev.get("ts", "")
        elif kind == "task_claimed":
            cur["status"] = "claimed"
            cur["claimed_by"] = ev.get("agent", "")
            cur["claim_ts"] = ev.get("ts", "")
        elif kind == "task_completed":
            cur["status"] = "completed"
            cur["completed_ts"] = ev.get("ts", "")
            cur["summary"] = ev.get("summary", "")
            cur["commit"] = ev.get("commit", "")
        elif kind == "task_failed":
            cur["status"] = "failed"
            cur["failed_ts"] = ev.get("ts", "")
            cur["error"] = ev.get("error", "")
    return tasks


def next_pending(events: list[dict] | None = None) -> dict[str, Any] | None:
    evs = events if events is not None else load_events()
    tasks = project_tasks(evs)
    pend = [t for t in tasks.values() if t.get("status") == "pending"]
    if not pend:
        return None
    pend.sort(key=lambda x: x.get("task_id") or "")
    return pend[0]


def enqueue_task(title: str, notes: str = "") -> str:
    events = load_events()
    existing_ids = set(project_tasks(events).keys())
    nums = [int(t[2:]) for t in existing_ids if t.startswith("C-") and t[2:].isdigit()]
    nxt = (max(nums) + 1) if nums else 1
    task_id = f"C-{nxt:04d}"
    _append(
        {
            "event": "task_queued",
            "task_id": task_id,
            "title": title,
            "notes": notes,
        }
    )
    return task_id


def append_completed(
    task_id: str,
    summary: str,
    commit: str = "",
    agent: str = "CrewSwarm",
) -> None:
    _append(
        {
            "event": "task_completed",
            "task_id": task_id,
            "agent": agent,
            "summary": summary,
            "commit": commit,
        }
    )


def append_failed(task_id: str, error: str, agent: str = "CrewSwarm") -> None:
    _append(
        {
            "event": "task_failed",
            "task_id": task_id,
            "agent": agent,
            "error": error,
        }
    )


def append_claimed(task_id: str, agent: str) -> None:
    _append(
        {
            "event": "task_claimed",
            "task_id": task_id,
            "agent": agent,
        }
    )


def completions_since(since_iso: str | None, limit: int = 80) -> list[dict]:
    """task_completed events newer than since_iso (or all if blank/invalid)."""
    events = load_events()
    since_ts = 0.0
    if since_iso:
        try:
            since_ts = datetime.fromisoformat(since_iso.replace("Z", "+00:00")).timestamp()
        except ValueError:
            since_ts = 0.0
    out: list[dict] = []
    for ev in reversed(events):
        if ev.get("event") != "task_completed":
            continue
        ts = ev.get("ts") or ""
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except ValueError:
            t = 0.0
        if t > since_ts:
            out.append(
                {
                    "ts": ts,
                    "task_id": ev.get("task_id", ""),
                    "summary": ev.get("summary", ""),
                    "commit": ev.get("commit", ""),
                    "agent": ev.get("agent", ""),
                }
            )
        if len(out) >= limit:
            break
    out.reverse()
    return out


def latest_completion_ts() -> str | None:
    events = load_events()
    best = None
    best_t = 0.0
    for ev in events:
        if ev.get("event") != "task_completed":
            continue
        ts = ev.get("ts") or ""
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except ValueError:
            continue
        if t >= best_t:
            best_t = t
            best = ts
    return best
