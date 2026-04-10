#!/usr/bin/env python3
"""
Minimal checks for Ollama + smallest model (smoke test before swarm runs).

  python3 lds_pipeline/crew_swarm/eval_model.py

Env: CREW_OLLAMA_BASE_URL (Ollama root or .../v1), CREW_OLLAMA_MODEL (same as swarm).
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def _ollama_root(url: str) -> str:
    u = url.rstrip("/")
    if u.endswith("/v1"):
        return u[:-3]
    return u


def _openai_v1_chat_url(base: str) -> str:
    """Ollama OpenAI-compatible chat endpoint."""
    b = base.rstrip("/")
    if b.endswith("/v1"):
        return b + "/chat/completions"
    return b + "/v1/chat/completions"


def _ollama_tags(base: str) -> dict | None:
    root = _ollama_root(base)
    url = root + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            return json.loads(r.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


def main() -> None:
    base = os.environ.get("CREW_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.environ.get("CREW_OLLAMA_MODEL", "qwen2.5:1.5b")
    print(f"CREW_OLLAMA_BASE_URL={base}")
    print(f"CREW_OLLAMA_MODEL={model}")

    tags = _ollama_tags(base)
    if tags is None:
        print("FAIL: could not reach Ollama /api/tags — is `ollama serve` running?")
        sys.exit(1)

    names = [m.get("name", "") for m in tags.get("models", [])]
    if any(model == n or n.startswith(model + ":") for n in names):
        print(f"OK: model '{model}' appears in ollama list.")
    else:
        print(f"WARN: model '{model}' not found in ollama tags. Pull it, e.g.:")
        print(f"  ollama pull {model}")

    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": 'Reply with exactly: OK'}],
            "temperature": 0,
        }
    ).encode()
    chat_url = _openai_v1_chat_url(base)
    req = urllib.request.Request(
        chat_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read().decode())
        text = (
            body.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        print("chat sample:", (text or "")[:200].replace("\n", " "))
        print("OK: chat/completions succeeded.")
    except urllib.error.HTTPError as e:
        print(f"FAIL: chat/completions HTTP {e.code} — check model name and Ollama.")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"FAIL: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
