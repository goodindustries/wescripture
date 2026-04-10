#!/usr/bin/env python3
"""
add_para_ids_to_sources.py
==========================
Post-process generated source HTML pages to ensure:
  - paragraphs are marked as <p class="source-para" id="pN">
  - source_toc.json paragraph counts reflect actual <p.source-para> count

This is an ingestion-layer durability pass for deep linking.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "library"
TOC = LIB / "source_toc.json"
SCRIPTURE_TOC = LIB / "toc.json"


BOOK_SLUG_DISPLAY = {
    "doctrine_and_covenants": "D&C",
    "joseph_smith_matthew": "Joseph Smith—Matthew",
    "joseph_smith_history": "Joseph Smith—History",
    "articles_of_faith": "Articles of Faith",
    "song_of_solomon": "Song of Solomon",
    "words_of_mormon": "Words of Mormon",
}


def load_book_name_to_slug() -> dict[str, str]:
    if not SCRIPTURE_TOC.is_file():
        return {}
    toc = json.loads(SCRIPTURE_TOC.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for e in toc:
        if e.get("type") != "chapter":
            continue
        cid = e.get("id") or ""
        m = re.match(r"^(.+)_\d+$", cid)
        if not m:
            continue
        slug = m.group(1)
        name = BOOK_SLUG_DISPLAY.get(slug) or " ".join(p.capitalize() for p in slug.split("_"))
        out[name.lower()] = slug
    # extra aliases
    out["dc"] = "doctrine_and_covenants"
    out["d&c"] = "doctrine_and_covenants"
    out["jsh"] = "joseph_smith_history"
    out["js—h"] = "joseph_smith_history"
    out["js-h"] = "joseph_smith_history"
    return out


REF_RE = re.compile(
    r"\b(?:(JST)\s+)?"
    r"((?:[1-3]\s+)?[A-Z][A-Za-z—\-]*(?:\s+[A-Z][A-Za-z—\-]*)*)"
    r"\.?\s+(\d+)\s*:\s*(\d+)"
    r"(?:\s*[–\-]\s*(\d+))?",
    re.UNICODE,
)


def collect_docs(node, out: list[dict]) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("href"), str) and node.get("href", "").endswith(".html"):
            out.append(node)
        for v in node.values():
            collect_docs(v, out)
    elif isinstance(node, list):
        for x in node:
            collect_docs(x, out)


def normalize_para_text(s: str) -> str:
    # Ingestion-layer hard-wrap cleanup inside a paragraph:
    # - collapse single newlines to spaces
    # - preserve double newlines (handled at paragraph splitting time upstream)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in s.split("\n") if ln.strip()]
    avg = (sum(len(ln) for ln in lines) / len(lines)) if lines else 0
    looks_like_poetry = len(lines) >= 4 and avg and avg < 55
    if looks_like_poetry:
        # Keep intentional line breaks as <br> in HTML.
        out = s.strip()
        out = out.replace("\r\n", "\n").replace("\r", "\n")
        out = re.sub(r"\n{3,}", "\n\n", out)
        out = out.replace("\n\n", "<br/><br/>")
        out = out.replace("\n", "<br/>")
        return out
    s = re.sub(r"\n(?!\n)", " ", s)
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def linkify_refs_html(text: str, book_map: dict[str, str]) -> str:
    def repl(m: re.Match) -> str:
        _is_jst = bool(m.group(1))
        book = (m.group(2) or "").strip()
        ch = int(m.group(3))
        v1 = int(m.group(4))
        slug = book_map.get(book.lower())
        if not slug:
            return m.group(0)
        href = f"chapters/{slug}_{ch}.html#v{v1}"
        label = m.group(0)
        return f'<a class="ref-link" href="{href}">{label}</a>'

    # Avoid double-wrapping existing anchors
    if "<a" in text.lower():
        return text
    return REF_RE.sub(repl, text)


def process_html(path: Path, normalize: bool, book_map: dict[str, str]) -> int:
    html = path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    paras = soup.select("p.source-para")
    if not paras:
        # Fallback: promote paragraphs inside source docs
        for p in soup.select("article.source-doc p"):
            cls = p.get("class") or []
            if "source-para" not in cls:
                p["class"] = list(dict.fromkeys(cls + ["source-para"]))
        paras = soup.select("p.source-para")

    for i, p in enumerate(paras, start=1):
        if normalize:
            # Normalize within the HTML contents while keeping markup minimal
            txt = p.get_text(separator="\n", strip=False)
            norm = normalize_para_text(txt)
            norm = linkify_refs_html(norm, book_map)
            p.clear()
            frag = BeautifulSoup(norm, "html.parser")
            for child in list(frag.contents):
                p.append(child)
        if not p.get("id"):
            p["id"] = f"p{i}"

    path.write_text(str(soup), encoding="utf-8")
    return len(paras)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--normalize", action="store_true", help="Normalize hard wraps inside <p.source-para>")
    ap.add_argument("--max-files", type=int, default=0, help="Process only first N docs (0=all)")
    args = ap.parse_args()

    tree = json.loads(TOC.read_text(encoding="utf-8"))
    book_map = load_book_name_to_slug()
    docs: list[dict] = []
    collect_docs(tree, docs)
    if args.max_files:
        docs = docs[: args.max_files]

    touched = 0
    for d in docs:
        href = d.get("href")
        if not href:
            continue
        p = LIB / href
        if not p.is_file():
            continue
        n = process_html(p, normalize=args.normalize, book_map=book_map)
        if d.get("paragraphs") != n:
            d["paragraphs"] = n
        touched += 1

    TOC.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Processed {touched} source docs; updated {TOC}")


if __name__ == "__main__":
    main()

