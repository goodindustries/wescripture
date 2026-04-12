#!/usr/bin/env python3
"""
Build library/chapters/{slug}_lexstudies.json — pre-generated morphology-backed
word-study paragraphs for graph keyword stems (same selection cap as reader).

Uses lemma alignment from morphology_align.py. Text generation:
  --ollama   call local Ollama (LEX_STUDIES_MODEL, default gemma4:e2b)
  (default)  deterministic fallback paragraph from facts + matches

Run from repo root:
  python3 lds_pipeline/fetch_morphology_sources.py
  python3 lds_pipeline/build_lex_studies.py --chapters john_3 genesis_1 1_nephi_1
  python3 lds_pipeline/build_lex_studies.py --all   # slow; many chapters
"""

from __future__ import annotations

import argparse
import hashlib
import os
import importlib.util
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
CHAPTERS = REPO / "library" / "chapters"
DONALDSON = REPO / "library" / "donaldson"
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DEFAULT_MODEL = "gemma4:e2b"
OLLAMA_TIMEOUT_S = 120
PROMPT_VERSION = "lex-v1"

# Mirror library/index.html GRAPH_KW_STEM_STOPS (subset + build_word_index STOPS merged at runtime)
def _load_stops() -> set[str]:
    spec = importlib.util.spec_from_file_location("bw", REPO / "lds_pipeline" / "build_word_index.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    raw = getattr(mod, "STOPS", set())
    if isinstance(raw, dict):
        return set(raw.keys())
    return set(raw)


STOPS = _load_stops()
GRAPH_STOPS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "of", "to", "for", "with", "by", "from", "at", "as",
    "is", "was", "are", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "it", "its", "he", "him", "his", "she", "her", "they", "them", "their", "we", "us", "our", "you", "your",
    "i", "me", "my", "not", "no", "so", "if", "that", "this", "these", "those", "which", "who", "whom", "what",
    "when", "where", "why", "how", "all", "any", "some", "such", "than", "then", "there", "thus", "unto", "into",
    "shall", "should", "will", "would", "may", "might", "must", "can", "could",
    "ye", "thee", "thou", "thy", "thine", "hath", "doth", "saith", "also", "even", "only", "very",
}
MIN_SCORE = 0.12

sys.path.insert(0, str(REPO / "lds_pipeline"))
import morphology_align as morph  # noqa: E402

DEFINITION_SYSTEM = (
    "You write compact original-language word studies for Latter-day Saint readers. "
    "When given facts (English surface form, verse wording, optional Hebrew/Greek lemma and gloss, "
    "and short corpus excerpts), trace the key term to the underlying language when facts provide it; "
    "identify the lemma and its root sense, explain literal sense and semantic range briefly, then show "
    "how it functions in this scriptural context and what covenantal or spiritual weight it carries. "
    "Keep ONE clear paragraph (no bullet lists). Focus on details that deepen understanding. "
    "If facts say there is no public lemma alignment for this English token, do NOT invent Greek or Hebrew; "
    "write an English discourse study grounded in the verse and excerpts only, and say plainly that "
    "original-language alignment is unavailable for this volume. "
    "Do not cite Strong's numbers. No filler."
)


def _slug_chapter_num(slug: str) -> int:
    return int(slug.rsplit("_", 1)[-1])


def _is_junk_keyword(title: str) -> bool:
    t = (title or "").strip().lower()
    if not t or len(t) < 2:
        return True
    bad = ("footnote", "chapter", "verse", "summary", "q&a", "greek", "hebrew", "transliteration")
    return any(b in t for b in bad)


def _graph_stem_in_verse(entry: dict[str, Any], verse_text: str) -> bool:
    vt = (verse_text or "").lower()
    for f in entry.get("forms") or []:
        s = (f or "").strip()
        if not s:
            continue
        if " " in s:
            if s.lower().replace("  ", " ") in vt.replace("  ", " "):
                return True
        else:
            if re.search(rf"\b{re.escape(s.lower())}\b", vt):
                return True
    return False


