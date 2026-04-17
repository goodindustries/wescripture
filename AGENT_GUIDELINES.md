# Agent Guidelines — WeScripture

This document is the canonical reference for any agent (Claude, autonomous script,
or human contributor) working in this repository. Read it before writing a line.

---

Read `MISSION.md` before this document. The mission and methods there are the
reason every guideline below exists.

---

## 1. Design Tokens

All UI is built from these CSS custom properties. Never hardcode these values; use
the variable name everywhere so the palette stays consistent.

```css
:root {
    --bg:           #F5F2EC;   /* warm off-white page background */
    --text:         #1C1C1C;   /* primary body text */
    --muted:        #6C6C6C;   /* secondary labels, metadata, captions */
    --accent:       #9C7A4D;   /* brand amber — links, highlights, active states */
    --accent-hover: #7A5E38;   /* darkened amber for hover */
    --divider:      rgba(0,0,0,0.09);  /* hairline separators */
    --nav-h:        52px;      /* fixed navigation bar height */
    --toc-w:        340px;     /* sidebar / table-of-contents width */
    --reader-max:   760px;     /* maximum content column width */
}
```

Entity annotation colors (inline verse underlines):
- **Person** entity: `var(--accent)` dotted underline (`#9C7A4D`)
- **Place** entity: `#4a7090` dotted underline (steel blue)
- **Thing** entity: `#6a4a8c` dotted underline (muted violet)

---

## 2. Typography

```
Font stack: 'Inter', -apple-system, sans-serif
Font rendering: -webkit-font-smoothing: antialiased

Sizes used in the library:
  10px  uppercase label / provenance metadata
  11px  secondary annotations, search results, status text
  12px  TOC subtitles, nav metadata
  13px  body reading text, discovery panel entries
  14px  verse body text (--verse-font-size)
  15px  chapter headings, section sub-heads
  18px  book / major heading
  22px  primary screen title

Weight conventions:
  400 — body
  500 — slightly emphasized labels
  600 — section headers, panel titles
  700 — ALL CAPS labels (letter-spacing: .1em)

Uppercase label pattern (reuse this exact style):
  font-size: 10px; font-weight: 700; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted);
```

---

## 3. Layout Patterns

### Three-panel shell
```
#shell: fixed, top: var(--nav-h), fills remaining viewport
  #toc:    left panel, width: var(--toc-w), background: #FEFCF8
  #reader: center column, flex: 1, overflow-y: auto
  #panel:  right discovery panel, slides in from right, fixed width 380px
```

### Discovery panel entry
```
padding: 9px 12px
cursor: pointer
border-bottom: 1px solid var(--divider)
hover: background rgba(0,0,0,0.03)
```

### Cards (quote, hist, note)
Left accent bar: `box-shadow: inset 3px 0 0 var(--accent)`
Background: neutral, no fill by default.

### Active/selected state
Selected verse: `box-shadow: inset 3px 0 0 var(--accent), 0 0 0 1px rgba(156,122,77,0.18)`

---

## 4. Interaction Model

**Verse click** → opens discovery panel with:
1. Verse text header (verse ref + full text)
2. People · Places · Things chips (entity scan of verse text)
3. Commentary cards from the corpus (talks, books)
4. Key Words — English headword as printed in the verse + compact original-language word study (lemma line optional; no concordance numbers in copy)

**Entity chip / annotated word click** → opens entity profile panel before word study

**Word click (span.w)** → word study panel (frequency, scripture cross-refs, compact lexical/spiritual note where available)

**TOC tile click** → loads chapter HTML into #reader via `loadChapter(id)`

Rule: every click must open something useful or do nothing. No dead ends.

