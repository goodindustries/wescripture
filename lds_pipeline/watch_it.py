#!/usr/bin/env python3
"""
One screen: ledger counts + are agent processes alive + tail of local feed.

  python3 lds_pipeline/watch_it.py           # refresh every 5s
  python3 lds_pipeline/watch_it.py 3         # every 3s
  python3 lds_pipeline/watch_it.py --once    # single snapshot (exit 0)

Start the work elsewhere, e.g.:
  python3 lds_pipeline/track_feed.py --follow
  ./lds_pipeline/run_orchestrate_forever.sh
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))
from task_ledger import _load_events, _project  # noqa: E402

FEED = REPO / "diagnostics" / "track.feed.txt"
PATTERNS = (
    "orchestrate.py",
    "run_orchestrate_forever",
    "task_worker.py",
    "track_feed.py",
)


def pgrep_count(pattern: str) -> int:
    try:
        r = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if r.returncode != 0 or not r.stdout.strip():
            return 0
        return len([x for x in r.stdout.strip().splitlines() if x.strip()])
    except (OSError, subprocess.TimeoutExpired):
        return 0


def main() -> None:
    argv = [x for x in sys.argv[1:] if x]
    once = "--once" in argv
    argv = [x for x in argv if x != "--once"]
    interval = float(argv[0]) if argv else 5.0

    def frame() -> None:
        if not once:
            if os.name != "nt":
                os.system("clear")
            else:
                os.system("cls")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        tasks = _project(_load_events())
        c = Counter(t.get("status") for t in tasks.values())
        pend = c.get("pending", 0)
        claim = c.get("claimed", 0)
        done = c.get("completed", 0)

        print(f"  WeScripture · {now}")
        print("=" * 56)
        print(f"  Ledger:  pending {pend}  |  claimed {claim}  |  completed {done}")
        print()
        print("  Processes (0 = nothing matching — start orchestrate or track_feed):")
        any_on = False
        for p in PATTERNS:
            n = pgrep_count(p)
            if n:
                any_on = True
            print(f"    {p:28} {n}")
        print(f"    {'ANY agent activity':28} {'yes' if any_on else 'NO — start a runner'}")
        print()
        print(f"  Last lines ({FEED.name}):")
        if FEED.is_file():
            lines = FEED.read_text(encoding="utf-8", errors="replace").splitlines()
            for line in lines[-18:]:
                print(f"    {line[:118]}")
        else:
            print("    (file missing — run: python3 lds_pipeline/track_feed.py --follow)")
        print()
        print("=" * 56)
        if not once:
            print(f"  Refreshing every {interval:g}s  ·  Ctrl+C to stop")

    if once:
        frame()
        return

    try:
        while True:
            frame()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
