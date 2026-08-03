#!/usr/bin/env python3
"""Reflow chapter markup for the Edition design.

Scripture used to be one bordered <div class="verse"> per verse, which made a
chapter scan like a spreadsheet. The Edition direction sets scripture as
continuous prose in a single measure: verses become inline spans inside a
chapter-level <p>, so the text reads as a page rather than a table.

Each verse also gains data-depth="0|1|2|3" — how much study material it
carries. The verse numeral colours itself from that attribute and a 2px band
in the margin reads the same value, which is how a reader senses where the
depth clusters without the page being speckled with dots.

Depth counts what actually exists:
  - Donaldson notes, quotes and word entries   (library/donaldson/*.json)
  - corpus connections                          (library/verse_discovery.json)
  - cross-references, edges at w>=0.75          (library/chapters/*_graph.json)

Translations are excluded on purpose: every Bible verse has them, so they say
nothing about this verse.

Markup notes, learned the hard way:
  - Verse divs come in two flavours, spans flush against the div and spans on
    their own lines, and 1,174 of them wrap a nested <div class="backlinks">.
    A regex that assumes one shape silently skips the others, so each verse is
    located by scanning for its true matching </div>.
  - Each verse is rewritten IN PLACE. An earlier version spliced from the first
    verse to the last, which deleted every verse the pattern had missed inside
    that range. The integrity check below exists because of that.
  - Nested blocks (backlinks) cannot live inside a span, so they are lifted to
    a hidden container after the paragraph. They are already display:none in
    the reader and nothing expands them, but the data is kept rather than cut.

Usage:
    python3 scripts/reflow_chapters_edition.py [--check] [--limit N]
"""
import json
import re
from html.parser import HTMLParser
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS = ROOT / "library" / "chapters"
DONALDSON = ROOT / "library" / "donaldson"
DISCOVERY = ROOT / "library" / "verse_discovery.json"
TOC = ROOT / "library" / "toc.json"

VERSE_OPEN = re.compile(r'<div class="verse" id="v(\d+)">')
NUM_OPEN = re.compile(r'<span class="verse-num">')
TEXT_OPEN = re.compile(r'<span class="verse-text">')
ALREADY_DONE = '<p class="chapter-text"'

# Verse text wraps nested <span class="w"> word spans, so its extent can only be
# found by counting tags. A non-greedy regex ending at "</span>" stops at the
# first nested word instead and silently truncates the verse — which is exactly
# what happened before the integrity check below was strict enough to catch it.


def match_span(html, open_end):
    """Index of the '<' of the </span> closing the span opened before open_end."""
    depth = 1
    i = open_end
    while i < len(html):
        nxt_open = html.find("<span", i)
        nxt_close = html.find("</span>", i)
        if nxt_close == -1:
            return -1
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 5
        else:
            depth -= 1
            if depth == 0:
                return nxt_close
            i = nxt_close + 7
    return -1


def read_span(html, pattern, start=0):
    """(inner_html, span_start, span_end) for the first span matching pattern."""
    match = pattern.search(html, start)
    if not match:
        return None
    close = match_span(html, match.end())
    if close == -1:
        return None
    return html[match.end():close], match.start(), close + len("</span>")


def depth_bucket(count):
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    if count <= 3:
        return "2"
    return "3"


def find_close(html, start):
    """Index just past the </div> that closes the tag opened before `start`."""
    i, depth = start, 1
    while depth and i < len(html):
        nxt_open = html.find("<div", i)
        nxt_close = html.find("</div>", i)
        if nxt_close == -1:
            return -1
        if nxt_open != -1 and nxt_open < nxt_close:
            depth += 1
            i = nxt_open + 4
        else:
            depth -= 1
            i = nxt_close + 6
    return i if depth == 0 else -1


