from __future__ import annotations

from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    session_secret: str
    cors_origins: list[str]


def _split_csv(value: str) -> list[str]:
    parts = [p.strip() for p in (value or "").split(",")]
    return [p for p in parts if p]


def get_settings() -> Settings:
    return Settings(
        app_env=getenv("APP_ENV", "local"),
        database_url=getenv("DATABASE_URL", ""),
        session_secret=getenv("SESSION_SECRET", ""),
        cors_origins=_split_csv(getenv("CORS_ORIGINS", "")),
    )

