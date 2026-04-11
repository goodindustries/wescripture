"""CrewAI sequential crew: dispatcher → worker (tool) → aggregator."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))

from crew_swarm.events import append_claimed, append_completed, append_failed
from crew_swarm.llm_config import build_crew_llm, kickoff_output_text
from crew_swarm.tools import LAST_EXIT, LAST_HANDLED, LAST_SUMMARY, build_dispatch_tool


def _ledger_task_id_from_notes(notes: str) -> str | None:
    m = re.search(r"ledger_task_id:\s*(T-\d+)", notes or "")
    return m.group(1) if m else None


def _strip_ledger_ref_for_dispatch(notes: str) -> str:
    """Remove ledger bridge line so try_dispatch sees original notes only."""
    return re.sub(r"^ledger_task_id:\s*T-\d+\s*\n?", "", notes or "", count=1).strip()


def _mirror_ledger_complete(ledger_tid: str, summary: str, commit: str) -> None:
    argv = [
        sys.executable,
        str(REPO / "lds_pipeline" / "task_ledger.py"),
        "complete",
        "--task-id",
        ledger_tid,
        "--agent",
        "CrewSwarm",
        "--notes",
        (summary or "")[:480],
    ]
    if commit:
        argv += ["--commit", commit]
    subprocess.run(argv, cwd=str(REPO), check=False)


def _mirror_ledger_reopen(ledger_tid: str, notes: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(REPO / "lds_pipeline" / "task_ledger.py"),
            "reopen",
            "--task-id",
            ledger_tid,
            "--notes",
            (notes or "")[:480],
        ],
        cwd=str(REPO),
        check=False,
    )


def _git_short_head() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return (r.stdout or "").strip()[:12] if r.returncode == 0 else ""
    except OSError:
        return ""


def run_swarm_on_task(task: dict[str, Any], verbose: bool = True) -> dict[str, Any]:
    """
    Run a 3-agent sequential crew on one task dict (task_id, title, notes).
    Appends task_completed or task_failed to crew_events.jsonl based on dispatch outcome.
    """
    from crewai import Agent, Crew, Task
    from crewai.process import Process

    tid = task.get("task_id", "")
    title = task.get("title", "")
    notes = task.get("notes", "")
    ledger_tid = _ledger_task_id_from_notes(notes)
    notes_dispatch = _strip_ledger_ref_for_dispatch(notes)
    payload = json.dumps(
        {"task_id": tid, "title": title, "notes": notes_dispatch},
        ensure_ascii=False,
    )

    append_claimed(tid, agent="CrewSwarm")

    llm = build_crew_llm()
    dispatch_tool = build_dispatch_tool()

    dispatcher = Agent(
        role="Task dispatcher",
        goal="Confirm the next unit of work and pass context to the pipeline worker.",
        backstory="You coordinate wescripture pipeline tasks. Be concise.",
        llm=llm,
        verbose=verbose,
        allow_delegation=False,
    )
    worker = Agent(
        role="Pipeline worker",
        goal="Execute the repository pipeline for the given task using the dispatch tool exactly once.",
        backstory="You run local scripts via tools. You must call run_wescripture_dispatch with the JSON payload.",
        llm=llm,
        tools=[dispatch_tool],
        verbose=verbose,
        allow_delegation=False,
    )
    aggregator = Agent(
        role="Run summarizer",
        goal="Summarize whether the pipeline run succeeded in one or two sentences for the operator.",
        backstory="You read prior agent output and produce a brief human-readable status line.",
        llm=llm,
        verbose=verbose,
        allow_delegation=False,
    )

    t1 = Task(
        description=(
            f"The next task is fixed — do not choose another.\n"
            f"task_id: {tid}\n"
            f"title: {title}\n"
            f"notes: {notes_dispatch}\n"
            f"Reply with one line: confirmed, ready for pipeline worker."
        ),
        expected_output="One line confirming readiness.",
        agent=dispatcher,
    )
    t2 = Task(
        description=(
            "Call the tool run_wescripture_dispatch exactly once. "
            f"Pass this JSON string as the only argument (copy verbatim): {payload}"
        ),
        expected_output="Raw tool output: JSON with handled, exit_code, summary.",
        agent=worker,
    )
    t3 = Task(
        description=(
            "Based on the worker output above, state whether the dispatch ran, "
            "whether it matched a handler, and the exit code if mentioned."
        ),
        expected_output="One or two sentences summarizing success or failure.",
        agent=aggregator,
    )

    crew = Crew(
        agents=[dispatcher, worker, aggregator],
        tasks=[t1, t2, t3],
        process=Process.sequential,
        verbose=verbose,
    )

    narrative = ""
    try:
        raw = crew.kickoff()
        narrative = kickoff_output_text(raw)
    except Exception as e:  # noqa: BLE001
        append_failed(tid, f"crew kickoff: {e!s}")
        if ledger_tid:
            _mirror_ledger_reopen(ledger_tid, f"crew kickoff failed: {e!s}")
        return {"ok": False, "error": str(e), "narrative": narrative}

    handled = LAST_HANDLED
    exit_code = LAST_EXIT
    summary = LAST_SUMMARY or (str(narrative)[:500] if narrative else "no summary")

    if not handled:
        msg = f"dispatch: no handler or not handled — {summary}"
        append_failed(tid, msg)
        if ledger_tid:
            _mirror_ledger_reopen(ledger_tid, msg[:450])
        return {
            "ok": False,
            "task_id": tid,
            "handled": False,
            "exit_code": exit_code,
            "narrative": narrative,
            "summary": summary,
        }

    commit = _git_short_head()
    ok_run = exit_code == 0
    line = f"dispatch: {summary}" + (f" (exit {exit_code})" if exit_code else "")
    if ok_run:
        append_completed(tid, summary=line, commit=commit, agent="CrewSwarm")
        if ledger_tid:
            _mirror_ledger_complete(ledger_tid, line, commit)
    else:
        fail_msg = f"dispatch exit {exit_code}: {summary}"
        append_failed(tid, fail_msg)
        if ledger_tid:
            _mirror_ledger_reopen(ledger_tid, fail_msg[:450])

    return {
        "ok": ok_run,
        "task_id": tid,
        "handled": True,
        "exit_code": exit_code,
        "commit": commit if ok_run else "",
        "narrative": narrative,
        "summary": summary,
    }
