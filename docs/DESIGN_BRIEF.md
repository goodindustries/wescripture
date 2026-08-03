# WeScripture — Design Brief

**For:** an external design team producing a visual design we will implement.
**Date:** 2026-08-03. **Scope:** two surfaces — the Home page and the Reader.
**Status of the current UI:** functional, feature-complete for these surfaces, and visually unresolved. We are asking for a design, not a repaint of what exists.

---

## 1. What this is

WeScripture is a scripture reading app for Latter-day Saints. It carries the full standard works (Old Testament, New Testament, Book of Mormon, Doctrine & Covenants, Pearl of Great Price) plus a large layer of study material attached verse by verse.

**The one sentence that governs every decision:**

> "I come closer to Jesus Christ because of the meaning I get from the scriptures as I use this app."

Two consequences we hold to:

1. **It is a reading tool first.** The scripture text is the product. Everything else serves it and must never compete with it. A person should be able to read for thirty minutes and forget the interface exists.
2. **Meaning is one tap from every verse.** Tap a verse and its context opens *beside* the text — never instead of it, never on another page.

**Who uses it.** Adults doing personal or family scripture study, most often in the morning or evening, most often following *Come Follow Me* — the Church's week-by-week reading curriculum (2026 is the Old Testament year). Roughly half will be on a phone. Many are reading the same passage they have read many times; the app earns its place by making the passage mean more, not by being novel.

**Tone.** Reverent but not solemn. Warm, quiet, made-by-a-person. It should feel closer to a well-made printed edition of scripture than to a productivity app or a social feed. It must never feel gamified, corporate, or like a startup landing page.

---

## 2. What we are not asking for

- Not a rebrand. The name stays. If the wordmark improves, we will listen.
- Not new features. Design what is described here; we will build what you design.
- Not a marketing site. The public root page is a separate, later problem.
- Not dark mode in round one. Design light; note anything that would block a later dark theme.

---

## 3. What is wrong today (our own read)

Attached screenshots show the current build. Our honest assessment:

1. **The reader's resting state is empty.** With the study panel open and no verse selected, half a 1440px screen is blank cream holding one small "✦ Tap a verse to study it." With the panel closed, a 760px text column floats in a 1440px window with ~340px of dead margin on each side. Neither state looks composed.
2. **Scripture reads as a table, not a page.** Every verse sits in its own row with a hairline divider above and below. It scans like a spreadsheet. Printed scripture does not do this, and the dividers are doing work that spacing and indentation should do.
3. **Nothing signals that depth exists.** The study material is the whole point of the app, and a first-time reader has no way to know it is there. There is a small dot on some verse numbers; that is all.
4. **Link noise inside the text.** Named entities (Jerusalem, Judah, Israel) are gold and underlined inline. In a verse with four of them, the underlines fight the sentence.
5. **Alignment is inconsistent.** The book title is centered; the chapter numeral is left; the verse column is left; the week strip is left. No single spine.
6. **The header is undifferentiated.** Breadcrumbs, a "Today" pill, two icon buttons and "Sign in" all sit at similar weight in a thin bar. Nothing leads.
7. **Home is a stack of boxes.** Three rounded cards of near-identical treatment (This Week, Browse, Resume, Feed). Nothing tells you where to look first, and the volume covers are small dark rectangles with text crammed inside.

You are free to disagree with any of this. If you think the divider-per-verse is right and something else is the real problem, tell us.

---

## 4. Hard constraints

These are technical facts, not preferences. Design within them.

| Constraint | Detail |
|---|---|
| **Static site** | Plain HTML/CSS/JS on Netlify. No React, no build step, no CSS framework. Everything you specify gets hand-written as CSS. |
| **Self-hosted fonts** | We can license and self-host webfonts. Budget ~2 families, up to ~4 weights total, for performance. Name specific faces. |
| **Content is fixed** | Scripture text is KJV and cannot be reworded, reflowed mid-sentence, or abridged. Verse numbers must remain visible and addressable. |
| **Chapter HTML is pre-generated** | 1,582 chapter files already carry the verse markup. Deep structural changes to per-verse markup are expensive; changes to layout, type, color, spacing, and chrome are cheap. Flag anything that requires new per-verse elements. |
| **Performance** | Reading must feel instant on a mid-range phone. No heavy imagery behind text, no layout that depends on measuring text in JS. |
| **Accessibility** | Body text ≥16px, contrast ≥4.5:1, visible keyboard focus, 44px touch targets, respects reduced motion. Non-negotiable. |
| **Breakpoints in use** | 375 (phone), 768 (tablet), 1024, 1440+ (desktop). |

