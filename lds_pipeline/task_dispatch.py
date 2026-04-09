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

    # ── Registry Wikipedia — … ───────────────────────────────────────────────
    if title.startswith("Registry Wikipedia — scripture_people"):
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "build_entity_wikipedia.py"),
                "--scripture-people",
            ]
        )
        return DispatchOutcome(True, rc, f"build_entity_wikipedia --scripture-people (exit {rc})")

    if title.startswith("Registry Wikipedia — places"):
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "build_entity_wikipedia.py"),
                "--places",
            ]
        )
        return DispatchOutcome(True, rc, f"build_entity_wikipedia --places (exit {rc})")

    if title.startswith("Registry Wikipedia — things"):
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "build_entity_wikipedia.py"),
                "--things",
            ]
        )
        return DispatchOutcome(True, rc, f"build_entity_wikipedia --things (exit {rc})")

    if title.startswith("Registry Wikipedia — topics"):
        rc = _run(
            [
                sys.executable,
                str(REPO / "lds_pipeline" / "build_entity_wikipedia.py"),
                "--topics",
            ]
        )
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
                "2",
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
                "2",
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
                "2",
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
                "2",
                "--limit",
                limit,
            ]
        )
        return DispatchOutcome(True, rc, f"generate_christ_connections {key} limit={limit} (exit {rc})")

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
