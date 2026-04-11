# AGENTS.md

## Cursor Cloud specific instructions

### Services

| Service | Command | Port | Notes |
|---|---|---|---|
| **Frontend (static)** | `python3 -m http.server 8080 --directory /workspace` | 8080 | Serves the full site; `index.html` is the landing, `library/` has the reader |
| **FastAPI API** | `uvicorn server.app.main:app --host 0.0.0.0 --port 8000` | 8000 | Stateless health/session endpoints; no DB required for `/healthz`, `/api/version`, `/api/whoami` |
| **Pipeline** | `python3 lds_pipeline/orchestrate.py --once --no-scout` | — | Quick single-wave pipeline check; see `CLAUDE.md` for full orchestration |

### Caveats

- **No root `package.json`**: `node_modules/` is pre-committed with Puppeteer for test scripts only. There is no `npm install` step.
- **No configured linter**: The repo has no ESLint, Prettier, Ruff, or similar. Use `python3 -m py_compile <file>` for Python syntax checks.
- **`$HOME/.local/bin` not on PATH by default**: After `pip install`, binaries like `uvicorn` live in `~/.local/bin`. Prepend it: `export PATH="$HOME/.local/bin:$PATH"`.
- **`library/` is large data**: Per `CLAUDE.md`, avoid reading/scanning `library/` unless the task is data work. Reference paths only.
- **Docker Compose stack is optional**: The `docker-compose.yml` (Caddy + FastAPI + Postgres) is for VPS deployment, not required for local dev.
- **Netlify deploy requires auth**: `npx netlify-cli deploy --prod --dir library` needs `netlify link` + CLI auth token. Not available in cloud agent by default.
- **Static smoke test**: `./tools/smoke_static_deploy.sh http://localhost:8080` checks JSON endpoints locally (requires the static server running).
