# API scope (VPS + FastAPI)

The Docker stack ([`docker-compose.yml`](../docker-compose.yml), [`server/app/main.py`](../server/app/main.py)) defines a **future** boundary for state that does not belong in static hosting or `localStorage` alone.

## Recommended phases

1. **Phase A — static + localStorage (Netlify)**  
   Highlights, study saves, and position stay in the browser. No account.

2. **Phase B — anonymous device + optional API (VPS)**  
   `POST /api/...` with a device id (header or cookie) for backup/sync, no login required.

3. **Phase C — accounts**  
   Email/password or OAuth; merge device data into account.

## What stays where

| Data | Netlify static | VPS API |
|------|----------------|---------|
| Scripture text / graphs | yes (CDN) | no |
| User highlights / notes | localStorage only | optional sync |
| Entity JSON | yes | no (unless you add editorial API later) |

## CORS

Set `CORS_ORIGINS` in `.env` to the production reader origin(s) before exposing write endpoints.

## Reader integration

The scripture reader (`library/index.html`) sets `window.WESCRIPTURE_API = null` by default and should **not** call `/api` until Phase B is enabled; future wiring can set it to the API base URL (same origin on VPS) and guard fetches on that value.
