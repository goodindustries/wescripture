#!/usr/bin/env python3
"""
Local-only merged feed (ledger + orchestrate.log + worker *.log JSON).
Stays under diagnostics/ — not part of the Netlify site; use the terminal or pipe.

  python3 lds_pipeline/track_feed.py                    # dump once to stdout
  python3 lds_pipeline/track_feed.py --follow           # stdout + append diagnostics/track.feed.txt
  tail -f diagnostics/track.feed.txt                    # in another pane, same machine

Optional JSON snapshot for local tools (default path is diagnostics, not library/):
  python3 lds_pipeline/track_feed.py --json-out diagnostics/track_feed.json

Pipe elsewhere:
  python3 lds_pipeline/track_feed.py --follow 2>&1 | tee ~/wescripture-feed.log
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))
from task_ledger import _load_events, _project  # noqa: E402

ORCH_LOG = REPO / "diagnostics" / "orchestrate.log"
TEXT_FEED = REPO / "diagnostics" / "track.feed.txt"
LEDGER_PATH = REPO / "task-ledger.jsonl"
DIAG = REPO / "diagnostics"

TS_ORCH = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s+(.*)$")


def _parse_iso(s: str) -> float:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _ledger_event_tuple(ev: dict, tasks: dict[str, dict], source: str) -> tuple[float, str, str]:
    """One feed line from a ledger JSONL event."""
    ts = ev.get("ts") or ""
    kind = ev.get("event", ev.get("type", "?"))
    tid = ev.get("task_id", "")
    ag = ev.get("agent", "")
    title = (ev.get("title") or ev.get("note") or "").strip()
    if not title and tid:
        title = (tasks.get(tid) or {}).get("title") or ""
    title = title[:140]
    body = f"{kind} {tid}".strip()
    if ag:
        body += f" agent={ag}"
    if title:
        body += f" — {title}"
    notes = (ev.get("notes") or "").strip()
    if kind == "task_completed" and ev.get("commit"):
        body += f" commit={str(ev['commit'])[:12]}"
    if notes and kind in ("task_reopened", "task_completed", "task_noted", "task_queued"):
        snip = notes[:160] + ("…" if len(notes) > 160 else "")
        body += f" | {snip}"
    t = _parse_iso(ts) if ts else 0.0
    return (t, source, body.strip())


def collect_ledger_items(limit: int = 60) -> list[tuple[float, str, str]]:
    """Ledger lines: task titles come from projected state (claim/reopen rows often omit title)."""
    events = _load_events()
    tasks = _project(events)
    return [_ledger_event_tuple(ev, tasks, "ledger") for ev in events[-limit:]]


def collect_recent_completions(limit: int = 45) -> list[tuple[float, str, str]]:
    """Newest-last task_completed rows from full ledger (not only tail window)."""
    events = _load_events()
    tasks = _project(events)
    picked: list[tuple[float, str, str]] = []
    for ev in reversed(events):
        kind = ev.get("event", ev.get("type", ""))
        if kind not in ("task_completed", "completed"):
            continue
        picked.append(_ledger_event_tuple(ev, tasks, "complete"))
        if len(picked) >= limit:
            break
    picked.reverse()
    return picked


def collect_orchestrate_items(limit: int = 40) -> list[tuple[float, str, str]]:
    out: list[tuple[float, str, str]] = []
    if not ORCH_LOG.is_file():
        return out
    lines = ORCH_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-limit:]:
        m = TS_ORCH.match(line.strip())
        if m:
            t = _parse_iso(m.group(1))
            msg = m.group(2).strip()
        else:
            t = time.time()
            msg = line.strip()
        out.append((t, "orchestrate", msg))
    return out


def collect_worker_json_items(limit_per_file: int = 8) -> list[tuple[float, str, str]]:
    out: list[tuple[float, str, str]] = []
    if not DIAG.is_dir():
        return out
    for path in sorted(DIAG.glob("task-worker-*.log")):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines[-limit_per_file:]:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = row.get("ts", "")
            t = _parse_iso(ts) if ts else 0.0
            tid_w = row.get("task_id", "")
            ag_w = row.get("agent", "")
            oc = row.get("outcome", "?")
            title_w = (row.get("title") or "").strip()[:120]
            head = f"{oc} {tid_w} {ag_w}".strip()
            if title_w:
                head += f" — {title_w}"
            extra = []
            if row.get("backend"):
                extra.append(f"backend={row['backend']}")
            cm = row.get("claude_model")
            if cm and str(cm).strip() not in ("", "—"):
                extra.append(f"claude={cm}")
            if row.get("ollama"):
                extra.append(f"ollama={row['ollama']}")
            notes_w = (row.get("notes") or "").strip()
            if notes_w and len(notes_w) < 200:
                extra.append(notes_w)
            elif notes_w:
                extra.append(notes_w[:180] + "…")
            msg = head + ("  " + " ".join(extra) if extra else "")
            out.append((t, "worker", msg.strip()))
    return out


def merge_feed(
    ledger_limit: int = 80,
    orch_limit: int = 50,
    completion_limit: int = 45,
) -> list[dict]:
    items: list[tuple[float, str, str]] = []
    items.extend(collect_ledger_items(ledger_limit))
    items.extend(collect_recent_completions(completion_limit))
    items.extend(collect_orchestrate_items(orch_limit))
    items.extend(collect_worker_json_items())
    items.sort(key=lambda x: x[0])
    seen = set()
    rows: list[dict] = []
    for t, src, msg in items:
        key = (int(t), msg[:200])
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "ts": datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                if t > 0
                else "",
                "source": src,
                "text": msg,
            }
        )
    return rows


def format_lines(rows: list[dict], base_url: str) -> str:
    lines = [
        f"# WeScripture activity feed  ·  site: {base_url}",
        "# sources: ledger | complete (recent task_done) | orchestrate | worker (.log JSON)",
        "",
    ]
    for r in rows:
        ts = r.get("ts", "")[:19]
        src = r.get("source", "?")[:12].ljust(12)
        txt = r.get("text", "")
        lines.append(f"{ts}  [{src}] {txt}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Merged ledger/orchestrator/worker feed.")
    ap.add_argument("--follow", action="store_true", help="Only new events (poll); append lines to --feed-file")
    ap.add_argument("--interval", type=float, default=3.0, help="Seconds between polls in --follow")
    ap.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write merged feed JSON (local only; e.g. diagnostics/track_feed.json)",
    )
    ap.add_argument(
        "--feed-file",
        type=Path,
        default=TEXT_FEED,
        help="Append path when using --follow (default: diagnostics/track.feed.txt)",
    )
    ap.add_argument(
        "--write-text",
        type=Path,
        default=None,
        help="One-shot: also write full snapshot to this file",
    )
    ap.add_argument("--site-url", default=os.environ.get("WESCRIPTURE_SITE_URL", "https://thegoodproject.net"))
    args = ap.parse_args()

    base = args.site_url.rstrip("/")

    def row_sig(r: dict) -> str:
        ts = r.get("ts", "")[:19]
        src = r.get("source", "?")
        txt = r.get("text", "")
        return f"{ts}|{src}|{txt}"

    def emit(rows: list[dict], printed: set[str], append_file: Path | None) -> set[str]:
        for r in rows:
            line = f"{r.get('ts', '')[:19]}  [{r.get('source', '?'):12}] {r.get('text', '')}"
            sig = row_sig(r)
            if sig in printed:
                continue
            printed.add(sig)
            print(line, flush=True)
            if append_file is not None:
                append_file.parent.mkdir(parents=True, exist_ok=True)
                with append_file.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
        return printed

    if args.json_out:
        rows = merge_feed()
        payload = {
            "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "site_base": base,
            "items": rows[-500:],
        }
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Wrote {args.json_out} ({len(payload['items'])} items)", flush=True)

    if args.follow:
        seed = merge_feed()
        printed = {row_sig(r) for r in seed}
        print(
            f"Feed: only NEW lines (seeded {len(printed)} existing). Appending → {args.feed_file}  (Ctrl+C)\n",
            flush=True,
        )
        try:
            while True:
                rows = merge_feed()
                printed = emit(rows, printed, append_file=args.feed_file)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.", flush=True)
        return

    rows = merge_feed()
    text = format_lines(rows, base)
    print(text, end="")
    if args.write_text:
        args.write_text.parent.mkdir(parents=True, exist_ok=True)
        args.write_text.write_text(text, encoding="utf-8")
        print(f"Wrote {args.write_text}", flush=True)


if __name__ == "__main__":
    main()
