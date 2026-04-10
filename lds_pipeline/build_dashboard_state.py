#!/usr/bin/env python3
"""
Write library/dashboard_state.json for the live dashboard (static site publish dir).

Aggregates:
  - Verse coverage summary from library/verse_coverage.json (run build_verse_coverage.py first)
  - Task counts + claimed work + recent ledger lines from task-ledger.jsonl (repo root)

Netlify only publishes `library/`, so this file must be committed (or produced in CI) for
the deployed dashboard to update.

  python3 lds_pipeline/build_dashboard_state.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))
LIB = REPO / "library"
VC = LIB / "verse_coverage.json"
OUT = LIB / "dashboard_state.json"
LEDGER = REPO / "task-ledger.jsonl"
HB = LIB / "agent_heartbeat.json"

from task_ledger import _load_events, _project  # noqa: E402


def _parse_ts(s: str | None) -> datetime | None:
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def main() -> None:
    now = datetime.now(timezone.utc)

    coverage_summary = None
    if VC.is_file():
        vc = json.loads(VC.read_text(encoding="utf-8"))
        coverage_summary = vc.get("summary")
        cov_gen = vc.get("generated")
    else:
        cov_gen = None

    events = _load_events()
    tasks = _project(events)

    pending = sum(1 for t in tasks.values() if t.get("status") == "pending")
    claimed_list = [t for t in tasks.values() if t.get("status") == "claimed"]
    claimed = len(claimed_list)
    claimed_items = []
    agents_claimed_now: set[str] = set()
    for t in sorted(claimed_list, key=lambda x: x.get("claim_ts") or "", reverse=True):
        ag = t.get("claimed_by")
        if ag:
            agents_claimed_now.add(str(ag))
        claimed_items.append(
            {
                "task_id": t.get("task_id"),
                "agent": t.get("claimed_by"),
                "title": (t.get("title") or "")[:140],
                "claim_ts": t.get("claim_ts"),
            }
        )

    cut24 = now - timedelta(hours=24)
    cut7d = now - timedelta(days=7)
    completed_24h = 0
    agents_7d: set[str] = set()

    for ev in events:
        kind = ev.get("event", ev.get("type", ""))
        if kind not in ("task_completed", "completed"):
            continue
        ts = _parse_ts(ev.get("ts"))
        if ts and ts >= cut24:
            completed_24h += 1
        if ts and ts >= cut7d:
            ag = ev.get("agent") or ev.get("claimed_by")
            if ag:
                agents_7d.add(str(ag))

    recent: list[dict] = []
    for ev in reversed(events[-400:]):
        kind = ev.get("event", ev.get("type", ""))
        if kind not in (
            "task_claimed",
            "task_completed",
            "completed",
            "task_queued",
            "queue",
            "task_registered",
            "task_reopened",
        ):
            continue
        tid = ev.get("task_id", "")
        recent.append(
            {
                "event": kind,
                "task_id": tid,
                "agent": ev.get("agent"),
                "ts": ev.get("ts"),
                "title": (ev.get("title") or "")[:100],
            }
        )
        if len(recent) >= 18:
            break

    last_ev_ts = None
    if events:
        last_ev_ts = events[-1].get("ts")

    heartbeat = None
    if HB.is_file():
        try:
            heartbeat = json.loads(HB.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            heartbeat = {"error": "invalid JSON"}

    doc = {
        "generated": now.replace(microsecond=0).isoformat(),
        "coverage_generated": cov_gen,
        "coverage": coverage_summary,
        "ledger": {
            "last_event_ts": last_ev_ts,
            "pending": pending,
            "claimed": claimed,
            "agents_claimed_now": sorted(agents_claimed_now),
            "claimed_tasks": claimed_items[:24],
            "completed_last_24h": completed_24h,
            "agents_active_7d": sorted(agents_7d),
        },
        "recent_events": recent,
        "heartbeat": heartbeat,
        "notes": {
            "claimed": "Tasks checked out in the ledger (usual proxy: one in-flight task per worker).",
            "heartbeat": "Optional library/agent_heartbeat.json from local runners if you commit it.",
        },
    }

    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}", flush=True)


if __name__ == "__main__":
    main()
