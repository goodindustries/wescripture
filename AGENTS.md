# AGENTS.md — WeScripture

Cursor agents read this first. Project context + working contract.

## Project
Scripture search and study platform. Frontend: HTML/CSS/JS. Backend pipelines: Python.
Data lives in `library/` and `model/`. Multi-agent coordination runs through
`task_ledger.py` at the repo root.

## Agent Startup (every session, in order)

1. `python3 task_ledger.py` — read the brief. That *is* your context across sessions.
   (last handoff + decisions, in-progress, blocked, pending by plan/phase, recent notes)
2. If `brief` shows `[NEEDS-EST]` or `[NEEDS-SPLIT (Np)]`, decompose BEFORE claiming:
   - `python3 task_ledger.py decompose T-XXXX --agent <you>`
   - Uses Fibonacci scale (1,2,3,5,8,13). Every leaf must be **1 point**.
   - If no local LLM (Ollama/Anthropic), the command prints a prompt and exits 2.
     Fulfill the `LEDGER_FULFILL_COMMAND` it prints, then rerun `decompose`.
3. For non-trivial work (3+ steps, multi-file, or real trade-offs):
   - Write a plan at `.cursor/plans/<slug>_<shortid>.plan.md`.
   - Seed root tasks via `python3 task_ledger.py add "..." --plan <slug> --phase <phase-id>`
     (bulk seeding belongs in `scripts/seed_<name>.py`).
   - Run `decompose` on each root until all leaves are 1pt.
4. Open a session and work **only on 1pt leaves**:
   - `python3 task_ledger.py session start --agent <you> --goal "..."`
   - `status T-XXXX --agent <you> --status in_progress --note "..."`
   - commit, push, then `--status completed --commit <sha> --note "..."`
   - Parents auto-roll-up to `completed` when every child is terminal.
5. Close with a handoff (required — this is the continuity mechanism):
   - `python3 task_ledger.py session end --agent <you> --handoff "..." --decision "..." --decision "..."`

Full contract: `AGENT_GUIDELINES.md` §7.

## Working Rules

- **No preamble. No recap. No filler.** Start with the action or answer.
- **Diffs over rewrites** when change is <30% of file.
- **Batch related edits** into one operation.
- **Done = one line**: what changed. Nothing else.
- **Commit after every working milestone** before starting new work.
- Commit format: `T-XXXX: what changed` when a task id exists; else `[area] what changed`.
- Never start a new feature on a dirty working tree.

## File Scope — read ONLY what the task requires

Forbidden unless the task requires them:
- `node_modules/`
- `library/` (large data files — reference by path only unless task is data work)
- `assets/tmp_*` and `tmp_*.jpg`
- `diagnostics/` (unless task is diagnostics)
- All `test-mobile-diag*.js` (archived)
- `archive/` (prior ledger + archived modules, read-only reference)
- `.idea/`, `.DS_Store`, `*.bak`

Active working surface:
- `task_ledger.py`, `task-ledger.jsonl`, `ledger-state.json` — coordination
- `library/index.html`, `library/chapters/` — reader
- `server/` — FastAPI (post-rearchitect)
- `pipeline/` — corpus ingestion (post-rearchitect)
- `agents/` — agent profile docs
- `scripts/` — one-shot utilities (e.g. `seed_ledger.py`)

## Test Scripts — Cleanup Rule

Any `test-*.js` or `test-*.py` older than the current task should be deleted after
the task is complete, not accumulated. Ask before deleting if unsure.

## Architecture (quick ref)

- Frontend: static HTML/CSS/JS, deployed via Netlify
- Backend (v1, in progress): Supabase Postgres + pgvector, thin FastAPI at `server/`
- Corpus pipeline (v1, in progress): `pipeline/` with Makefile DAG
- Legacy: `lds_pipeline/` — autonomous agent loops, slated for archive (ledger task T-0010)
