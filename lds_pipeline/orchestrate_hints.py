"""
Human-oriented UI / test URLs for orchestration logs (orchestrate.log, watch_progress).

Public site base: env WESCRIPTURE_SITE_URL (default https://thegoodproject.net).
Netlify publish dir is `library/`, so deployed paths are /index.html, /chapters/…, not /library/….
"""

from __future__ import annotations

import os
import re
from pathlib import Path

def site_base() -> str:
    return os.environ.get("WESCRIPTURE_SITE_URL", "https://thegoodproject.net").rstrip("/")


def ui_hints_for_task_title(title: str, base: str | None = None) -> list[str]:
    """Return bullet lines (without leading dash; caller may indent)."""
    b = (base or site_base()).rstrip("/")
    t = (title or "").strip()
    out: list[str] = []

    m = re.match(r"^Ch ([a-z0-9_]+):", t, re.I)
    if m:
        cid = m.group(1)
        out.append(f"Reader chapter: {b}/chapters/{cid}.html")
        out.append(f"Right-panel spec (test): {b}/test.html — open same chapter from TOC")

    m = re.match(r"^Donaldson — ([a-z0-9_]+):", t, re.I)
    if m:
        slug = m.group(1)
        if re.search(r"_\d+$", slug):
            out.append(f"Chapter reader: {b}/chapters/{slug}.html")
            out.append(f"Donaldson file (when built): same repo library/donaldson/{slug}.json")
        else:
            out.append(f"Book group `{slug}` — use TOC {b}/index.html to open a chapter")

    if "Registry Wikipedia" in t or t.startswith("Christ —"):
        out.append(f"Main app + entity panels: {b}/index.html")

    if "People registry" in t or "scripture_people" in t.lower():
        out.append(f"Figures surface in reader chips: {b}/index.html (any chapter with entities)")

    if "Things registry" in t or "things.json" in t.lower():
        out.append(f"Things / discovery UI: {b}/index.html")

    if "Normalize Donaldson" in t:
        out.append(f"Donaldson in chapter + notes: open {b}/index.html → pick a standard-work chapter")

    if not out:
        out.append(f"Smoke: {b}/index.html")

    # Dedupe preserving order
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def format_hints_block(title: str, prefix: str = "    ") -> str:
    lines = ui_hints_for_task_title(title)
    return "\n".join(f"{prefix}UI: {line}" for line in lines)


CLAIM_RE = re.compile(
    r"^\[(?P<agent>[^\]]+)\]\s+claimed\s+(?P<tid>T-\d+):\s*(?P<title>.+)$"
)


def parse_claim_line(line: str) -> dict | None:
    line = line.strip()
    m = CLAIM_RE.match(line)
    if not m:
        return None
    return {"agent": m.group("agent"), "task_id": m.group("tid"), "title": m.group("title").strip()}


def scan_worker_out_logs(diag_dir: Path, tail_lines: int = 200) -> list[dict]:
    """Last 'claimed' line per Worker*.out file (best-effort)."""
    found: list[dict] = []
    if not diag_dir.is_dir():
        return found
    for path in sorted(diag_dir.glob("task-worker-Worker*.out")):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in reversed(lines[-tail_lines:]):
            p = parse_claim_line(line)
            if p:
                p["log_file"] = path.name
                found.append(p)
                break
    return found


def format_claim_report(diag_dir: Path, base: str | None = None) -> str:
    """Multi-line string for orchestrate.log."""
    rows = scan_worker_out_logs(diag_dir)
    if not rows:
        return "  (no Worker*.out claim lines found yet)"
    b = (base or site_base()).rstrip("/")
    parts: list[str] = []
    for r in rows:
        parts.append(
            f"  {r['log_file']}: {r['agent']} → {r['task_id']}: {r['title'][:100]}"
        )
        for h in ui_hints_for_task_title(r["title"], base=b):
            parts.append(f"    UI: {h}")
    return "\n".join(parts)
