# Flow Rearchitecture — Analysis + Plan

Date: 2026-08-02. Source: Reif's own words across session transcripts + MISSION.md, checked against the live app (local walk-through, desktop + mobile, screenshots).

## The vision, distilled from Reif's transcripts

> "I come closer to Jesus Christ because of the meaning I get from the scriptures as I use this app."

- **Primarily a scripture reading tool** — reading first, everything else serves it.
- **Double pane**: verse on the left; footnotes on the right in **panes: cross-references, commentary, other translations** (ESV/NIV-class; public-domain first per docs/TRANSLATIONS.md).
- **Come Follow Me by date**: open the app, hit Today, be reading the current week immediately.
- Etymology / word-origin material is high-value — never strip it.
- Long commentary must be paragraphized; connections must not be broken links.
- Later wave: sentence-level linking scripture↔documents and documents↔documents.

The user journey Reif defined: **open → find my CFM reading → read seamlessly → click a verse → see its context (Donaldson + others)**.

## Findings (ranked by damage to that journey)

### 1. Today flow was broken three ways — FIXED (code) / OPEN (data)
- `getTodayWeek()` hardcoded `new Date('2026-07-12')` — Today jumped to the 2 Kings week forever. **Fixed** (real local date, ISO string compare).
- 7 weeks have `refs: []` (Esther, Amos/Obadiah/Jonah, Micah–Zephaniah, Malachi, Intro, Easter, Christmas) → Today was a silent no-op those weeks. **Fixed** (title-derived target + nearest-week fallback).
- **OPEN — data**: `library/cfm_2026.json` refs are incomplete. Week 31 title is "Ezra 1; 3–7; Nehemiah 2; 4–6; 8" but refs contain only Ezra 1 and Nehemiah 2 — the generator kept only the first chapter of each range. Regenerate all weeks with full chapter ranges. Also: file is 2026-only; Today dies on 2027-01-01.

### 2. Arriving via Today gives zero CFM context
You land in a bare chapter. No week title, no list of the week's chapters, no sense of progress, no way to step Ezra 1 → 3 → 4 (next-chapter follows book order, not the reading list). The flagship flow drops its own thread — against MISSION.md's "without losing their place."

### 3. Verse panel does not match the vision's pane structure
Current stack order: entity chips → Add note → **Donaldson (unbroken 6,000-char italic wall)** → Connections → Key words → **Cross References (bottom)**. Problems:
- **Translations pane: does not exist** (0 occurrences in reader). Research finished in docs/TRANSLATIONS.md, never implemented.
- Cross-references — the fastest meaning-payoff and first pane in Reif's spec — are buried below the commentary wall.
- Donaldson source JSON has no `\n\n`, so `renderCommentaryParagraphs()` no-ops on exactly the text it was built for. Paragraph breaks must be restored at extraction time.
- Donaldson bleed: some files carry adjacent verse text as "notes" (e.g. `donaldson/1_chronicles_15.json` verse 25's note is just verse 26's scripture text). Known T-0219 class.

### 4. Two competing homes, inconsistent brand
- Root `index.html` (marketing): blue pill CTA off the gold/navy serif system; book grid in **alphabetical order** (1 Chr, 1 Kgs, 1 Sam, 2 Chr … Amos, Dan, Deut) — meaningless order for scripture; duplicate navigation vs reader home.
- Reader home: canonical order, Continue card, Community Feed stuck on "Loading…" forever when Supabase is unreachable (requests ERR_FAILED silently; no error/empty state).
- **Monitor** (internal ops page) is a floating button visible to every user on both pages.
- `.netlify/functions/config` 404s on every load.

## Rearchitected flows

### Flow A — Open → read today (core loop)
1. **One home.** Reader home is the home. Root page becomes a thin landing (single CTA, brand-consistent) or a redirect; kill the duplicate alphabetical grid.
2. **Today card on reader home**: "This week — Ezra 1; 3–7; Nehemiah 2; 4–6; 8" with chapter chips + Continue-reading card above the browse grid.
3. **In-chapter CFM strip** when arrived via Today: week title + chapter chips + prev/next that walk the week's reading list, not book order.
4. **Regenerate cfm_2026.json** with full chapter ranges; add 2027 handling (or a graceful "new schedule coming" state).

### Flow B — Verse → meaning (the panel)
Restore the chosen Edition C design: pill tabs, reading-first.
1. **Tabs: Refs · Commentary · Words · Translations** (order = Reif's pane spec; entity chips stay on top).
2. Cross-references first — one tap from verse to scripture-to-scripture meaning.
3. Commentary tab: Donaldson collapsed to first paragraph + "read more"; fix extraction to emit real paragraph breaks; filter bled verse-text notes.
4. **Translations tab (new)**: phase 1 = public-domain WEB + ASV side-by-side per docs/TRANSLATIONS.md schema.

### Flow C — Trust & polish
- Gate Monitor button behind `?dev=1`.
- Feed card: hide or show an honest error state when Supabase fails.
- Root page brand: gold/navy serif system, canonical book order if the grid stays.
- Kill the `.netlify/functions/config` 404 (ship a static fallback or guard the fetch).

## Execution order (each independently shippable)
1. Flow B panel reorder + collapse (biggest meaning-per-click win) — UI only.
2. Flow A items 2–3 (Today context strip + home card) — UI + small state.
3. cfm_2026.json regeneration (data; unblocks correct week walking).
4. Donaldson extraction re-run (paragraph breaks + bleed filter) — pipeline.
5. Flow C polish sweep.
6. Translations phase 1 (new data + tab).