def _normalize_kw(s: str) -> str:
    return re.sub(r"[^a-z0-9\u0590-\u05ff\u0370-\u03ff\u1f00-\u1fff]+", "", (s or "").lower())[:40]


def _dona_headwords_for_verse(slug: str, vnum: int) -> set[str]:
    path = DONALDSON / f"{slug}.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    block = data.get(str(vnum)) or {}
    seen: set[str] = set()
    for w in block.get("words") or []:
        lab = (w.get("word") or "").strip()
        if lab and not _is_junk_keyword(lab):
            seen.add(_normalize_kw(lab))
    return seen


def _pick_display_form(entry: dict[str, Any], stem: str, verse_text: str) -> str:
    vt = (verse_text or "").lower()
    best = ""
    for f in entry.get("forms") or []:
        s = (f or "").strip()
        if not s or s.lower() not in vt:
            continue
        if len(s) > len(best):
            best = s
    if best:
        return best[:1].upper() + best[1:].lower() if len(best) > 1 else best.upper()
    return stem[:1].upper() + stem[1:] if stem else ""


def merge_graph_stems(
    verse_text: str,
    verse_word_data: dict[str, Any],
    dona_norm: set[str],
) -> list[tuple[str, dict[str, Any], str]]:
    """Return up to 2 (stem, entry, display_label) graph keyword rows."""
    cand: list[tuple[str, dict[str, Any], float, str]] = []
    for stem, entry in (verse_word_data or {}).items():
        if not stem or stem in GRAPH_STOPS or stem.lower() in STOPS:
            continue
        if float(entry.get("score") or 0) < MIN_SCORE:
            continue
        if not _graph_stem_in_verse(entry, verse_text):
            continue
        lab = _pick_display_form(entry, stem, verse_text)
        if not lab or _is_junk_keyword(lab):
            continue
        nk = _normalize_kw(lab)
        if nk in dona_norm:
            continue
        cand.append((stem, entry, float(entry.get("score") or 0), lab))
    cand.sort(key=lambda x: -x[2])
    out: list[tuple[str, dict[str, Any], str]] = []
    seen: set[str] = set()
    for stem, entry, _sc, lab in cand:
        nk = _normalize_kw(lab)
        if nk in seen:
            continue
        seen.add(nk)
        out.append((stem, entry, lab))
        if len(out) >= 2:
            break
    return out


def _surface_for_stem(html: str, vnum: int, stem: str) -> str:
    """First .w span text for stem in verse."""
    soup = BeautifulSoup(html, "html.parser")
    v = soup.find("div", class_="verse", id=f"v{vnum}")
    if not v:
        return stem
    vt = v.find("span", class_="verse-text")
    if not vt:
        return stem
    for sp in vt.find_all("span", class_="w"):
        if sp.get("data-st") == stem:
            t = sp.get_text(strip=True)
            return t if t else stem
    return stem


def _verse_plain_text(html: str, vnum: int) -> str:
    soup = BeautifulSoup(html, "html.parser")
    v = soup.find("div", class_="verse", id=f"v{vnum}")
    if not v:
        return ""
    vt = v.find("span", class_="verse-text")
    if not vt:
        return ""
    t = vt.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", t).strip()


def _top_matches(entry: dict[str, Any], n: int = 2) -> list[str]:
    ms = entry.get("matches") or []
    lines = []
    for m in ms[:n]:
        src = (m.get("s") or "").replace("_", " ").title()
        x = re.sub(r"\s+", " ", (m.get("x") or "")).strip()
        if len(x) > 220:
            x = x[:217] + "…"
        if src and x:
            lines.append(f"{src}: {x}")
    return lines


def _cache_key(slug: str, v: int, stem: str, bundle: dict[str, Any]) -> str:
    h = hashlib.sha256(
        json.dumps(
            {"slug": slug, "v": v, "stem": stem, "b": bundle, "pv": PROMPT_VERSION},
            sort_keys=True,
        ).encode()
    ).hexdigest()[:20]
    return h