**Current tokens** (for reference only — replace them if you have a better system):
background `#F5F2EC`, text `#1C1C1C`, muted `#6C6C6C`, accent `#9C7A4D` (gold), panel `#FEFCF8`, hairline `rgba(0,0,0,.09)`, reading column max 760px, body type EB Garamond 18px/1.78.

---

## 5. Surface one — Home

**Its single job:** get the person into today's reading in one tap, and make returning tomorrow feel obvious.

### Regions, in current priority order

1. **This Week (Come Follow Me).** The flagship entry. Carries: a week title that is itself a scripture reference list (e.g. *"Ezra 1; 3–7; Nehemiah 2; 4–6; 8"*), the date range (*Jul 27 – Aug 2*), one tappable chip per chapter in the week, and a primary action ("Start reading"). **Chapter chips range from 1 to about 30 per week** — the design must hold both without looking broken. Three weeks a year are topical (Easter, Christmas, Introduction) and have no chapters at all; the card hides entirely then, so the layout must not depend on it existing.
2. **Continue / Resume.** Where the person left off: book, chapter, verse, and how long ago. Also recent chapters and saved items. Empty for a first-time visitor.
3. **Browse the library.** 5 volumes → 87 books → 1,582 chapters. Currently: a row of 5 volume covers, then a two-column list of book names for the selected volume, then a chapter grid. Book counts per volume vary wildly (Old Testament 39, Pearl of Great Price 5). Psalms alone has 150 chapters, so the chapter grid must survive that.
4. **Community feed.** Notes and highlights other readers have shared publicly. Optional, signed-out for most people, and frequently unavailable. It must be able to sit quietly or vanish without leaving a hole.

### States to design
- First visit: no history, no resume, feed signed-out.
- Returning mid-week: resume populated, week partially read.
- Topical week: no This Week card.
- Feed unavailable (offline or backend down) — an honest, quiet state, not a spinner that never ends.

### The question we most want answered
Home currently gives Browse, Resume, and This Week near-equal visual weight, so nothing leads. **We believe today's reading should dominate and everything else should recede.** Show us what that looks like — including whether Browse belongs on this page at all or behind an entry point.

---

## 6. Surface two — The Reader

The core of the product. Two panes on desktop; the study pane becomes a bottom sheet on phones.

```
┌──────────────────────────────────────────────────────────┐
│ header: wordmark · breadcrumb · Today · search · account │
├──────────────────────────────────────────────────────────┤
│ Come Follow Me week strip (sticky, when in a week)       │
├────────────────────────────────┬─────────────────────────┤
│                                │                         │
│   SCRIPTURE                    │   STUDY PANE            │
│   book title, chapter numeral  │   verse ref             │
│   verses, numbered             │   entity chips          │
│   continuous scroll into the   │   Add note              │
│   next chapter                 │   tabs: Refs ·          │
│                                │   Commentary · Words ·  │
│                                │   Translations          │
│                                │   tab content           │
└────────────────────────────────┴─────────────────────────┘
```

### 6a. The scripture column — the thing that matters most

This is where a person spends 95% of their time. **If you get only one thing right, get this right.**

- KJV text, verse-numbered. Verses run 1 to 176 in a chapter (Psalm 119); most chapters are 10–40.
- Verse numbers must stay visible and be tappable targets — they carry indicators and open the study pane.
- Reading is continuous: scrolling past the end of a chapter loads the next one inline. Design the seam between chapters — right now it is just a gap, and the reader loses their sense of place.
- A tapped verse becomes the "active" verse and needs a persistent, calm marker while the study pane shows it.
- Some words are entity links (people, places, things) — currently gold underlines. We need a treatment that stays discoverable without shredding the paragraph. **This is an explicit ask.**
- Some verse numbers carry a small indicator meaning "there is study material here." We want people to notice depth exists without the page becoming speckled. **Also an explicit ask.**
- Highlights: readers can highlight passages in 5 colors, and other people's public highlights can overlay the same text. Two overlapping highlight systems on one verse needs a visual answer.