**Completed-chapter panel shell (visual spec):** `library/test.html` (deployed:
[wescripture.netlify.app/library/test.html](https://wescripture.netlify.app/library/test.html))
is the layout prototype for the right column: `#panel` / `#panel-body`, empty state,
`panel-header` (ref + italic verse), uppercase `panel-section` bands, then stacked
`word-card`, `note-card`, `quote-card`, `scrip-card`, and `hist-card` patterns.
The prototype omits **People · Places · Things** chips by design; production
`index.html` must keep that entity row — it sits under the header, before Key Words.

---

## 5. Data Conventions

### Entity IDs
```
person:snake_case      e.g. person:joseph_smith, person:nephi_1
place:snake_case       e.g. place:jerusalem, place:jordan_river
thing:snake_case       e.g. thing:liahona, thing:urim_thummim
topic:snake_case       e.g. topic:faith, topic:atonement
book:snake_case        e.g. book:teachings_of_the_prophet
```

### Scripture figure (has `group` field)
```json
{
  "id": "person:moses",
  "name": "Moses",
  "group": "old_testament",
  "desc": "One sentence summary.",
  "variants": ["Moses", "Moshe"],
  "born": {"year": -1393, "place_name": "Egypt"},
  "died": {"year": -1273, "place_name": "Mount Nebo"},
  "wikipedia_title": "Moses",
  "wikipedia_summary": "...",
  "wikipedia_thumbnail": "https://...",
  "wikipedia_url": "https://en.wikipedia.org/wiki/Moses",
  "scripture_refs": ["exo.2.1", "num.20.1"],
  "ref_count": 842
}
```

### Modern LDS figure (no `group`)
```json
{
  "id": "person:jeffrey_r_holland",
  "name": "Jeffrey R. Holland",
  "desc": "Member of the Quorum of the Twelve Apostles.",
  "wikipedia_title": "Jeffrey R. Holland",
  "wikipedia_summary": "...",
  "wikipedia_thumbnail": "https://...",
  "roles": [{"title": "Apostle", "from": 1994}]
}
```

### Topic entry
```json
{
  "id": "topic:faith",
  "name": "Faith",
  "desc": "One sentence definition.",
  "wikipedia_summary": "...",
  "related_scriptures": ["heb.11.1", "alma.32.21"],
  "canonical_verses": ["heb.11.1"]
}
```

### Scripture reference format
`book_abbrev.chapter.verse` — e.g. `1ne.3.7`, `jn.3.16`, `dc.76.22`

---

## 6. File Map

```
library/
  index.html              — single-page library app (all JS inline)
  entities/
    people.json           — 1,660+ persons (scripture figures + modern LDS)
    people_index.json     — name variant → entity ID lookup
    places.json           — 48+ places
    places_index.json     — name → place ID
    things.json           — 26+ scriptural objects
    things_index.json     — name → thing ID
    topics.json           — 49 topics with related_scriptures
  chapters/               — 1,584 chapter HTML files, one per canonical chapter

task_ledger.py            — multi-agent, cross-session task ledger CLI (canonical)
task-ledger.jsonl         — append-only event log (source of truth)
ledger-state.json         — materialized snapshot (rebuilt on every write; READ THIS FIRST)
scripts/seed_ledger.py    — idempotent seeder (plan → unit chunks)

archive/                  — prior ledger modules + event log (pre-rebuild, read-only)
lds_pipeline/             — legacy autonomous pipeline, slated for archive (T-0010)
  task_ledger.py          — LEGACY; isolated to lds_pipeline/task-ledger-legacy.jsonl

AGENT_GUIDELINES.md       — this file
AGENT_MISSION.md          — product mission and quality standard
agents/                   — individual agent profile documents
```

---

## 7. Agent Workflow — Plan → Decompose → Ledger → Execute

The ledger (`task_ledger.py`) is the coordination surface across agents and
sessions. It is append-only; `ledger-state.json` is the one-file snapshot an agent
reads to know current state without replay.

### 7.1 Startup — zero context required

```bash
git pull origin main
python3 task_ledger.py                       # prints the brief
#   → last session's handoff + decisions
#   → counts by status
#   → in-progress, blocked
#   → pending tasks grouped by plan + phase
#   → 5 most-recent notes
```

If the brief is enough context, skip to 7.4. Otherwise continue.

### 7.2 Plan first (non-trivial work only)

A "non-trivial" task = 3+ logical steps, touches multiple files, or has
meaningful trade-offs. For these:

1. Write a plan to `.cursor/plans/<slug>_<shortid>.plan.md` capturing:
   goal, constraints, target architecture, phased steps, risks, non-goals.
2. The plan is the *why* and *shape*. The ledger is the *what* and *status*.

For trivial single-step changes, skip planning and go to 7.3 — one ledger task
with a clear title is enough.

### 7.3 Decompose with Fibonacci estimation — every leaf is 1 point

Every claimable task must be **1 point** of work. Anything larger is split
recursively until it is. Estimation uses the Fibonacci SWE scale:

```
1pt   ~30 min     single file, single concept       (rename, css rule, one test case)
2pt   ~1 h        single file or trivial multi      (small fn + caller)
3pt   ~2-3 h      multi-file, well-bounded          (new CLI subcommand + tests)
5pt   ~half day   cross-system, single concern      (new endpoint + frontend wire)
8pt   ~full day   requires design choice            (schema + migration + api + reader)
13pt+ epic, MUST be split before working
```

Workflow per task:

```bash
python3 task_ledger.py add "Task title" --plan <plan-slug> --phase <phase-id>
python3 task_ledger.py decompose T-XXXX --agent <you>
#   → runs estimate (LLM picks a Fibonacci number with rationale)
#   → if > 1pt, splits into 2-8 children that should each estimate to 1pt
#   → recurses on each child until every leaf is 1pt
#   → honors MAX_DEPTH=5 (env LEDGER_MAX_DEPTH)
```

LLM provider resolution (automatic, first hit wins):

1. Ollama at `127.0.0.1:11434` if reachable (env `OLLAMA_MODEL`, default `llama3.2:3b`)
2. Anthropic API if `ANTHROPIC_API_KEY` set
3. **Stdout fallback**: `decompose` prints a parseable prompt and exits with
   code 2. The Cursor agent reads the prompt, computes the answer, runs the
   printed `LEDGER_FULFILL_COMMAND`, then reruns `decompose T-XXXX` to continue.

Each decompose call processes as many nodes as it can before emitting the next
prompt — you'll usually make progress in chunks of several nodes per iteration.

A valid 1-point leaf is:

- **Bounded**: ~30 minutes of focused work.
- **Self-contained**: no undefined dependency on a later sibling.
- **Verifiable**: single concrete artifact or a single test passing.
- **Titled by effect, not activity**: `"Write Supabase migration for corpus tables"`
  not `"work on database"`.

Manual overrides (bypass the LLM):

```bash
python3 task_ledger.py estimate T-XXXX --agent <you> --apply --points 3 --rationale "..."
python3 task_ledger.py split T-XXXX --agent <you> --apply \
  --child "first 1pt leaf title" --child "second 1pt leaf title" --rationale "..."
```

Bulk seeding of a plan's root tasks still belongs in `scripts/seed_<name>.py`
(idempotent, reviewable). Decomposition runs after seeding.

### 7.4 Open a session

```bash
python3 task_ledger.py session start --agent <YourName> \
  --goal "What you intend to accomplish this session"
```

One active session per agent. The goal is a sentence, not a paragraph.

### 7.5 Claim and execute (only 1pt leaves)

```bash
# Claim (status = in_progress)
python3 task_ledger.py status T-XXXX --agent <YourName> --status in_progress \
  --note "starting; noted constraint X"

# Progress notes (any time, any number)
python3 task_ledger.py status T-XXXX --agent <YourName> --status in_progress \
  --note "resolved constraint X via Y; next: Z"

# Blocked (keep it claimed, but flag)
python3 task_ledger.py status T-XXXX --agent <YourName> --status blocked \
  --note "blocked: need Supabase service key"

# Done
git add <files> && git commit -m "T-XXXX: short description" && git push
python3 task_ledger.py status T-XXXX --agent <YourName> --status completed \
  --commit "$(git rev-parse --short HEAD)" --note "what shipped in one line"
```

Hold **at most one** in-progress task per agent. Release (`--status pending`) or
complete before claiming the next.

### 7.6 Close the session

```bash
python3 task_ledger.py session end --agent <YourName> \
  --handoff "What the next agent needs to know in one paragraph" \
  --decision "Decision 1 worth preserving" \
  --decision "Decision 2 worth preserving"
```

The handoff + decisions are read verbatim by the next session's `brief`. This is
the continuity mechanism — treat it seriously.

### 7.7 Conflict avoidance

- `task-ledger.jsonl` is append-only. On a merge conflict, **keep both sides**
  (all lines from both versions). No line is ever deleted.
- `ledger-state.json` is derived — on conflict, pick either side and run any
  ledger command (e.g. `python3 task_ledger.py ls >/dev/null`) to rewrite it from
  the jsonl.
- Claim before editing. Never edit files for a task you haven't set to
  `in_progress`.
- Never rebase or force-push `main`.

---

## 8. Quality Gates

Before pushing any library change:

1. Open `library/index.html` in a browser.
2. Navigate to at least one chapter (e.g. John 1).
3. Click a verse. Confirm discovery panel opens.
4. If entity annotation was changed: click a person name. Confirm entity profile.
5. If word index was changed: click a content word. Confirm word study shows results.

For pipeline changes: run with `--dry-run` first, inspect output, then run live.

### UI feature tests (Puppeteer)

**Policy:** New or materially changed UI in `library/` (HTML/JS in `library/index.html`, chapter templates, etc.) should ship with a **dedicated** root-level script: **`test-<feature-slug>.js`**, using the same stack as [`test-library-buttons.js`](test-library-buttons.js) / [`test-title-inline-nav.js`](test-title-inline-nav.js) (Puppeteer + local HTTP server).

**Naming:** Mirror the feature (`test-title-inline-nav.js`, `test-home-iframe-inline-nav.js`, …).

**Agent workflow (review → build → run):**

1. **Review** — Map entry points (selectors, `data-*`, URLs, `postMessage` types) and the happy path.
2. **Infer** — Define 3–8 assertions (initial DOM → primary interaction → outcome).
3. **Build** — Add `test-<feature>.js`; document the base URL in the file header.
4. **Run** — From repo root, serve static files so `library/index.html` is reachable (see script header). Example: `python3 -m http.server 4173` with cwd = repo root → `http://127.0.0.1:4173/library/index.html`. Or `cd library && python3 -m http.server 4173` → `http://127.0.0.1:4173/index.html` (adjust `BASE_URL` in the test).
5. **Gate** — Before merge/deploy on UI changes, run the feature’s test and fix failures.

Tests should assert **user-visible** behavior (navigation, panels, chapter IDs), not internal variables.

---

## 9. What Not to Do

- Do not use `git push --force` on `main`.
- Do not delete lines from `task-ledger.jsonl`.
- Do not hardcode pixel values or colors that are already in the token set.
- Do not create new entity files (people2.json, etc.) — always extend the existing files.
- Do not add `console.log` to production library/index.html.
- Do not create new JS frameworks, build steps, or package.json dependencies.
  The library is intentionally zero-dependency at runtime.
- Do not invent new entity ID patterns — follow the existing `type:snake_case` convention.
