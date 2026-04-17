#!/usr/bin/env python3
"""One-shot seed for the rebuilt task ledger. Idempotent: re-running is a no-op."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER_CLI = ROOT / "task_ledger.py"
LEDGER_JSONL = ROOT / "task-ledger.jsonl"
PLAN = "wescripture-rearchitect-reset_f7bbe76b"

TASKS = [
    ("phase0_corpus",       "Pin BoM Central / OpenScriptures sources per volume with licenses in CORPUS_SOURCES.md; validate JST format and write inline-merge test cases for Gen 1, Matt 5, John 1, 1 Ne 3"),
    ("phase1_schema",       "Write Supabase migration for volume/book/chapter/verse/verse_variant/commentary_source/commentary_para/embedding/connection tables; retire server/migrations/001_init.sql"),
    ("phase1_pipeline",     "Scaffold pipeline/ directory with Makefile targets (fetch, normalize, jst_weave, donaldson, upsert, embed, connect, audit) and pinned requirements.txt"),
    ("phase1_pilot",        "Ingest pilot slice (Gen 1-3, Matt 1-3, 1 Ne 1-3 + Donaldson) and verify verse numbering + JST markers end to end"),
    ("phase1_api",          "Rewrite server/app/main.py down to /api/boot, /api/chapter/{id}, /api/verse/{id}/panel with Supabase JWT verification"),
    ("phase1_reader_flag",  "Add USE_API flag in library/index.html and rewire toc, chapter, verse-panel bootstraps to /api/*; keep static fallback for pilot"),
    ("phase2_full_ingest",  "Run make all over full standard works + Donaldson; verify row counts + strict audit green"),
    ("phase2_connect",      "Embed all verses + commentary_para; build connection table (top-K=40, cosine>=0.28); tune threshold from reader feedback"),
    ("phase2_reader_cutover","Remove USE_API flag; reader is API-only; retire per-chapter _words/_graph/_notes loads for v1"),
    ("phase3_archive",      "Move lds_pipeline, legacy library subtrees, co-generated JSON, agent scripts to archive/pre-rewrite/; delete test-mobile-diag*"),
    ("phase3_ci",           "Rewrite .github/workflows/ci.yml: schema migrate, make audit strict, pipeline pytest, reader Puppeteer, FastAPI pytest with DB fixture"),
    ("phase3_obs_security", "Add Sentry to reader + FastAPI + Netlify functions; shared-secret auth on monitor_* or delete in favor of /api/*"),
    ("phase3_docs",         "Write CORPUS.md documenting schema, ID rules, ingestion DAG, license provenance"),
    ("user_data_remap",     "One-time backfill: map legacy verse refs (e.g. 'Genesis 1:3') in Supabase notes/highlights/morsels to canonical ids (gen.1.3)"),
]

HANDOFF = (
    "Ledger rebuilt (v2). Previous 84k-event ledger archived at "
    "archive/task-ledger-v1.2026-04-17.jsonl. Rearchitect plan approved; "
    "14 todos seeded below. Next up: phase0_corpus."
)
DECISIONS = [
    "Corpus source: Book of Mormon Central / OpenScriptures (openly licensed)",
    "Database: Supabase Postgres + pgvector with thin FastAPI",
    "Semantic scope v1: scripture + Donaldson only",
    "UI: keep split-pane reader; rewire to /api/* behind USE_API flag",
    "Ledger: rebuilt; old autonomous pipeline isolated to lds_pipeline/task-ledger-legacy.jsonl",
]


def run(args: list[str]) -> None:
    r = subprocess.run([sys.executable, str(LEDGER_CLI), *args], check=True, capture_output=True, text=True)
    print(r.stdout.strip())


def current_titles() -> set[str]:
    if not LEDGER_JSONL.exists():
        return set()
    titles = set()
    for line in LEDGER_JSONL.read_text().splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "task_add":
            titles.add(ev.get("title", ""))
    return titles


def already_seeded() -> bool:
    if not LEDGER_JSONL.exists():
        return False
    for line in LEDGER_JSONL.read_text().splitlines():
        if not line.strip():
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "session_end" and ev.get("agent") == "prior-session":
            return True
    return False


def main() -> int:
    if already_seeded():
        print("ledger already seeded; skipping")
        return 0
    existing = current_titles()
    for phase, title in TASKS:
        if title in existing:
            continue
        run(["add", title, "--plan", PLAN, "--phase", phase, "--source", "rearchitect-plan"])
    if not already_seeded():
        args = ["session", "end", "--agent", "prior-session", "--handoff", HANDOFF]
        for d in DECISIONS:
            args += ["--decision", d]
        run(args)
    print("\n— seed complete —")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