**Type is the whole design here.** Give us a scripture face chosen deliberately — measure, leading, verse-number treatment, how the chapter numeral and book title open a chapter, and what a "page" of it feels like at 375px and at 1440px.

### 6b. The study pane

Opens beside the verse. Contains, in this fixed priority order:

1. **Refs** — cross-references. Other verses that illuminate this one, each a reference plus its full text, tappable to jump. Typically 1–5, occasionally more, sometimes zero. Some carry a source chip (e.g. *Millennial Star*) and a filter row appears when sources are mixed.
2. **Commentary** — verse-by-verse commentary (the Donaldson corpus, 11,783 notes across 14,405 verses) plus "connections" drawn from a wider corpus of Church writings. **Length is brutally variable: median 189 characters, 90th percentile 976, 99th percentile 5,470, longest 57,288.** Long entries are currently clamped to ~6 lines with a "Read more". Design for both the one-line note and the essay.
3. **Words** — key words with original-language and etymological material. Etymology is high-value to us; never design it away.
4. **Translations** — the same verse in World English Bible and American Standard Version alongside the KJV, for comparison. Present only for Bible books (1,189 chapters); absent for Book of Mormon, D&C, Pearl of Great Price.

Above the tabs: the verse reference, entity chips (people/places/things in this verse, 0–8 of them), and an "Add note" affordance that expands into note/highlight/save controls.

**Tabs currently show a count and hide when empty.** A verse with nothing at all shows "No commentary found for this verse."

### States to design
- **Idle** (pane open, no verse chosen) — currently a near-empty half-screen. Our worst state. It should either invite the first tap or not occupy that space at all.
- **Loading** — data arrives per chapter, tens to hundreds of milliseconds.
- **Rich verse** — all four tabs populated, long commentary.
- **Bare verse** — no commentary, no refs, nothing to say.
- **Phone** — the pane is a bottom sheet over the text; it must not swallow the verse being studied.

### 6c. The Come Follow Me week strip

Sticky above the text when the current chapter belongs to a week. Carries the week title, one chip per chapter (up to ~30), position ("2 of 11"), and prev/next that walk the *reading list* rather than book order. When a person reads on into a chapter the week skips, it stays but says "Not in this week's reading."

It is genuinely useful and currently looks like a toolbar bolted above the page. It should feel like part of the book — a running head, a ribbon, something with a reason to be there.

---

## 7. What we need back

1. **Direction** — 2 or 3 distinct visual directions as static comps (Home + Reader, desktop + phone), enough to judge the idea. We will pick one.
2. **Then, for the chosen direction:**
   - Type system: named faces, weights, full scale with sizes and line-heights for both the scripture column and the interface.
   - Color system: named tokens with hex values, including the active-verse, highlight, and link treatments.
   - Spacing and layout: grid, reading measure, breakpoint behavior at 375 / 768 / 1024 / 1440.
   - Components: verse row, verse number, entity link, study-pane tab, cards, chips, buttons, header.
   - The states listed in §5 and §6 — empty, loading, error, first-visit, and the long-commentary case.
   - Motion: what moves, how far, how long. Assume we honor reduced-motion.
3. **Format:** Figma preferred, with a written rationale. We implement in hand-written CSS, so we need values, not vibes — but we would rather have a strong opinion with a few gaps than a spec with no point of view.

**Please design against our real content.** Everything in this brief exists as real data we can export for you: actual week titles, actual commentary at every length from 40 to 57,000 characters, actual cross-references, actual verse text. Ask and we will send it. Designs that only work against tidy placeholder copy will break the day we implement them.

---

## 8. Reference

- `MISSION.md` — product mission.
- `docs/FLOW_REARCHITECTURE.md` — the user journey and the gaps we found in it.
- `docs/BUILD_PLAN.md` — what shipped and what is coming (notably: General Conference talk citations per verse, which will become a fifth kind of study material).
- Live: the reader at `/library/`.
- Screenshots accompanying this brief: home (desktop + phone), reader idle, reader with study pane empty, reader with all four tabs populated, week strip on phone.
