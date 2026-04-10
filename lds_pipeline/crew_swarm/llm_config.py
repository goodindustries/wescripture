"""Ollama via OpenAI-compatible API (LangChain ChatOpenAI). Env: CREW_OLLAMA_BASE_URL, CREW_OLLAMA_MODEL."""

from __future__ import annotations

import os


def build_chat_llm():
    """Return a LangChain-compatible chat model pointing at local Ollama."""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as e:
        raise ImportError(
            "Install crew dependencies: pip install -r requirements-crew.txt"
        ) from e

    base = os.environ.get("CREW_OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")
    model = os.environ.get("CREW_OLLAMA_MODEL", "qwen2.5:1.5b")
    key = os.environ.get("CREW_OLLAMA_API_KEY", "ollama")
    temperature = float(os.environ.get("CREW_OLLAMA_TEMPERATURE", "0.15"))
    return ChatOpenAI(
        model=model,
        openai_api_base=base,
        openai_api_key=key,
        temperature=temperature,
    )