def _ollama_generate(model: str, user_prompt: str) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": f"{DEFINITION_SYSTEM}\n\n{user_prompt}",
            "stream": False,
            "options": {"temperature": 0.35, "num_predict": 380},
        }
    ).encode()
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT_S) as resp:
                result = json.loads(resp.read())
            text = (result.get("response") or "").strip()
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
            return text
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(1.5)
    return ""


def _fallback_study(
    verse_text: str,
    surface_en: str,
    stem: str,
    bundle: dict[str, Any],
    match_lines: list[str],
    vol: str,
) -> str:
    snip = re.sub(r"\s+", " ", verse_text)[:200].strip()
    ml = " ".join(match_lines)[:400]
    if bundle.get("confidence") == "high" and bundle.get("lang") == "grc":
        gr = bundle.get("surface_gr") or ""
        lem = bundle.get("lemma") or ""
        return (
            f"In this line, “{surface_en}” sits over Greek {lem} (surface form “{gr}”), the wording behind "
            f"our English in the Greek New Testament tradition used for alignment. Read in context — “{snip}…” — "
            f"the term carries its usual semantic range while doing specific work in the sentence’s argument. "
            f"{ml if ml else 'Corpus parallels in this app’s index underline how early readers heard the same lemma in similar settings.'}"
        )
    if bundle.get("confidence") == "high" and bundle.get("lang") == "hbo":
        he = bundle.get("surface_he") or ""
        lem = bundle.get("lemma") or ""
        return (
            f"Here “{surface_en}” aligns to Hebrew wording tagged in the Westminster Leningrad tradition "
            f"(lemma field {lem}; surface “{he}”). In “{snip}…”, the construction colors how creation, covenant, "
            f"or command is being declared. "
            f"{ml if ml else 'Let the verse’s own parallelism and repetition guide how narrow or broad the sense should be taken.'}"
        )
    if vol in ("bofm", "dc", "pgp", "other"):
        return (
            f"No public verse-token Hebrew/Greek alignment is shipped for this Restoration-era volume; the study stays in English. "
            f"“{surface_en}” in “{snip}…” should be read for what it does rhetorically and theologically in its immediate sentence. "
            f"{ml if ml else 'Use the semantic channel (tap the underlined word) for curated parallels across standard works and commentary.'}"
        )
    return (
        f"No confident open-licensed morphology row matched this English keyword (stem “{stem}”) in this verse; "
        f"the study stays in English. “{surface_en}” in “{snip}…” should be read in context for what it contributes to the line. "
        f"{ml if ml else 'Use the semantic channel (tap the underlined word) for curated parallels across standard works and commentary.'}"
    )


def _user_prompt(verse_text: str, surface_en: str, stem: str, bundle: dict[str, Any], match_lines: list[str]) -> str:
    lines = [
        "Facts (do not invent beyond these):",
        f"- Verse (English): {verse_text}",
        f"- Keyword stem: {stem}; surface in verse: {surface_en}",
        f"- Volume class: {bundle.get('volume', '')}",
        f"- Alignment confidence: {bundle.get('confidence', '')}",
        f"- Language tag: {bundle.get('lang', '')}",
        f"- Lemma (if any): {bundle.get('lemma', '')}",
        f"- Greek surface (if any): {bundle.get('surface_gr', '')}",
        f"- Hebrew surface (if any): {bundle.get('surface_he', '')}",
        f"- Morph code (if any): {bundle.get('morph', '')}",
        "- Top corpus excerpts:",
    ]
    lines.extend(f"  • {m}" for m in match_lines[:3])
    lines.append("Write the study paragraph now.")
    return "\n".join(lines)


