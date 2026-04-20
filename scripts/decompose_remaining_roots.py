#!/usr/bin/env python3
"""
Idempotent: estimate + split each rearchitect root that still lacks points/children.

Run from repo root:
    python3 scripts/decompose_remaining_roots.py

Uses manual Fibonacci estimates and 1-point child titles (no LLM).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "task_ledger.py"
STATE = ROOT / "ledger-state.json"

# (task_id, points, estimate_rationale, [child titles...])
ROOTS: list[tuple[str, int, str, list[str]]] = [
    (
        "T-0001",
        8,
        "licenses doc plus four JST merge test cases and cross-checks",
        [
            "Draft CORPUS_SOURCES.md with BoMCentral and OpenScriptures URLs",
            "Document JST inline-merge format rules for corpus validation",
            "Add pytest for Genesis chapter 1 JST merge golden behavior",
            "Add pytest for Matthew chapter 5 JST merge golden behavior",
            "Add pytest for John chapter 1 JST merge golden behavior",
            "Add pytest for 1 Nephi chapter 3 JST merge golden behavior",
            "Cross-check per-volume license notes inside CORPUS_SOURCES.md",
            "Link pipeline README to CORPUS_SOURCES.md for corpus provenance",
        ],
    ),
    (
        "T-0002",
        8,
        "multi-table Supabase migration replacing legacy 001_init.sql",
        [
            "Add migration for volume and book dimension tables",
            "Add migration for chapter verse and verse_variant tables",
            "Add migration for commentary_source and commentary_para tables",
            "Add migration for embedding storage with pgvector column type",
            "Add migration for semantic connection graph table",
            "Add indexes foreign keys and RLS stubs for corpus schema",
            "Retire or wrap server/migrations/001_init.sql without breaking deploy",
            "Smoke test migrate up down against local Postgres docker fixture",
        ],
    ),
    (
        "T-0004",
        8,
        "pilot slice ingest plus Donaldson wiring and verification gates",
        [
            "Ingest Genesis chapters one through three into pilot tables",
            "Ingest Matthew chapters one through three into pilot tables",
            "Ingest 1 Nephi chapters one through three into pilot tables",
            "Wire Donaldson fetch scope for pilot books and chapters",
            "Verify pilot verse numbering matches canonical id scheme",
            "Verify JST markers in pilot output match expected fixtures",
            "Add Makefile pilot-ingest target with dry-run and verbose logs",
            "Emit pilot audit log with row counts and checksum summary",
        ],
    ),
    (
        "T-0005",
        8,
        "thin FastAPI surface with JWT and three JSON panel endpoints",
        [
            "Implement GET /api/boot returning reader bootstrap JSON payload",
            "Implement GET /api/chapter/{id} with normalized chapter verses",
            "Implement GET /api/verse/{id}/panel for discovery right pane JSON",
            "Add Supabase JWT verification dependency for protected routes",
            "Trim or feature-flag legacy server routes no longer used by reader",
            "Add pytest covering boot chapter and verse panel happy paths",
            "Standardize JSON errors and CORS headers for browser reader origin",
            "Document API env vars secrets and deploy notes in server README",
        ],
    ),
    (
        "T-0006",
        5,
        "feature flag plus three rewires and static fallback preservation",
        [
            "Add USE_API boolean and env wiring near top of library index.html",
            "Rewire TOC bootstrap to /api/boot when USE_API flag is true",
            "Rewire loadChapter to /api/chapter/{id} when USE_API flag is true",
            "Rewire verse panel open to /api/verse/{id}/panel when flag true",
            "Preserve static JSON chapter loads when USE_API flag is false",
        ],
    ),
    (
        "T-0007",
        13,
        "full standard works ingest embed connect audit is a multi-day epic",
        [
            "Run pipeline fetch stage for full standard works book list",
            "Run normalize stage across every chapter in standard works corpus",
            "Run jst_weave stage producing JST-injected verse text everywhere",
            "Run donaldson ingest for all commentary spans linked to verses",
            "Run database upsert batches for verses variants and commentary rows",
            "Run embedding generation for all verse and commentary paragraph rows",
            "Run semantic connect build with cosine threshold and top K neighbors",
            "Run strict audit Makefile target and capture diagnostics artifact",
            "Verify aggregate row counts against expected scripture totals",
            "Spot-check random verse sample for Donaldson anchor correctness",
            "Tune batch sizes and memory for embed and upsert throughput",
            "Write full ingest runbook in pipeline README with recovery steps",
            "Tag or archive ingest output bundle for reproducible deployments",
        ],
    ),
    (
        "T-0008",
        8,
        "vectors plus connection table and operational tuning hooks",
        [
            "Add batch embedding job for all verse rows in corpus tables",
            "Add batch embedding job for all commentary_para rows in corpus",
            "Build connection table storing top K cosine neighbors per verse",
            "Set default cosine similarity threshold to point two eight value",
            "Create ivfflat or compatible index for pgvector similarity search",
            "Add reader feedback path to log bad or noisy connection samples",
            "Stub algorithm documentation section inside future CORPUS.md file",
            "Add SQL audit query listing verses with zero outgoing connections",
        ],
    ),
    (
        "T-0009",
        5,
        "API-only reader by removing lazy per-chapter asset loads",
        [
            "Remove USE_API flag after production validation period completes",
            "Delete _words lazy load code paths from scripture reader module",
            "Delete _graph lazy load code paths from scripture reader module",
            "Delete _notes lazy load code paths from scripture reader module",
            "Update Puppeteer tests to assume API-only data loading behavior",
        ],
    ),
    (
        "T-0010",
        8,
        "large filesystem move with manifest and CI reference cleanup",
        [
            "Move lds_pipeline tree under archive/pre-rewrite with README note",
            "Move legacy library subtrees per inventory into archive pre rewrite",
            "Move co-generated JSON blobs into archive with checksum manifest",
            "Move one-off agent helper scripts into archive pre rewrite folder",
            "Delete root test-mobile-diag star test files per archive plan",
            "Fix broken imports or docs that referenced old moved file paths",
            "Add archive README describing how to restore paths if needed",
            "Run ripgrep CI step ensuring no stale references to old locations",
        ],
    ),
    (
        "T-0011",
        5,
        "CI workflow blocks: migrate audit pytest puppeteer api tests",
        [
            "Add Supabase schema migrate step to GitHub Actions workflow file",
            "Add make audit strict gate with failure on first warning to CI",
            "Add pipeline pytest job with pinned Python and requirements cache",
            "Add reader Puppeteer npm test job with headless chrome in CI",
            "Add FastAPI pytest job using docker Postgres service fixture",
        ],
    ),
    (
        "T-0012",
        5,
        "Sentry across three surfaces plus monitor RPC hardening",
        [
            "Initialize Sentry browser SDK in library index behind env toggle",
            "Initialize Sentry in FastAPI app with release and environment tags",
            "Add Sentry wrapper to Netlify functions if functions remain in use",
            "Apply shared secret or remove monitor underscore RPC endpoints",
            "Document Sentry DSN sampling and PII policy in deployment README",
        ],
    ),
    (
        "T-0013",
        3,
        "documentation deliverable split by topic for reviewability",
        [
            "Write CORPUS.md section for schema IDs and book abbreviation rules",
            "Write CORPUS.md section for ingestion DAG and Makefile target list",
            "Write CORPUS.md section for licenses and third party provenance",
        ],
    ),
    (
        "T-0014",
        5,
        "Supabase backfill for three user tables using canonical verse ids",
        [
            "Export Supabase notes rows containing legacy verse string formats",
            "Build mapping table from display reference strings to canonical ids",
            "Write idempotent SQL or script migrating notes verse key column",
            "Write idempotent migration for highlights legacy verse references",
            "Write idempotent migration for morsels with dry-run and rollback",
        ],
    ),
]


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def run_estimate(tid: str, pts: int, rationale: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(CLI),
            "estimate",
            tid,
            "--apply",
            "--agent",
            "Cursor",
            "--points",
            str(pts),
            "--rationale",
            rationale,
        ],
        cwd=str(ROOT),
        check=True,
    )


def run_split(tid: str, children: list[str], rationale: str) -> None:
    cmd = [
        sys.executable,
        str(CLI),
        "split",
        tid,
        "--agent",
        "Cursor",
        "--apply",
        "--rationale",
        rationale,
    ]
    for c in children:
        cmd.extend(["--child", c])
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def main() -> int:
    if not STATE.exists():
        print("ledger-state.json missing; run task_ledger.py once first", file=sys.stderr)
        return 1
    state = load_state()
    by_id = {t["id"]: t for t in state["tasks"]}
    for tid, pts, rat, children in ROOTS:
        t = by_id.get(tid)
        if not t:
            print(f"[skip] {tid} not in ledger")
            continue
        if t.get("children"):
            print(f"[skip] {tid} already split ({len(t['children'])} children)")
            continue
        if t.get("points") is not None:
            print(f"[skip] {tid} already estimated ({t['points']}p); delete estimate row to re-run or split manually")
            continue
        n = len(children)
        if n < 2:
            print(f"[error] {tid} needs >=2 children", file=sys.stderr)
            return 1
        if n != pts:
            print(
                f"[warn] {tid} points={pts} but {n} children (expected n==pts for 1p leaves); continuing",
                file=sys.stderr,
            )
        for i, title in enumerate(children):
            if len(title) < 12:
                print(f"[error] child {i} title too short: {title!r}", file=sys.stderr)
                return 1
        print(f"[run] {tid} estimate {pts}p + split -> {n} children")
        run_estimate(tid, pts, rat)
        run_split(tid, children, f"manual split for {tid}: {rat}")
        state = load_state()
        by_id = {x["id"]: x for x in state["tasks"]}
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
