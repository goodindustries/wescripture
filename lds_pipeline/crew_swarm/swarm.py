"""CrewAI sequential crew: dispatcher → worker (tool) → aggregator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))

from crew_swarm.events import append_claimed, append_completed, append_failed
from crew_swarm.llm_config import build_chat_llm
from crew_swarm.tools import LAST_EXIT, LAST_HANDLED, LAST_SUMMARY, build_dispatch_tool


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
    payload = json.dumps(
        {"task_id": tid, "title": title, "notes": notes},
        ensure_ascii=False,
    )

    append_claimed(tid, agent="CrewSwarm")

    llm = build_chat_llm()
    dispatch_tool = build_dispatch_tool()

    dispatcher = Agent(
        role="Task dispatcher",
        goal="Confirm the next unit of work and pass context to the pipeline worker.",
        backstory="You coordinate wescripture pipeline tasks. Be concise.",
        llm=llm,
        verbose=verbose,
        allow_delegation=False,
        memory=False,
    )
    worker = Agent(
        role="Pipeline worker",
        goal="Execute the repository pipeline for the given task using the dispatch tool exactly once.",
        backstory="You run local scripts via tools. You must call run_wescripture_dispatch with the JSON payload.",
        llm=llm,
        tools=[dispatch_tool],
        verbose=verbose,
        allow_delegation=False,
        memory=False,
    )
    aggregator = Agent(
        role="Run summarizer",
        goal="Summarize whether the pipeline run succeeded in one or two sentences for the operator.",
        backstory="You read prior agent output and produce a brief human-readable status line.",
        llm=llm,
        verbose=verbose,
        allow_delegation=False,
        memory=False,
    )

    t1 = Task(
        description=(
            f"The next task is fixed — do not choose another.\n"
            f"task_id: {tid}\n"
            f"title: {title}\n"
            f"notes: {notes}\n"
            f"Reply with one line: confirmed, ready for pipeline worker."
        ),
        agent=dispatcher,
    )
    t2 = Task(
        description=(
            "Call the tool run_wescripture_dispatch exactly once. "
            f"Pass this JSON string as the only argument (copy verbatim): {payload}"
        ),
        agent=worker,
    )
    t3 = Task(
        description=(
            "Based on the worker output above, state whether the dispatch ran, "
            "whether it matched a handler, and the exit code if mentioned."
        ),
        agent=aggregator,
    )

    crew = Crew(
        agents=[dispatcher, worker, aggregator],
        tasks=[t1, t2, t3],
        process=Process.sequential,
        verbose=2 if verbose else 0,
    )

    narrative = ""
    try:
        narrative = crew.kickoff() or ""
    except Exception as e:  # noqa: BLE001
        append_failed(tid, f"crew kickoff: {e!s}")
        return {"ok": False, "error": str(e), "narrative": narrative}

    handled = LAST_HANDLED
    exit_code = LAST_EXIT
    summary = LAST_SUMMARY or (str(narrative)[:500] if narrative else "no summary")

    if not handled:
        msg = f"dispatch: no handler or not handled — {summary}"
        append_failed(tid, msg)
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
    append_completed(tid, summary=line, commit=commit if ok_run else "", agent="CrewSwarm")
    return {
        "ok": ok_run,
        "task_id": tid,
        "handled": True,
        "exit_code": exit_code,
        "commit": commit,
        "narrative": narrative,
        "summary": summary,
    }
