# WeScripture Build Plan

Date: 2026-08-02. Inputs: docs/FLOW_REARCHITECTURE.md (vision + ranked gaps), plus three deep-research passes: (1) best-in-class Bible study app UX (Logos, Olive Tree, Accordance, Blue Letter Bible, STEP, NET, BibleHub, YouVersion), (2) LDS study ecosystem (Gospel Library, ScripturePlus, BYU Scripture Citation Index, Gospel Study App, Scripture Notes) + Come Follow Me 2026 structure, (3) linked-canon data architecture (Sefaria, OpenBible.info, CTS URNs, static-site link sharding).

## North star

> "I come closer to Jesus Christ because of the meaning I get from the scriptures as I use this app."

Reading tool first. Verse on the left; meaning one tap away on the right — cross-references, commentary, words, translations. Today → Come Follow Me is the flagship entry.

## What the research says (distilled)

**The winning formula across every best-in-class app is three things at once:**

1. **Verse is the center of gravity.** Commentary, cross-refs, translations, notes all orbit one active verse; tap verse → panes sync. (Logos Passage Guide, Olive Tree auto-sync pane, Sefaria connection panel, ScripturePlus study panel.)
2. **Daily reading is stupidly easy.** One "Today" affordance on home, < 1 second to active reading, visible progress, week context never lost. (YouVersion Today button; Gospel Library auto-surfaces the right CFM lesson on the right week.)
3. **Depth without navigation.** Meaning opens beside the text, never instead of it — side panel / bottom sheet, not a page change. (Sefaria, ScripturePlus, Gospel Library sidebar, STEP inline expansion.)

**The open differentiator.** The LDS ecosystem is layered: Gospel Library owns canon + infrastructure; third-party apps own the intellectual value-add (ScripturePlus commentary, Scripture Central scholarship, BYU Citation Index conference-talk linkage). **No one puts canon + scholarly commentary + prophetic guidance in one flow.** The BYU Scripture Citation Index's verse → General Conference talks index is the proven killer pattern (who cited it, when, jump to the moment in the talk) — and it has zero CFM integration. WeScripture already has Donaldson commentary and a Today→CFM flow; adding conference-talk citations per verse completes the trifecta no one else offers.

**The architecture precedent.** Sefaria proves the data model (typed, categorized link records addressed by hierarchical refs, served as static exports); OpenBible.info proves community-weighted cross-references work as a flat file with a numeric rank (filter rank ≥ threshold client-side); CDN practice proves per-chapter JSON shards scale to hundreds of thousands of links with no server. Scripture text is immutable, so simple `Book Chapter:Verse` position addressing is sufficient — no fuzzy anchoring needed.

## Design principles (each traceable to research)

