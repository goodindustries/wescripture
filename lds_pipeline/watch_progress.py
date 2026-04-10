#!/usr/bin/env python3
"""
Terminal dashboard: pending/claimed/completed counts, in-flight tasks, recent ledger lines.
  python3 lds_pipeline/watch_progress.py          # refresh every 5s
  python3 lds_pipeline/watch_progress.py 10       # every 10s
  python3 lds_pipeline/watch_progress.py 0        # once, no loop
"""

from __future__ import annotations

import os
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))
from orchestrate_hints import format_claim_report, site_base, ui_hints_for_task_title  # noqa: E402
from task_ledger import _load_events, _project  # noqa: E402


def clear() -> None:
    os.system("clear" if os.name != "nt" else "cls")


def run_once() -> None:
    from datetime import datetime, timezone

    events = _load_events()
    tasks = _project(events)
    counts = Counter(t["status"] for t in tasks.values())

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    base = site_base()
    print(f"  WeScripture ledger  ·  {now}")
    print(f"  Deployed UI base: {base}  (WESCRIPTURE_SITE_URL)")
    print("=" * 72)
    print("  COUNTS")
    for status in ("pending", "claimed", "completed", "noted"):
        n = counts.get(status, 0)
        if n or status in ("pending", "claimed", "completed"):
            print(f"    {status:12} {n}")
    print(f"    {'total':12} {len(tasks)}")

    pending_n = counts.get("pending", 0)
    claimed_n = counts.get("claimed", 0)
    print()
    print("  QUEUE")
    print(f"    claimable (pending): {pending_n}   ·   in-flight (claimed): {claimed_n}")

    claimed = [t for t in tasks.values() if t.get("status") == "claimed"]
    claimed.sort(key=lambda x: x.get("claim_ts") or "", reverse=True)
    print()
    print("  IN-FLIGHT (claimed)")
    if not claimed:
        print("    — none —")
    else:
        for t in claimed[:12]:
            tid = t.get("task_id", "")
            ag = t.get("claimed_by") or "?"
            title = (t.get("title") or "")[:68]
            ts = (t.get("claim_ts") or "")[:19]
            print(f"    {tid}  {ag:12}  {ts}")
            print(f"           {title}")
            for h in ui_hints_for_task_title(t.get("title") or ""):
                print(f"           → {h}")

    pend = [t for t in tasks.values() if t.get("status") == "pending"]
    pend.sort(key=lambda x: x.get("task_id") or "")
    print()
    print(f"  NEXT PENDING (showing up to 8 of {len(pend)})")
    if not pend:
        print("    — none —")
    else:
        for t in pend[:8]:
            tid = t.get("task_id", "")
            title = (t.get("title") or "")[:64]
            print(f"    {tid}  {title}")
            for h in ui_hints_for_task_title(t.get("title") or ""):
                print(f"           → {h}")

    print()
    print("  WORKER LOGS (last claim per Worker*.out)")
    diag = REPO / "diagnostics"
    for line in format_claim_report(diag).split("\n"):
        print(f"    {line}")

    print()
    print("  QUICK TEST LINKS")
    print(f"    App:   {base}/index.html")
    print(f"    Test:  {base}/test.html")
    print(f"    Ops:   {base}/dashboard.html")
    print(f"    Cover: {base}/verse_coverage.html")

    print()
    print("  RECENT LEDGER (last 12 events)")
    for ev in events[-12:]:
        kind = ev.get("event", ev.get("type", "?"))
        tid = ev.get("task_id", "")
        ag = ev.get("agent", "")
        ts = (ev.get("ts", "") or "")[:19]
        extra = ""
        if kind in ("task_completed", "completed", "task_claimed"):
            extra = f"  {ag}" if ag else ""
        print(f"    {ts}  {kind:16}  {tid}{extra}")

    print()
    print("=" * 72)


def main() -> None:
    interval = 5.0
    if len(sys.argv) > 1:
        interval = float(sys.argv[1])

    try:
        while True:
            clear()
            run_once()
            if interval <= 0:
                break
            print(f"\n  Refreshing every {interval:g}s…  (Ctrl+C to stop)")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
