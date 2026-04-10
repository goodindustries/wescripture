from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone

from fastapi import Cookie, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings

app = FastAPI(title="WeScripture API", version=os.getenv("APP_VERSION", "0.1.0"))

settings = get_settings()

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _sign(value: str) -> str:
    key = (settings.session_secret or "dev-insecure-change-me").encode("utf-8")
    mac = hmac.new(key, msg=value.encode("utf-8"), digestmod=hashlib.sha256).hexdigest()
    return f"{value}.{mac}"


def _verify(signed: str) -> str | None:
    if not signed or "." not in signed:
        return None
    value, mac = signed.rsplit(".", 1)
    expected = _sign(value).rsplit(".", 1)[1]
    if not hmac.compare_digest(mac, expected):
        return None
    return value


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "time_utc": datetime.now(timezone.utc).isoformat(), "env": settings.app_env}


@app.get("/api/version")
def api_version() -> dict:
    return {"name": "wescripture-api", "version": app.version, "env": settings.app_env}


@app.post("/api/session/ensure")
def ensure_session(response: Response, ws_session: str | None = Cookie(default=None)) -> dict:
    """
    Placeholder session wiring.

    For now this only sets a signed opaque cookie; later we will back it with a DB session row.
    """
    raw = _verify(ws_session) if ws_session else None
    if not raw:
        raw = secrets.token_urlsafe(32)
        signed = _sign(raw)
        response.set_cookie(
            "ws_session",
            signed,
            httponly=True,
            secure=False,  # Caddy terminates TLS in prod; set true when domain/TLS is configured
            samesite="lax",
            path="/",
            max_age=60 * 60 * 24 * 30,
        )
        return {"created": True}
    return {"created": False}


@app.get("/api/whoami")
def whoami(ws_session: str | None = Cookie(default=None)) -> dict:
    raw = _verify(ws_session) if ws_session else None
    return {"authenticated": False, "session_present": bool(raw)}

