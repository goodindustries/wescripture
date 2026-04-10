"""CrewAI LLM + Ollama (via LiteLLM). Env: CREW_OLLAMA_BASE_URL, CREW_OLLAMA_MODEL."""

from __future__ import annotations

import os


def _normalize_ollama_base(url: str) -> str:
    u = url.rstrip("/")
    if u.endswith("/v1"):
        return u[:-3]
    return u


def build_crew_llm():
    """
    Return crewai.LLM configured for a local Ollama model.

    Uses the `ollama/<model>` route through LiteLLM (bundled with CrewAI).
    """
    try:
        from crewai import LLM
    except ImportError as e:
        raise ImportError(
            "Install crew stack (Python 3.10+): pip install -r requirements-crew.txt"
        ) from e

    raw_base = os.environ.get("CREW_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    base = _normalize_ollama_base(raw_base)
    model = os.environ.get("CREW_OLLAMA_MODEL", "qwen2.5:1.5b")
    temperature = float(os.environ.get("CREW_OLLAMA_TEMPERATURE", "0.15"))
    # LiteLLM / CrewAI expect ollama/<name>
    lm = f"ollama/{model}" if not model.startswith("ollama/") else model

    return LLM(model=lm, base_url=base, temperature=temperature)


def kickoff_output_text(result) -> str:
    """Normalize crew.kickoff() return value across CrewAI versions."""
    if result is None:
        return ""
    if hasattr(result, "raw"):
        return str(result.raw or "")
    tasks_out = getattr(result, "tasks_output", None)
    if tasks_out:
        parts: list[str] = []
        for t in tasks_out:
            if hasattr(t, "raw"):
                parts.append(str(t.raw or ""))
            else:
                parts.append(str(t))
        return "\n".join(parts) if parts else str(result)
    return str(result)