class _VerseTextReader(HTMLParser):
    """Visible text of each verse element, nesting-aware.

    Reads the whole verse rather than just the verse-text span, because the
    point of the check is that the words a reader sees are unchanged — and in
    35 verses some of those words sit outside verse-text in the source.
    Backlinks subtrees are skipped: they are display:none in both layouts and
    the reflow relocates them by design.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.depth = 0
        self.skip = 0
        self.buf = []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "").split()
        if self.depth:
            self.depth += 1
            if self.skip or "backlinks" in classes:
                self.skip += 1
        elif "verse" in classes:
            self.depth = 1
            self.skip = 0
            self.buf = []

    def handle_endtag(self, tag):
        if self.depth:
            if self.skip:
                self.skip -= 1
            self.depth -= 1
            if self.depth == 0:
                self.out.append(re.sub(r"\s+", " ", "".join(self.buf)).strip())

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.buf.append(data)


def verse_texts(html):
    reader = _VerseTextReader()
    reader.feed(html)
    return reader.out


def chapter_labels():
    items = json.loads(TOC.read_text())
    book = None
    out = {}
    for item in items:
        if item.get("type") == "book":
            book = item["label"]
        elif item.get("type") == "chapter" and book:
            out[item["id"]] = f"{book} {item['label']}"
    return out


def build_depth_index(labels):
    counts = defaultdict(lambda: defaultdict(int))

    for path in DONALDSON.glob("*.json"):
        for verse, entry in json.loads(path.read_text()).items():
            n = (
                len(entry.get("notes") or [])
                + len(entry.get("quotes") or [])
                + len(entry.get("words") or [])
            )
            if n:
                counts[path.stem][verse] += n

    if DISCOVERY.exists():
        by_label = {label: cid for cid, label in labels.items()}
        for ref, entries in json.loads(DISCOVERY.read_text()).items():
            if ":" not in ref:
                continue
            chapter_ref, verse = ref.rsplit(":", 1)
            cid = by_label.get(chapter_ref)
            if cid:
                counts[cid][verse] += len(entries)

    for path in CHAPTERS.glob("*_graph.json"):
        cid = path.name[: -len("_graph.json")]
        try:
            graph = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        verse_nodes = {n["id"]: n for n in graph.get("nodes", []) if n.get("t") == "v"}
        for edge in graph.get("edges", []):
            if (edge.get("w") or 0) < 0.75:
                continue
            node = verse_nodes.get(edge.get("s"))
            if node and node.get("n") is not None:
                counts[cid][str(node["n"])] += 1

    return counts


def reflow(html, depths):
    """Returns (new_html, verse_count, depth_tally) or None when there is nothing to do."""
    out = []
    cursor = 0
    verses = 0
    tally = defaultdict(int)
    leftovers = []
    run_open = False

    while True:
        match = VERSE_OPEN.search(html, cursor)
        if not match:
            break
        close = find_close(html, match.end())
        if close == -1:
            break
        body = html[match.end(): close - 6]

        num = read_span(body, NUM_OPEN)
        text = read_span(body, TEXT_OPEN)
        if not (num and text):
            # Unrecognised verse: leave the file alone entirely rather than
            # risk dropping it. The caller's integrity check will flag the file.
            cursor = close
            continue

        # 35 verses in the corpus close verse-text early, leaving part of the
        # sentence loose inside the verse div (Deuteronomy 30:11 among them).
        # Everything in the verse that is not the numeral or a nested block IS
        # the verse, so the span is rebuilt from all of it — otherwise that
        # trailing clause would be filed as an extra and vanish from the page.
        rest = body[: num[1]] + body[num[2]:]
        blocks = []

        def take_blocks(fragment):
            out = []
            i = 0
            while True:
                start = fragment.find("<div", i)
                if start == -1:
                    out.append(fragment[i:])
                    break
                end = find_close(fragment, start + 4)
                if end == -1:
                    out.append(fragment[i:])
                    break
                out.append(fragment[i:start])
                blocks.append(fragment[start:end])
                i = end
            return "".join(out)

        rest = take_blocks(rest)
        text_in_rest = read_span(rest, TEXT_OPEN)
        if text_in_rest:
            inner, span_start, span_end = text_in_rest
            verse_inner = rest[:span_start] + inner + rest[span_end:]
        else:
            verse_inner = rest

        between = html[cursor:match.start()]
        # A run of verses separated only by whitespace becomes one paragraph.
        if run_open and between.strip():
            out.append("</p>")
            run_open = False
        out.append(between)
        if not run_open:
            out.append('<p class="chapter-text">')
            run_open = True

        vid = match.group(1)
        depth = depth_bucket(depths.get(vid, 0))
        tally[depth] += 1
        verses += 1
        # Both classes: "v" is the Edition styling hook; "verse" keeps the
        # existing JS selectors (.verse[id="vN"]) working. The old block layout
        # was written as div.verse, so it stops matching once a verse is a span
        # and the table look falls away on its own.
        out.append(
            f'<span class="verse v" id="v{vid}" data-depth="{depth}" tabindex="0" role="button">'
            # The space between numeral and text is load-bearing: without it
            # copied text and screen readers run them together ("3And the sons").
            f'<span class="verse-num">{num[0]}</span> '
            f'<span class="verse-text">{verse_inner.strip()}</span>'
            f"</span>"
        )

        # Nested blocks (backlinks) cannot live inside a span; park them in a
        # hidden container after the paragraph. Only markup ever lands here —
        # never words the reader is meant to see.
        if blocks:
            leftovers.append(f'<div data-verse="{vid}">{"".join(blocks)}</div>')

        cursor = close

    if not verses:
        return None

    if run_open:
        out.append("</p>")
    out.append(html[cursor:])

    result = "".join(out)
    if leftovers:
        result = result.replace(
            "</div>\n</body>",
            '<div class="chapter-verse-extras" hidden>' + "".join(leftovers) + "</div>\n</div>\n</body>",
            1,
        )
    return result, verses, tally


def main():
    check_only = "--check" in sys.argv
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None

    labels = chapter_labels()
    depth_index = build_depth_index(labels)

    paths = [p for p in sorted(CHAPTERS.glob("*.html")) if not p.name.endswith("_notes.html")]
    if limit:
        paths = paths[:limit]

    changed = done_already = skipped = 0
    failures = []
    tally = defaultdict(int)
    pending = []

    for path in paths:
        html = path.read_text(errors="ignore")
        if ALREADY_DONE in html:
            done_already += 1
            continue
        expected = len(VERSE_OPEN.findall(html))
        if not expected:
            skipped += 1
            continue

        result = reflow(html, depth_index.get(path.stem, {}))
        if result is None:
            failures.append(f"{path.name}: {expected} verses found, none converted")
            continue
        new_html, verses, counts = result

        # Integrity: every verse must survive with its text byte-for-byte
        # intact. Counts alone are not enough — an earlier bug kept the count
        # while truncating each verse at its first nested word span.
        if verses != expected:
            failures.append(f"{path.name}: {expected} verses in, {verses} out")
            continue
        if '<div class="verse"' in new_html:
            failures.append(f"{path.name}: verse divs remain")
            continue
        # Whitespace-insensitive: the source is inconsistent about the gap
        # between the numeral and the text (some files have none, which copies
        # as "1THEN"), and the reflow normalises it to one space. Comparing the
        # visible characters still catches the failure that matters — text
        # dropped or truncated.
        before = [re.sub(r"\s+", "", t) for t in verse_texts(html)]
        after = [re.sub(r"\s+", "", t) for t in verse_texts(new_html)]
        if before != after:
            diff = next((i for i, (x, y) in enumerate(zip(before, after)) if x != y), None)
            detail = f"first change at verse index {diff}" if diff is not None else f"{len(before)} -> {len(after)} verses"
            failures.append(f"{path.name}: verse text changed ({detail})")
            continue

        for k, v in counts.items():
            tally[k] += v
        changed += 1
        pending.append((path, new_html))

    if failures:
        print(f"REFUSING TO WRITE — {len(failures)} file(s) failed the integrity check:")
        for line in failures[:20]:
            print("  " + line)
        return 2

    if not check_only:
        for path, new_html in pending:
            path.write_text(new_html)

    print(f"chapters reflowed: {changed}")
    print(f"already reflowed: {done_already}, no verses: {skipped}")
    print("verse depth spread: " + ", ".join(f"{k}={tally[k]}" for k in sorted(tally)))
    return 1 if (check_only and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
