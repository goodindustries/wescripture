# WeScripture deployment (stateful-ready)

This repo currently serves a static UI (HTML/CSS/JS) plus a Python pipeline, and now includes a minimal **API boundary** and **Postgres** foundation for durable user data (notes, highlights, history, saved passages).

## Local development (Docker Compose)

### Prereqs
- Docker Desktop / Docker Engine + Docker Compose

### Start stack

```bash
cp .env.example .env
docker compose up -d --build
docker compose run --rm migrate
```

### URLs
- **Site**: `http://localhost/`
- **Library app**: `http://localhost/library/`
- **API health**: `http://localhost/healthz`
- **API version**: `http://localhost/api/version`

### Logs

```bash
docker compose logs -f caddy api postgres
```

### Stop

```bash
docker compose down
```

## Production baseline (Ubuntu VM/VPS + Docker Compose)

### Topology
- **Caddy**: TLS termination + static delivery + reverse proxy `/api/*`
- **API**: FastAPI (container)
- **Postgres**: durable storage (container + volume)
- **Backups**: nightly logical dumps to disk with retention

### VM setup (high level)
- Create an Ubuntu VM/VPS with a persistent disk.
- Install Docker + Docker Compose plugin.
- Create a deploy directory (e.g. `/opt/wescripture`) owned by a deploy user.
- Place a production `.env` on the VM (not committed to git).

### Caddy TLS
For production, update `Caddyfile` to use your real hostname instead of `:80`:

```caddy
your-domain.com {
  # same handlers
}
```

Caddy will obtain/renew TLS automatically (Let’s Encrypt).

### Backups and restore
- Backups write to `./backups/postgres/` on the host (mounted into the `pg_backup` container).
- Retention is controlled by `RETENTION_DAYS`.

Restore example (to a fresh DB):

```bash
gunzip -c backups/postgres/backup-YYYY-MM-DD.sql.gz | psql "$DATABASE_URL" -v ON_ERROR_STOP=1
```

Operational requirement: do at least one restore drill after initial setup, and after any major DB changes.

## Environments
- **local**: laptop/dev, Compose defaults, insecure secrets ok.
- **production**: VM/VPS, real secrets, TLS on, backups enabled, limited access.
- **staging (recommended)**: same as production, separate hostname + DB.

## Netlify (temporary fallback)
`netlify.toml` exists for fallback static hosting, but the primary deployment path is now the VM/VPS Docker stack so iteration is not gated by Netlify build minutes.

URL layout for the static reader vs landing differs between Netlify (`publish = library`) and VPS (repo root at `/`, reader under `/library/`). See [`docs/ENVIRONMENT_URLS.md`](docs/ENVIRONMENT_URLS.md).