1. **Never navigate away from the text.** All meaning renders in the panel beside the verse. (Sefaria, ScripturePlus, Olive Tree)
2. **Cross-references first.** Fastest meaning payoff; scripture explaining scripture beats any commentary wall. (Reif's pane spec; STEP; BYU SCI usage pattern)
3. **Show counts before content.** Category headers with counts ("Refs 12 · Commentary 3"); empty categories disappear. (Sefaria's dynamic category list)
4. **Collapse long-form by default.** First paragraph + read-more. Dense walls are the #1 complaint about Blue Letter Bible / BibleHub. (Donaldson today is exactly this failure)
5. **Today is one tap and keeps its thread.** Land in the reading with week title + chapter chips + prev/next that walk the week's list, not book order. (YouVersion; Gospel Library CFM auto-surface; #1 hated pattern = daily reading hidden behind menus)
6. **Distraction-free canon.** Nothing interrupts the scripture text itself — no ops buttons, no loading spinners mid-column, no ads ever. (universal praise/hate pattern)
7. **Static-first data.** Per-chapter JSON shards, pre-ranked at build time, lazy-loaded per chapter, client-side filtered. No server for reading. (Sefaria-Export, OpenBible, CDN sharding)
8. **Preserve etymology / word-origin material.** High value per Reif; the ecosystem's most-requested missing feature is original-language tooling. (Gospel Library gap list)

## Link data schema (foundation for phases 3+)

- **Verse ID:** `book/chapter/verse` slug, matching existing library paths (e.g. `ezra/1/3`). Human-readable, edition-independent, CTS-spirit without URN ceremony.
- **Shard layout:** one JSON per chapter — `library/links/<book>/<chapter>.json`. Loaded lazily when a chapter opens; ~5–50KB each.
- **Link record:** `{ from: "ezra/1/3", to: "isaiah/44/28", type: "xref" | "commentary" | "talk" | "word", rank: 0–100, label, source }`. Pre-sorted by rank at build time; client filters by type into panel tabs.
- **Cross-ref source:** OpenBible.info dataset (CC-BY, 340K refs, votes as rank). Filter `rank >= 10` for default view; "show all" reveals the rest.

## Status (2026-08-02, end of session)

| Phase | State |
|---|---|
| 1 — Verse panel Edition C | **Shipped** `eae80df`, polish `17ec7a1` `d13361e` |
| 2 — Today keeps its thread | **Shipped** `ab0adbf` |
| 3 — CFM data regeneration | **Shipped** `e04fea8` (137 → 447 chapters) |
| 4 — Donaldson bleed | **Shipped** `86113e3` (1,132 bad notes removed) |
| 5 — Translations tab | **Shipped** (WEB + ASV, 1,189 chapters) |
| 6 — Conference talks per verse | Not started — the remaining differentiator |
| 7 — Trust & polish | Netlify 404 + feed hang done; one-home decision open |

Link-shard adoption (part of Phase 3) is still open: cross-references remain in
their existing structure. The translations shards are the first data laid out
in the per-chapter scheme described above, and they prove the pattern.

Reader suite: `./tests/reader/run.sh` — six browser tests, each written red
first against a real defect.

## Phases (each independently shippable; order = meaning-per-click, then data, then depth)

### Phase 1 — Verse panel, Edition C (SHIPPED)
Goal: one tap on a verse = fastest possible meaning.
- Pill tabs: **Refs · Commentary · Words · Translations** (entity chips stay on top).
- Cross-references first tab, first paint.
- Donaldson collapsed to first paragraph + read-more.
- Tab counts; empty tabs hidden (Sefaria pattern).
- Code: `library/index.html` ~line 4950 (renderVersePanel* / panel-section blocks).
- Done when: screenshot shows tabs in order; tap verse → Refs visible without scrolling; Donaldson ≤ 1 paragraph until expanded.

### Phase 2 — Today keeps its thread (SHIPPED)
Goal: flagship flow never drops the user.
- In-chapter CFM strip when arrived via Today: week title + chapter chips + prev/next walking the week's reading list (Ezra 1 → 3 → 4), not book order.
- Reader-home Today card: "This week — <title>" + chapter chips + Continue.
- Done when: Today → Ezra 1 → next lands Ezra 3; strip shows full week.

### Phase 3 — CFM + link data regeneration (CFM SHIPPED; link shards open)
Goal: correct data under Phase 2's UI.
- Regenerate `library/cfm_2026.json` with **full chapter ranges** (week 31 must contain Ezra 1, 3–7, Neh 2, 4–6, 8) and fill the 7 empty-refs weeks.
- Graceful 2027 state (or 2027 schedule if published).
- Adopt link schema above; migrate existing cross-refs into per-chapter shards; integrate OpenBible ranks.
- Done when: script validates every week's refs against its title; spot-check 5 weeks; panel reads from shards.

### Phase 4 — Donaldson re-extraction (BLEED SHIPPED)
Goal: commentary that reads like paragraphs, not a wall.
- Re-run extraction emitting real `\n\n` paragraph breaks (renderCommentaryParagraphs currently no-ops).
- Filter bled adjacent-verse text (1_chronicles_15.json class).
- Done when: random 10-file sample shows paragraphs + no verse-text-as-note.

### Phase 5 — Translations tab (SHIPPED)
Goal: the missing fourth pane.
- Public-domain WEB + ASV, side-by-side in the Translations tab (KJV inline stays canonical).
- Per-chapter shards same as links.
- Done when: tap verse → Translations tab shows KJV/WEB/ASV for that verse.

### Phase 6 — Conference talks per verse (the differentiator)
Goal: "What have prophets said about this verse?" — one tap.
- Data pipeline: General Conference citations per verse (BYU SCI pattern: speaker, talk, date, count; link to churchofjesuschrist.org talk anchor).
- New "Talks" entry in panel (inside Refs tab or fifth pill — decide at build).
- This is the feature no app combines with CFM; WeScripture's moat.
- Done when: Isaiah 1:18 shows real talk citations with speakers + dates.

### Phase 7 — Trust & polish (404 + feed SHIPPED)
- Supabase feed: honest error/empty state (no eternal "Loading…").
- Kill `.netlify/functions/config` 404 (static fallback or guarded fetch).
- One-home decision: root page → thin landing or redirect (open question in FLOW_REARCHITECTURE.md).

### Later wave (explicitly deferred)
- Original-language word data (Strong's-keyed Hebrew lexicon; ecosystem's most-requested gap) — extends Words tab.
- Reading progress / streaks (YouVersion pattern — gentle, no guilt).
- Sentence-level doc↔doc linking (W3C position selectors suffice; text immutable).
- Audio + read-along highlight.

## Non-goals (for restraint)

- No user accounts required to read. Sync-only features can require login later.
- No server-side rendering; static + lazy JSON stays the architecture.
- No AI-generated commentary in canon flow.
- No 30-translation dumps (BibleHub overload pattern) — curated few, well-chosen.
