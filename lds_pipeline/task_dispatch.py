#!/usr/bin/env python3
"""
task_dispatch.py
================
Deterministic execution for tasks whose titles/notes match known pipelines
(no cloud LLM). Lets workers run locally: Ollama-backed generators, Wikipedia
enrichment, entity annotation, etc.

Returns whether the task was handled and whether git dirtied the tree.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


@dataclass
class DispatchOutcome:
    handled: bool
    exit_code: int = 0
    summary: str = ""


def _run(argv: list[str], cwd: Path = REPO) -> int:
    print(f"  [dispatch] {' '.join(argv)}", flush=True)
    return subprocess.run(argv, cwd=str(cwd), check=False).returncode


def _chapter_id_to_book(cid: str) -> str:
    m = re.match(r"^(.+)_(\d+)$", cid)
    return m.group(1) if m else cid


def try_dispatch(task: dict) -> DispatchOutcome:
    title = (task.get("title") or "").strip()
    notes = (task.get("notes") or "").strip()

    # ── Corpus / vectorization (local; may be long-running) ───────────────
    if title == "Corpus pipeline: sync_standard_works verse catalog":
        rc = _run([sys.executable, str(REPO / "lds_pipeline" / "sync_standard_works.py")])
        return DispatchOutcome(True, rc, f"sync_standard_works.py exit {rc}")

    if title == "Corpus pipeline: run correlate_embeddings after sync":
        rc1 = _run([sys.executable, str(REPO / "lds_pipeline" / "sync_standard_works.py")])
        if rc1 != 0:
            return DispatchOutcome(True, rc1, f"sync_standard_works.py exit {rc1}")
        argv = [sys.executable, str(REPO / "lds_pipeline" / "correlate_embeddings.py")]
        if "--rebuild" in notes:
            argv.append("--rebuild")
        rc2 = _run(argv)
        return DispatchOutcome(True, rc2, f"sync ok; correlate_embeddings.py exit {rc2}")

    if title == "Corpus pipeline: run correlate_embeddings":
        argv = [sys.executable, str(REPO / "lds_pipeline" / "correlate_embeddings.py")]
        if "--rebuild" in notes:
            argv.append("--rebuild")
        rc = _run(argv)
        return DispatchOutcome(True, rc, f"correlate_embeddings.py exit {rc}")

    if title == "Corpus pipeline: correlate_embeddings books" and notes.strip():
        tokens = notes.split()
        want_rebuild = "--rebuild" in tokens
        books = [t for t in tokens if t != "--rebuild"]
        if not books:
            return DispatchOutcome(True, 1, "no book names in notes")
        argv = [
            sys.executable,
            str(REPO / "lds_pipeline" / "correlate_embeddings.py"),
            "--books",
        ] + books
        if want_rebuild:
            argv.append("--rebuild")
        rc = _run(argv)
        return DispatchOutcome(True, rc, f"correlate_embeddings --books ({len(books)} names) exit {rc}")

    if title == "Corpus maintenance: lint_source_paras":
        rc = _run([sys.executable, str(REPO / "lds_pipeline" / "lint_source_paras.py")])
        return DispatchOutcome(True, rc, f"lint_source_paras.py exit {rc}")

    if title == "Corpus maintenance: add_para_ids_to_sources":
        argv = [sys.executable, str(REPO / "lds_pipeline" / "add_para_ids_to_sources.py")]
        if "--normalize" in notes:
            argv.append("--normalize")
        rc = _run(argv)
        return DispatchOutcome(True, rc, f"add_para_ids_to_sources.py exit {rc}")

    if title == "Corpus audit: regenerate resource map":
        rc = _run([sys.executable, str(REPO / "lds_pipeline" / "audit_corpus_resources.py")])
        return DispatchOutcome(True, rc, f"audit_corpus_resources.py exit {rc}")

    # ── Ch genesis_1: add entity span annotations ─────────────────────────
    m = re.match(
        r"^Ch ([a-z0-9_]+): add entity span annotations",
        title,
        re.I,
    )
    if m:
        book = _chapter_id_to_book(m.group(1))
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "annotate_entity_spans.py"),
                "--books",
                book,
            ]
        )
        return DispatchOutcome(True, rc, f"annotate_entity_spans --books {book} (exit {rc})")

    # ── Ch mark_8: add or repair _notes.html ───────────────────────────────
    m_notes = re.match(
        r"^Ch ([a-z0-9_]+): add or repair _notes\.html",
        title,
        re.I,
    )
    if m_notes:
        cid = m_notes.group(1)
        out = REPO / "library" / "chapters" / f"{cid}_notes.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        shell = "<!DOCTYPE html>\n<html lang=\"en\">\n<body>\n</body>\n</html>\n"
        if not out.is_file():
            out.write_text(shell, encoding="utf-8")
            return DispatchOutcome(True, 0, f"wrote scaffold {out.name}")
        return DispatchOutcome(True, 0, f"{out.name} already present")

    # ── Registry Wikipedia — … ───────────────────────────────────────────────
    def _wiki_limit_argv(flag: str) -> list[str]:
        lim_m = re.search(r"--limit\s+(\d+)", notes)
        argv = [
            sys.executable,
            str(REPO / "lds_pipeline" / "build_entity_wikipedia.py"),
            flag,
        ]
        if lim_m:
            argv += ["--limit", lim_m.group(1)]
        return argv

    if title.startswith("Registry Wikipedia — scripture_people"):
        argv = _wiki_limit_argv("--scripture-people")
        rc = _run(argv)
        return DispatchOutcome(True, rc, f"build_entity_wikipedia --scripture-people (exit {rc})")

    if title.startswith("People registry: Wikipedia enrichment for scripture figures"):
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "build_entity_wikipedia.py"),
                "--scripture-people",
            ]
        )
        return DispatchOutcome(True, rc, f"build_entity_wikipedia --scripture-people (People registry task) exit {rc}")

    if title.startswith("Registry Wikipedia — places"):
        rc = _run(_wiki_limit_argv("--places"))
        return DispatchOutcome(True, rc, f"build_entity_wikipedia --places (exit {rc})")

    if title.startswith("Registry Wikipedia — things"):
        rc = _run(_wiki_limit_argv("--things"))
        return DispatchOutcome(True, rc, f"build_entity_wikipedia --things (exit {rc})")

    if title.startswith("Registry Wikipedia — topics"):
        rc = _run(_wiki_limit_argv("--topics"))
        return DispatchOutcome(True, rc, f"build_entity_wikipedia --topics (exit {rc})")

    if title.startswith("Registry Wikipedia — people.json"):
        lim_m = re.search(r"--limit\s+(\d+)", notes)
        limit = lim_m.group(1) if lim_m else "40"
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "build_entity_wikipedia.py"),
                "--people",
                "--limit",
                limit,
            ]
        )
        return DispatchOutcome(True, rc, f"build_entity_wikipedia --people --limit {limit} (exit {rc})")

    # ── Christ — … (Ollama local) ────────────────────────────────────────────
    if title.startswith("Christ — scripture_people"):
        lim_m = re.search(r"--limit\s+(\d+)", notes)
        limit = lim_m.group(1) if lim_m else "35"
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "generate_christ_connections.py"),
                "--only",
                "scripture_people",
                "--workers",
                "1",
                "--limit",
                limit,
            ]
        )
        return DispatchOutcome(True, rc, f"generate_christ_connections scripture_people limit={limit} (exit {rc})")

    if title.startswith("Christ — topics"):
        lim_m = re.search(r"--limit\s+(\d+)", notes)
        limit = lim_m.group(1) if lim_m else "20"
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "generate_christ_connections.py"),
                "--only",
                "topics",
                "--workers",
                "1",
                "--limit",
                limit,
            ]
        )
        return DispatchOutcome(True, rc, f"generate_christ_connections topics limit={limit} (exit {rc})")

    if title.startswith("Christ — people.json"):
        lim_m = re.search(r"--limit\s+(\d+)", notes)
        limit = lim_m.group(1) if lim_m else "40"
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "generate_christ_connections.py"),
                "--only",
                "people",
                "--workers",
                "1",
                "--limit",
                limit,
            ]
        )
        return DispatchOutcome(True, rc, f"generate_christ_connections people limit={limit} (exit {rc})")

    if title.startswith("Christ — places") or title.startswith("Christ — things"):
        key = "places" if "places" in title else "things"
        lim_m = re.search(r"--limit\s+(\d+)", notes)
        limit = lim_m.group(1) if lim_m else "50"
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "generate_christ_connections.py"),
                "--only",
                key,
                "--workers",
                "1",
                "--limit",
                limit,
            ]
        )
        return DispatchOutcome(True, rc, f"generate_christ_connections {key} limit={limit} (exit {rc})")

    # ── Full-queue registry tasks (titles from task_scout / manual queue) ───
    if title.startswith("People registry: rebuild to 200 figures"):
        rc1 = _run(
            [sys.executable, str(REPO / "lds_pipeline" / "build_scripture_figure_registry.py")]
        )
        if rc1 != 0:
            return DispatchOutcome(True, rc1, f"build_scripture_figure_registry exit {rc1}")
        rc2 = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "generate_christ_connections.py"),
                "--only",
                "scripture_people",
                "--workers",
                "1",
                "--limit",
                "250",
            ]
        )
        return DispatchOutcome(True, rc2, f"scripture_people build + christ (exit {rc2})")

    if title.startswith("Things registry: expand to 60+"):
        rc1 = _run([sys.executable, str(REPO / "lds_pipeline" / "expand_things_registry.py")])
        if rc1 != 0:
            return DispatchOutcome(True, rc1, f"expand_things_registry exit {rc1}")
        rc2 = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "generate_christ_connections.py"),
                "--only",
                "things",
                "--workers",
                "1",
                "--limit",
                "120",
            ]
        )
        return DispatchOutcome(True, rc2, f"things expand + christ (exit {rc2})")

    return DispatchOutcome(False, 0, "no matching dispatch rule")


def git_has_changes() -> bool:
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=True,
    )
    return bool(r.stdout.strip())
