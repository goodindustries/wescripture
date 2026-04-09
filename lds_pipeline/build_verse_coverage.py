#!/usr/bin/env python3
"""
build_verse_coverage.py
=======================
Scan scripture chapters and produce a verse-level done-ness bitmap:

  bit 1 — Donaldson: verse has words, notes, or quotes in library/donaldson/{slug}.json
  bit 2 — Entity links: verse HTML has data-entity / data-place / data-thing or .ent-link
  bit 4 — Verse discovery: verse_discovery.json has a non-empty entry for this ref

Output: library/verse_coverage.json (for verse_coverage.html) + optional --markdown report.

Run from repo root:
    python3 lds_pipeline/build_verse_coverage.py
    python3 lds_pipeline/build_verse_coverage.py --max-chapters 50   # smoke test
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "library"
TOC = LIB / "toc.json"
CH = LIB / "chapters"
DON = LIB / "donaldson"
VD = LIB / "verse_discovery.json"
OUT = LIB / "verse_coverage.json"

BOOK_SLUG_DISPLAY = {
    "doctrine_and_covenants": "D&C",
    "joseph_smith_matthew": "Joseph Smith—Matthew",
    "joseph_smith_history": "Joseph Smith—History",
    "articles_of_faith": "Articles of Faith",
    "song_of_solomon": "Song of Solomon",
    "words_of_mormon": "Words of Mormon",
}

BIT_D = 1
BIT_E = 2
BIT_V = 4
FULL = BIT_D | BIT_E | BIT_V


def slug_to_book_name(slug: str) -> str:
    if slug in BOOK_SLUG_DISPLAY:
        return BOOK_SLUG_DISPLAY[slug]
    return " ".join(p.capitalize() for p in slug.split("_"))


def chapter_ref_prefix(chapter_id: str) -> str | None:
    m = re.match(r"^(.+)_(\d+)$", chapter_id)
    if not m:
        return None
    return f"{slug_to_book_name(m.group(1))} {int(m.group(2))}:"


def verse_nums_from_soup(soup: BeautifulSoup) -> list[int]:
    nums = []
    for div in soup.find_all("div", class_="verse"):
        vid = div.get("id") or ""
        mm = re.match(r"^v(\d+)$", vid)
        if mm:
            nums.append(int(mm.group(1)))
    return sorted(set(nums))


def verse_has_entity_markup(verse_div) -> bool:
    if not verse_div:
        return False
    html = str(verse_div)
    return bool(
        re.search(
            r"data-entity=|data-place=|data-thing=|class=\"[^\"]*\bent-link\b",
            html,
        )
    )


def donaldson_hits_for_verse(dj: dict, v: int) -> bool:
    block = dj.get(str(v))
    if not isinstance(block, dict):
        return False
    if block.get("words"):
        return True
    if block.get("notes"):
        return True
    if block.get("quotes"):
        return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-chapters", type=int, default=0, help="Only process first N chapters (0=all)")
    ap.add_argument("--markdown", type=Path, default=None, help="Write diagnostics/verse_coverage.md")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not TOC.is_file():
        print("ERROR: library/toc.json missing", file=sys.stderr)
        sys.exit(1)

    toc = json.loads(TOC.read_text(encoding="utf-8"))
    chapter_ids = [e["id"] for e in toc if e.get("type") == "chapter" and e.get("id")]
    if args.max_chapters:
        chapter_ids = chapter_ids[: args.max_chapters]

    vd: dict = {}
    if VD.is_file():
        vd = json.loads(VD.read_text(encoding="utf-8"))

    chapters_out: dict = {}
    tot = full = 0
    d_hit = e_hit = v_hit = 0

    for i, cid in enumerate(chapter_ids):
        if not args.quiet and i % 200 == 0:
            print(f"  … {i}/{len(chapter_ids)} {cid}", flush=True)

        hp = chapter_ref_prefix(cid)
        ch_path = CH / f"{cid}.html"
        if not ch_path.is_file():
            continue

        html = ch_path.read_text(encoding="utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")
        vnums = verse_nums_from_soup(soup)
        if not vnums:
            continue
        dj = {}
        dj_path = DON / f"{cid}.json"
        if dj_path.is_file():
            try:
                dj = json.loads(dj_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                dj = {}

        max_v = max(vnums)
        bits = [0] * max_v
        for vn in vnums:
            b = 0
            if donaldson_hits_for_verse(dj, vn):
                b |= BIT_D
                d_hit += 1
            vdiv = soup.find(id=f"v{vn}")
            if verse_has_entity_markup(vdiv):
                b |= BIT_E
                e_hit += 1
            if hp:
                ref = f"{hp}{vn}"
                ent = vd.get(ref)
                if isinstance(ent, list) and len(ent) > 0:
                    b |= BIT_V
                    v_hit += 1
            bits[vn - 1] = b
            tot += 1
            if b == FULL:
                full += 1

        complete = sum(1 for x in bits if x == FULL)
        chapters_out[cid] = {
            "n": max_v,
            "complete": complete,
            "bits": bits,
        }

    pct = round(100.0 * full / tot, 2) if tot else 0.0

    doc = {
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "summary": {
            "chapters_scanned": len(chapters_out),
            "verses": tot,
            "verses_full": full,
            "full_pct": pct,
            "bit_hits": {
                "donaldson": d_hit,
                "entity_links": e_hit,
                "verse_discovery": v_hit,
            },
            "legend": {
                "bits": "bitmask per verse index: 1=Donaldson content, 2=entity markup, 4=verse_discovery row; 7=all",
            },
        },
        "chapters": chapters_out,
    }

    OUT.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {OUT} — {tot} verses, {full} full ({pct}%)", flush=True)

    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Verse coverage ({doc['generated']})",
            "",
            f"- Verses scanned: **{tot}**",
            f"- Verses with Donaldson + entity links + discovery: **{full}** ({pct}%)",
            f"- Bit hits: Donaldson {d_hit}, entity {e_hit}, discovery {v_hit}",
            "",
            "## Lowest completion (top 40)",
            "",
            "| Chapter | Verses | Complete | % |",
            "|---------|--------|----------|---|",
        ]
        rows = []
        for cid, c in chapters_out.items():
            n, comp = c["n"], c["complete"]
            if n <= 0:
                continue
            pct_c = round(100.0 * comp / n, 1)
            rows.append((pct_c, comp, n, cid))
        rows.sort(key=lambda x: (x[0], x[3]))
        for pct_c, comp, n, cid in rows[:40]:
            lines.append(f"| {cid} | {n} | {comp} | {pct_c}% |")
        args.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {args.markdown}", flush=True)


if __name__ == "__main__":
    main()
