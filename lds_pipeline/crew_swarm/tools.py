"""LangChain Core tool wrapping task_dispatch.try_dispatch (CrewAI-compatible)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "lds_pipeline"))

LAST_SUMMARY: str = ""
LAST_HANDLED: bool = False
LAST_EXIT: int = 0


def _dispatch_json(task_json: str) -> str:
    """Run deterministic pipeline for this task title/notes. Input: JSON object string."""
    global LAST_SUMMARY, LAST_HANDLED, LAST_EXIT
    from task_dispatch import try_dispatch

    try:
        task = json.loads(task_json)
    except json.JSONDecodeError as e:
        LAST_SUMMARY = f"invalid JSON: {e}"
        LAST_HANDLED = False
        LAST_EXIT = -1
        return LAST_SUMMARY
    if not isinstance(task, dict):
        LAST_SUMMARY = "task must be a JSON object"
        LAST_HANDLED = False
        LAST_EXIT = -1
        return LAST_SUMMARY

    out = try_dispatch(task)
    LAST_HANDLED = out.handled
    LAST_EXIT = out.exit_code
    LAST_SUMMARY = out.summary or ""
    return json.dumps(
        {
            "handled": out.handled,
            "exit_code": out.exit_code,
            "summary": out.summary,
        },
        ensure_ascii=False,
    )


def build_dispatch_tool():
    """StructuredTool (LangChain Core) — preferred for modern agents."""
    try:
        from langchain_core.tools import StructuredTool
    except ImportError as e:
        raise ImportError("pip install -r requirements-crew.txt (langchain-core)") from e

    return StructuredTool.from_function(
        name="run_wescripture_dispatch",
        description=(
            "Runs the wescripture pipeline for one task. "
            "Input: a JSON object string with keys task_id, title, notes. "
            'Example: {"task_id":"C-0001","title":"Ch genesis_1: add entity span annotations","notes":""}'
        ),
        func=_dispatch_json,
    )
