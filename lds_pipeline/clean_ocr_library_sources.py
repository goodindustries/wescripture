#!/usr/bin/env python3
"""
clean_ocr_library_sources.py
============================
Post-process `library/sources/**.html` paragraphs to reduce OCR artifacts.

Goals:
- Keep all paragraphs (do not drop garbled OCR).
- Apply deterministic, "obvious" cleanup automatically.
- If text still looks garbled but changes materially, mark as "guessed" and
  preserve a small original snippet for provenance.

This script edits generated `library/sources/.../*.html` in-place.

Run from repo root:
  python3 lds_pipeline/clean_ocr_library_sources.py --groups times_and_seasons millennial_star
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "library"
TOC = LIB / "source_toc.json"


_HIGH_NON_ASCII = re.compile(r"[^\x00-\x7F]")
_OCR_GARBAGE_RE = re.compile(r"[§©®†‡¶°½¼¾×÷]{2,}|(?:[^\x00-\x7F].*?){5,}")


def non_ascii_ratio(s: str) -> float:
    if not s:
        return 0.0
    return len(_HIGH_NON_ASCII.findall(s)) / max(len(s), 1)


def looks_garbled(s: str) -> bool:
    if not s:
        return False
    if non_ascii_ratio(s) > 0.08:
        return True
    if _OCR_GARBAGE_RE.search(s):
        return True
    return False


def clean_text_obvious(s: str) -> str:
    """Safe deterministic OCR cleanup (no semantic guessing)."""
    t = (s or "").replace("\r", "\n")
    # Common ligatures / OCR punctuation.
    t = (
        t.replace("ﬁ", "fi")
        .replace("ﬂ", "fl")
        .replace("ﬀ", "ff")
        .replace("ﬃ", "ffi")
        .replace("ﬄ", "ffl")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u2014", "-")
        .replace("\u2013", "-")
    )
    # Replacement char from broken decoding.
    t = t.replace("\ufffd", " ")
    t = t.replace("\u00ad\n", "")
    t = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", t)
    # Join soft line wraps (common in OCR text dumps)
    t = re.sub(r"(?<!\n)\n(?!\n)", " ", t)
    # Remove decorative rules
    t = re.sub(r"(?m)^[\\-_=]{3,}\\s*$", "", t)
    # Remove obvious OCR garbage runs.
    t = re.sub(r"[§©®†‡¶°½¼¾×÷]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


_P_RE = re.compile(
    r'(<p[^>]*\bclass="[^"]*\bsource-para\b[^"]*"[^>]*>)(.*?)(</p>)',
    re.I | re.S,
)


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = html_lib.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def escape_text(s: str) -> str:
    return html_lib.escape(s, quote=False)


@dataclass
class FixStats:
    files: int = 0
    paras_total: int = 0
    paras_garbled: int = 0
    obvious: int = 0
    guessed: int = 0


def iter_doc_hrefs(toc_json: list[dict], *, groups: set[str] | None) -> Iterable[str]:
    for coll in toc_json:
        items = coll.get("items", []) or []
        flat: list[dict] = []
        for it in items:
            if it.get("type") == "group":
                flat.extend(it.get("items", []) or [])
            else:
                flat.append(it)
        for doc in flat:
            href = doc.get("href")
            if not href:
                continue
            if groups:
                # href: sources/<group>/<file>.html
                parts = str(href).split("/")
                if len(parts) < 3:
                    continue
                grp = parts[1]
                if grp not in groups:
                    continue
            yield str(href)


def rewrite_file(path: Path, *, max_guessed_orig: int) -> tuple[bool, FixStats]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    stats = FixStats(files=1)

    def repl(m: re.Match) -> str:
        head, inner, tail = m.group(1), m.group(2), m.group(3)
        stats.paras_total += 1

        text0 = strip_tags(inner)
        if not text0:
            return m.group(0)

        garbled0 = looks_garbled(text0)
        if garbled0:
            stats.paras_garbled += 1

        text1 = clean_text_obvious(text0)
        # If still heavily garbled, apply a deterministic "salvage" pass:
        # strip high non-ASCII noise while keeping the paragraph in the corpus.
        if looks_garbled(text1) and non_ascii_ratio(text1) > 0.12:
            text1 = re.sub(r"[^\x00-\x7F]+", " ", text1)
            text1 = re.sub(r"\s+", " ", text1).strip()
        if text1 == text0:
            return m.group(0)

        # Determine confidence class.
        garbled1 = looks_garbled(text1)
        confidence = "obvious" if (garbled0 and not garbled1) else ("guessed" if garbled0 else "obvious")
        if confidence == "obvious":
            stats.obvious += 1
        else:
            stats.guessed += 1

        # Attach provenance attrs to <p ...>.
        head2 = head
        if 'data-ocr-fix=' not in head2.lower():
            head2 = head2.rstrip(">")
            head2 += f' data-ocr-fix="{confidence}"'
            if confidence == "guessed":
                snippet = text0[:max_guessed_orig].replace('"', "'")
                head2 += f' data-ocr-orig="{html_lib.escape(snippet, quote=True)}"'
            head2 += ">"

        return head2 + escape_text(text1) + tail

    out = _P_RE.sub(repl, raw)
    changed = out != raw
    if changed:
        path.write_text(out, encoding="utf-8")
    return changed, stats


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--groups", nargs="*", default=[], help="Source groups to clean (e.g. times_and_seasons)")
    ap.add_argument("--max-files", type=int, default=0, help="If set, stop after this many files")
    ap.add_argument("--max-guessed-orig", type=int, default=240, help="Max original snippet chars stored for guessed fixes")
    args = ap.parse_args()

    toc = json.loads(TOC.read_text(encoding="utf-8"))
    groups = set(args.groups) if args.groups else None

    totals = FixStats()
    changed_files = 0
    for href in iter_doc_hrefs(toc, groups=groups):
        fp = LIB / href
        if not fp.exists():
            continue
        changed, st = rewrite_file(fp, max_guessed_orig=args.max_guessed_orig)
        totals.files += st.files
        totals.paras_total += st.paras_total
        totals.paras_garbled += st.paras_garbled
        totals.obvious += st.obvious
        totals.guessed += st.guessed
        if changed:
            changed_files += 1
        if args.max_files and totals.files >= args.max_files:
            break

    print(
        json.dumps(
            {
                "files_scanned": totals.files,
                "files_changed": changed_files,
                "paras_total": totals.paras_total,
                "paras_garbled_initial": totals.paras_garbled,
                "fix_obvious": totals.obvious,
                "fix_guessed": totals.guessed,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