def build_chapter(slug: str, use_ollama: bool, model: str, force: bool) -> dict[str, Any]:
    html_path = CHAPTERS / f"{slug}.html"
    words_path = CHAPTERS / f"{slug}_words.json"
    out_path = CHAPTERS / f"{slug}_lexstudies.json"
    if not html_path.exists() or not words_path.exists():
        print(f"  skip {slug}: missing html or words", flush=True)
        return {}
    prev_hash = {}
    if out_path.exists() and not force:
        try:
            prev = json.loads(out_path.read_text(encoding="utf-8"))
            prev_hash = prev.get("_meta", {}).get("keys", {})
        except json.JSONDecodeError:
            prev_hash = {}

    html = html_path.read_text(encoding="utf-8")
    words_root = json.loads(words_path.read_text(encoding="utf-8"))
    if isinstance(words_root, dict) and "_m" in words_root and "v" in words_root:
        catalog = words_root["_m"]
        verses_raw = words_root["v"]
        words_data: dict[str, Any] = {}
        for vk, vdata in verses_raw.items():
            inner: dict[str, Any] = {}
            for stem, entry in (vdata or {}).items():
                e = dict(entry)
                if "matches" not in e and e.get("m"):
                    e["matches"] = [catalog[i] for i in e["m"] if i < len(catalog)]
                inner[stem] = e
            words_data[vk] = inner
    else:
        words_data = words_root

    vol = morph.slug_volume(slug)
    ch_num = _slug_chapter_num(slug)
    book_title = morph.book_title_from_slug(slug)

    out: dict[str, Any] = {}

    for vkey, verse_word_data in words_data.items():
        if not str(vkey).isdigit():
            continue
        vnum = int(vkey)
        verse_text = _verse_plain_text(html, vnum)
        dona_norm = _dona_headwords_for_verse(slug, vnum)
        picks = merge_graph_stems(verse_text, verse_word_data, dona_norm)
        if not picks:
            continue
        nt_toks = morph.nt_tokens_for_verse(book_title, ch_num, vnum) if vol == "nt" else []
        ot_toks = morph.ot_tokens_for_verse(slug, ch_num, vnum) if vol == "ot" else []
        verse_out: dict[str, Any] = {}
        for stem, entry, _lab in picks:
            surface = _surface_for_stem(html, vnum, stem)
            bundle = morph.align_stem(vol, stem, surface, nt_toks, ot_toks)
            if bundle is None:
                bundle = morph.english_only_bundle(vol, stem, surface)
            match_lines = _top_matches(entry, 2)
            _cache_key(slug, vnum, stem, bundle)  # reserved for future incremental rebuilds
            up = _user_prompt(verse_text, surface, stem, bundle, match_lines)
            if use_ollama:
                study = _ollama_generate(model, up) or _fallback_study(verse_text, surface, stem, bundle, match_lines, vol)
            else:
                study = _fallback_study(verse_text, surface, stem, bundle, match_lines, vol)
            verse_out[stem] = {
                "lang": bundle.get("lang"),
                "lemma": bundle.get("lemma") or "",
                "surface_gr": bundle.get("surface_gr") or "",
                "surface_he": bundle.get("surface_he") or "",
                "morph": bundle.get("morph") or "",
                "confidence": bundle.get("confidence") or "none",
                "study": study,
                "matches": match_lines,
            }
        if verse_out:
            out[str(vnum)] = verse_out

    if not out:
        print(f"  {slug}: no graph stems to export", flush=True)
        return {}
    payload = {
        "_meta": {
            "slug": slug,
            "prompt_version": PROMPT_VERSION,
            "ollama": bool(use_ollama),
        },
        **out,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"  wrote {out_path.name} ({len(out)} verses)", flush=True)
    return payload


def _all_chapter_slugs() -> list[str]:
    return sorted(p.stem for p in CHAPTERS.glob("*.html") if p.stem != "index")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chapters", nargs="*", help="Chapter ids e.g. john_3 genesis_1")
    ap.add_argument("--all", action="store_true", help="Every chapter with html+words")
    ap.add_argument("--ollama", action="store_true")
    ap.add_argument("--model", default=os.environ.get("LEX_STUDIES_MODEL", DEFAULT_MODEL))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.all:
        slugs = _all_chapter_slugs()
    elif args.chapters:
        slugs = args.chapters
    else:
        slugs = ["john_3", "genesis_1", "1_nephi_1"]

    model = args.model or DEFAULT_MODEL
    for slug in slugs:
        build_chapter(slug, args.ollama, model, args.force)


if __name__ == "__main__":
    main()
