# The Good Project — Agent Mission

Read `MISSION.md` first — all of it. That document is the soul of the project.
It contains the vision in the words of the prophets, what we are building, and
the four methods that govern every decision: Connection, Spiritual Arcing,
Depth and Breadth, and Everything Has a Story.
This document is the operational layer for executing inside that vision.

Its product goal is simple:

- create the shortest path to both depth and breadth on a single subject
- let a serious reader move from one verse or paragraph into the best connected
  material without losing provenance or context
- prefer clarity, usefulness, and insight over ornamental features

## Product Standard

Agents working on this project should optimize for:

- clean reading first
- deep linking that actually opens the source and keeps recursion alive
- provenance that stays visible, so readers know what kind of text they are in
- interfaces that reduce friction instead of adding ceremony
- regression resistance, because silent corpus breakage destroys trust

## Manner

The style should be disciplined and product-focused:

- build something people doing real study would actually want to use
- favor concrete gains over abstract cleverness
- surface the shortest useful path, then let power users go deeper
- treat every broken verse, dead link, and unreadable source as product debt
- prefer honest diagnostics over flattering metrics

## Definition Of Better

A change is better when it helps a reader:

- understand where a text comes from
- see why a connection matters
- reach a stronger source faster
- keep traversing without confusion
- trust that the text on screen is clean, accurate, and readable

## Agent Federation

This project runs distributed agents that each pull the repository, claim a task
from the shared ledger, execute it, and push results back. Every claim and completion
is pushed to origin immediately so all agents see current state.

Before starting any work:

```bash
git pull origin main
python3 lds_pipeline/task_ledger.py next --agent YourAgentName
```

When done:

```bash
git add <files>
git commit -m "T-XXXX: description"
git push origin main
python3 lds_pipeline/task_ledger.py complete --task-id T-XXXX --agent YourAgentName \
  --commit $(git rev-parse --short HEAD) --notes "what was done"

# Required: spawn one follow-on task from what you observed while doing the work
python3 lds_pipeline/task_ledger.py append --type queue \
  --title "The next most valuable thing to do, grounded in what you just learned"
```

The queue never runs dry because every agent feeds it. Every new task must be
grounded in direct observation and must serve the mission: deepen reading, improve
connections, clean the corpus, or make traversal faster and more trustworthy.

**Corpus task supply (automated):** The backlog is meant to be **TOC-sized** plus
**entity registries** (Wikipedia, `christ_connection`, etc.). **`lds_pipeline/task_scout.py`**
(default `--streams all`) appends `task_queued` rows for: chapter entity spans,
missing `_notes.html`, Donaldson gaps by book, and **batched registry work**
(scripture people / places / things / topics / `people.json`). Titles match
**`lds_pipeline/task_dispatch.py`** so **`task_worker.py --backend dispatch`**
runs local pipelines (including Ollama-backed `generate_christ_connections.py`)
without re-explaining the mission each time.

**Autonomous loop:** **`lds_pipeline/autonomous_runner.py`** pulls `main`, runs
`task_scout` when pending count is below `--min-pending`, then **`task_worker.py --backend hybrid`**
(dispatch first, Claude if no rule). After each **successful** completion,
**`task_followup.py`** (Ollama, default `gemma4:e2b` — lighter than `e4b` / `latest`) appends **one** grounded
follow-on task from the git diff and pushes the ledger. Use `--no-followup` or
`--no-scout` when you need to disable either behavior.

Humans and chat agents should still append high-judgment tasks; scout + followup
are the baseline so the queue does not depend on repeated manual prompting.

**Orchestration (default):** `./lds_pipeline/launch_agents.sh` runs **`orchestrate.py`**
(pull → `task_scout` when pending is low → parallel worker waves until the queue drains).
Use `./lds_pipeline/launch_agents.sh --legacy` for the old single-worker **`autonomous_runner.py`** loop.
CLI: `python3 lds_pipeline/orchestrate.py` (`--backend`, `--wave-size`, `--max-waves`, `--no-scout`, `--once`).
**Always-on loop:** `./lds_pipeline/run_orchestrate_forever.sh` (re-runs orchestrate after each drain; `ORCHESTRATE_LOOP_SLEEP` between cycles, default 120s).
Cursor agents are instructed to **execute** orchestrate when you ask for workers — not only suggest commands (see `.cursor/rules/agent-orchestrate.mdc`).

**Small scout tasks (default):** `task_scout` queues **one** Wikipedia entry and **one** Christ-connection per task (`TASK_SCOUT_WIKI_CHUNK` / `TASK_SCOUT_CHRIST_CHUNK` default **1**), **one Donaldson chapter per task** (`TASK_SCOUT_DONALDSON_BUNDLE=1`). Raise those env vars to batch. **`--micro`** is 1/1/1 (same as defaults). **Pause workers:** `./lds_pipeline/pause_agents.sh` (or `PAUSE_TRACK_FEED=1` to also stop `track_feed.py`). **Workers** print `models: backend=… claude_cli=… ollama=…` after each claim; set **`OLLAMA_MODEL`** for local Ollama (christ generation + followup).
**Parallel throughput (manual wave):** `./lds_pipeline/run_parallel_task_workers.sh`
starts one worker per slot (default count ≈ `2×CPU`, capped by `MAX_PARALLEL_WORKERS`, default 16);
agents are named `Worker000`…`Worker015`. Set `TASK_WORKER_BACKEND=hybrid` for dispatch-first.
**Drain the queue:** `./lds_pipeline/run_task_drain.sh [wave-size]` runs wave after wave until
`pending-count` is zero (does not run scout — refill with `task_scout` or `autonomous_runner` first).
`python3 lds_pipeline/task_ledger.py pending-count` prints pending tasks only.
**Activity feed (local, pipe-friendly):** `python3 lds_pipeline/track_feed.py --follow` streams merged ledger + orchestrator + worker lines to stdout and appends **`diagnostics/track.feed.txt`** — use **`tail -f diagnostics/track.feed.txt`** in another terminal. Not deployed. Optional: `watch_progress.py` (full-screen refresh) or `tail -f diagnostics/orchestrate.log` (verbose orchestrator only).

**“Is it running?”:** `python3 lds_pipeline/watch_it.py` refreshes a dashboard (ledger counts, `pgrep` counts for orchestrate/workers/track_feed, tail of `track.feed.txt`). `python3 lds_pipeline/watch_it.py --once` for a single snapshot.

**Verse done-ness dashboard:** `python3 lds_pipeline/build_verse_coverage.py` writes
`library/verse_coverage.json` (Donaldson + entity markup + verse discovery per verse).
Open `library/verse_coverage.html` locally or after deploy to see the table and heatmaps.

**Ops dashboard (auto-refreshing):** `python3 lds_pipeline/build_dashboard_state.py` writes
`library/dashboard_state.json` (ledger snapshot + coverage summary). Open
`library/dashboard.html` — it polls every 15s. Re-run the script and push after ledger
or coverage changes so the live site updates; optional `library/agent_heartbeat.json`
is merged in if you commit it from runners.

Full design system reference: `AGENT_GUIDELINES.md`
