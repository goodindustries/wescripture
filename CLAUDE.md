# CLAUDE.md — WeScripture

## Project
Scripture search and study platform. Frontend: HTML/CSS/JS. Backend pipelines: Python.
Data lives in `library/` and `model/`. Agents live in `agents/`.

## Token Rules (enforced always)
- No preamble. No recap. No filler phrases. Start with the action or answer.
- No unsolicited explanations. Code only unless explanation is asked for.
- Diffs over full rewrites when change is < 30% of file.
- Batch all related edits into one operation.
- Done = one line: what changed. Nothing else.
- If output would exceed 150 lines, stop and confirm before continuing.

## Compaction — say "→ /compact now" after any of these:
- Feature complete
- Bug resolved
- Diagnostic/test session ends
- Exploration phase ends
- Dead end, changing approach
- Session exceeds ~35,000 output tokens
Never compact mid-implementation.

## File Scope — read ONLY what the task requires
Forbidden (never read or scan):
- `node_modules/`
- `library/` (large data files — reference by path only unless task is data work)
- `assets/tmp_*` and `tmp_*.jpg`
- `diagnostics/` (unless task is diagnostics)
- All `test-mobile-diag*.js` files (archived — do not load)
- `.idea/`, `.DS_Store`, `*.bak`

Active working files:
- `index.html`, `styles.css`, `approach.html`, `contact.html`
- `agents/` (when working on agent logic)
- `lds_pipeline/` (when working on pipeline)
- `tools/` (when working on tooling)

## Test Scripts — Cleanup Rule
Any `test-*.js` or `test-*.py` file older than the current task should be deleted
after the task is complete, not accumulated. Ask before deleting if unsure.

## Model Routing
- Default: Sonnet (reasoning, architecture, complex debugging)
- Subagents / exploration / file reading: Haiku or local (Ollama)
- Routine tasks (linting, search/replace, file ops): local model preferred
- Do NOT use extended thinking for HTML edits, CSS changes, or data formatting

## Local LLM Tasks (route to Ollama when available)
These tasks do NOT need Sonnet:
- Reading and summarizing scripture data files
- Finding references or cross-references in library/
- Formatting, linting, or cleaning JSON/HTML
- Running test scripts and reporting pass/fail
- Searching codebase for patterns
- Generating boilerplate HTML sections

## Git Discipline
- Commit after every working milestone before starting new work
- Commit message format: `[area] what changed` (e.g. `[search] fix verse lookup timeout`)
- Never start a new feature on a dirty working tree
- This prevents context loss at compaction and token limit boundaries

## Architecture (quick ref)
- Frontend: static HTML/CSS/JS, deployed via Netlify
- Data pipeline: Python scripts ingesting scripture sources into library/
- Search: client-side or pipeline-driven, see agents/
- Agents: autonomous task runners, see AGENT_GUIDELINES.md for contract
