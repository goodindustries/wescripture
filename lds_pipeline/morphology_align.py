#!/usr/bin/env python3
"""
Map English reader stems (from span.w data-st) to OT/NT morphology rows.

Uses MorphGNT files in lds_pipeline/cache/morphology/ and OSHB WLC XML
(Open Scriptures) for Hebrew. Lemma disambiguation uses lemma_hints.json.

Public API:
  load_volume_for_slug(slug) -> str  ('ot'|'nt'|...)
  align_stem(slug, chapter, verse, stem, surface_en, nt_tokens, ot_tokens) -> dict | None
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any
from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "lds_pipeline" / "cache" / "morphology"
HINTS_PATH = REPO / "library" / "assets" / "morphology" / "lemma_hints.json"
TOC_PATH = REPO / "library" / "toc.json"

# morphgnt/sblgnt: 61-Mt … 87-Re
BOOK_TO_NT_FILE: dict[str, str] = {
    "Matthew": "61-Mt-morphgnt.txt",
    "Mark": "62-Mk-morphgnt.txt",
    "Luke": "63-Lk-morphgnt.txt",
    "John": "64-Jn-morphgnt.txt",
    "Acts": "65-Ac-morphgnt.txt",
    "Romans": "66-Ro-morphgnt.txt",
    "1 Corinthians": "67-1Co-morphgnt.txt",
    "2 Corinthians": "68-2Co-morphgnt.txt",
    "Galatians": "69-Ga-morphgnt.txt",
    "Ephesians": "70-Eph-morphgnt.txt",
    "Philippians": "71-Php-morphgnt.txt",
    "Colossians": "72-Col-morphgnt.txt",
    "1 Thessalonians": "73-1Th-morphgnt.txt",
    "2 Thessalonians": "74-2Th-morphgnt.txt",
    "1 Timothy": "75-1Ti-morphgnt.txt",
    "2 Timothy": "76-2Ti-morphgnt.txt",
    "Titus": "77-Tit-morphgnt.txt",
    "Philemon": "78-Phm-morphgnt.txt",
    "Hebrews": "79-Heb-morphgnt.txt",
    "James": "80-Jas-morphgnt.txt",
    "1 Peter": "81-1Pe-morphgnt.txt",
    "2 Peter": "82-2Pe-morphgnt.txt",
    "1 John": "83-1Jn-morphgnt.txt",
    "2 John": "84-2Jn-morphgnt.txt",
    "3 John": "85-3Jn-morphgnt.txt",
    "Jude": "86-Jud-morphgnt.txt",
    "Revelation": "87-Re-morphgnt.txt",
}

# OSHB WLC filenames (osis book code)
SLUG_PREFIX_TO_OSIS = {
    "genesis": "Gen",
    "exodus": "Exod",
    "leviticus": "Lev",
    "numbers": "Num",
    "deuteronomy": "Deut",
    "joshua": "Josh",
    "judges": "Judg",
    "ruth": "Ruth",
    "1_samuel": "1Sam",
    "2_samuel": "2Sam",
    "1_kings": "1Kgs",
    "2_kings": "2Kgs",
    "1_chronicles": "1Chr",
    "2_chronicles": "2Chr",
    "ezra": "Ezra",
    "nehemiah": "Neh",
    "esther": "Esth",
    "job": "Job",
    "psalms": "Ps",
    "psalm": "Ps",
    "proverbs": "Prov",
    "ecclesiastes": "Eccl",
    "song_of_solomon": "Song",
    "isaiah": "Isa",
    "jeremiah": "Jer",
    "lamentations": "Lam",
    "ezekiel": "Ezek",
    "daniel": "Dan",
    "hosea": "Hos",
    "joel": "Joel",
    "amos": "Amos",
    "obadiah": "Obad",
    "jonah": "Jonah",
    "micah": "Mic",
    "nahum": "Nah",
    "habakkuk": "Hab",
    "zephaniah": "Zeph",
    "haggai": "Hag",
    "zechariah": "Zech",
    "malachi": "Mal",
}


@lru_cache(maxsize=1)
def _hints() -> dict[str, Any]:
    if not HINTS_PATH.exists():
        return {"nt": {}, "ot": {}}
    return json.loads(HINTS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _toc_volume_by_chapter() -> dict[str, str]:
    """chapter id -> 'Old Testament' | 'New Testament' | ..."""
    data = json.loads(TOC_PATH.read_text(encoding="utf-8"))
    cur = ""
    out: dict[str, str] = {}
    for row in data:
        if row.get("type") == "volume" and row.get("label"):
            cur = row["label"]
        cid = row.get("id")
        if cid and row.get("type") == "chapter":
            out[cid] = cur
    return out


def slug_volume(slug: str) -> str:
    lab = _toc_volume_by_chapter().get(slug, "")
    if lab == "Old Testament":
        return "ot"
    if lab == "New Testament":
        return "nt"
    if lab == "Book of Mormon":
        return "bofm"
    if lab == "Doctrine and Covenants":
        return "dc"
    if lab == "Pearl of Great Price":
        return "pgp"
    return "other"


def book_title_from_slug(slug: str) -> str:
    base = slug.rsplit("_", 1)[0]
    return base.replace("_", " ").title()


def slug_osis_book(slug: str) -> str | None:
    base = slug.rsplit("_", 1)[0].lower()
    return SLUG_PREFIX_TO_OSIS.get(base)


def parse_morphgnt_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    m = re.match(r"^(\d{6})\s+(\S+)\s+(\S+)\s+(.+)$", line)
    if not m:
        return None
    ref, pos, morph, tail = m.groups()
    ch = int(ref[2:4])
    vs = int(ref[4:6])
    parts = tail.split()
    if len(parts) < 2:
        return None
    lemma = parts[-1]
    surface = parts[0].strip(",").strip("⸀")
    return {"ch": ch, "v": vs, "pos": pos, "morph": morph, "surface": surface, "lemma": lemma}


@lru_cache(maxsize=32)
def _load_nt_book_tokens(path: Path) -> dict[tuple[int, int], list[dict[str, Any]]]:
    """(chapter, verse) -> list of token dicts."""
    if not path.exists():
        return {}
    verses: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = parse_morphgnt_line(line)
        if not row:
            continue
        key = (row["ch"], row["v"])
        verses.setdefault(key, []).append(
            {"surface": row["surface"], "lemma": row["lemma"], "morph": row["morph"], "pos": row["pos"]}
        )
    return verses


def nt_tokens_for_verse(book_title: str, chapter: int, verse: int) -> list[dict[str, Any]]:
    fn = BOOK_TO_NT_FILE.get(book_title)
    if not fn:
        return []
    return list(_load_nt_book_tokens(CACHE / fn).get((chapter, verse), []))


# Cache: (osis_path_str, chapter) -> dict[verse, list[tokens]]
_ot_chapter_cache: dict[tuple[str, int], dict[int, list[dict[str, Any]]]] = {}


def _load_ot_chapter_tokens(osis_book: str, chapter: int) -> dict[int, list[dict[str, Any]]]:
    global _ot_chapter_cache
    xml_path = CACHE / f"{osis_book}.xml"
    key = (str(xml_path), chapter)
    if key in _ot_chapter_cache:
        return _ot_chapter_cache[key]
    out: dict[int, list[dict[str, Any]]] = {}
    if not xml_path.exists():
        _ot_chapter_cache[key] = out
        return out
    soup = BeautifulSoup(xml_path.read_text(encoding="utf-8"), "xml")
    chap = soup.find("chapter", attrs={"osisID": f"{osis_book}.{chapter}"})
    if not chap:
        _ot_chapter_cache[key] = out
        return out
    for verse_el in chap.find_all("verse", recursive=False):
        vid = verse_el.get("osisid") or verse_el.get("osisID") or ""
        vm = re.search(r"\.(\d+)$", vid)
        if not vm:
            continue
        vnum = int(vm.group(1))
        toks: list[dict[str, Any]] = []
        for w in verse_el.find_all("w"):
            lemma = w.get("lemma") or ""
            morph = w.get("morph") or ""
            text = w.get_text(strip=True)
            if text:
                toks.append({"surface": text, "lemma": lemma, "morph": morph, "pos": "w"})
        out[vnum] = toks
    _ot_chapter_cache[key] = out
    return out


def ot_tokens_for_verse(slug: str, chapter: int, verse: int) -> list[dict[str, Any]]:
    ob = slug_osis_book(slug)
    if not ob:
        return []
    ch_map = _load_ot_chapter_tokens(ob, chapter)
    return list(ch_map.get(verse, []))


def _norm_lemma(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    return "".join(c for c in s.casefold() if c.isalnum() or c in ("ς",))


def _lemma_match_hint(lemma: str, hints: list[str], lang: str) -> bool:
    lem = _norm_lemma(lemma)
    for h in hints:
        if lang == "grc":
            hn = _norm_lemma(h)
            if hn and (lem == hn or lem.startswith(hn) or hn in lem):
                return True
        else:
            # OT: hints are Strong numbers; lemma attr like "430" or "b/7225"
            nums = re.findall(r"\d+[a-z]?", lemma)
            if h in nums:
                return True
    return False


def align_stem(
    vol: str,
    stem: str,
    surface_en: str,
    nt_tokens: list[dict[str, Any]],
    ot_tokens: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Return a bundle for lex-study generation, or None if no confident hit.
    Always returns English-only shell when vol not ot/nt (caller may still generate study).
    """
    hints_all = _hints()
    stem_l = stem.lower()
    if vol == "nt":
        hints = hints_all.get("nt", {}).get(stem_l) or hints_all.get("nt", {}).get(stem)
        if not hints:
            return None
        for t in nt_tokens:
            lem = t.get("lemma") or ""
            if _lemma_match_hint(lem, hints, "grc"):
                return {
                    "lang": "grc",
                    "lemma": lem,
                    "surface_gr": t.get("surface") or "",
                    "morph": t.get("morph") or "",
                    "confidence": "high",
                    "hint_stem": stem_l,
                }
        return None
    if vol == "ot":
        hints = hints_all.get("ot", {}).get(stem_l) or hints_all.get("ot", {}).get(stem)
        if not hints:
            return None
        for t in ot_tokens:
            lem = t.get("lemma") or ""
            if _lemma_match_hint(lem, hints, "hbo"):
                return {
                    "lang": "hbo",
                    "lemma": lem,
                    "surface_he": t.get("surface") or "",
                    "morph": t.get("morph") or "",
                    "confidence": "high",
                    "hint_stem": stem_l,
                }
        return None
    return None


def english_only_bundle(vol: str, stem: str, surface_en: str) -> dict[str, Any]:
    """Restoration scripture / unknown alignment."""
    return {
        "lang": "eng",
        "lemma": "",
        "surface_gr": "",
        "surface_he": "",
        "morph": "",
        "confidence": "none",
        "hint_stem": stem.lower(),
        "volume": vol,
        "surface_en": surface_en,
    }
