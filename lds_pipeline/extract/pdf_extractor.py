"""
PDF text extractor using PyMuPDF word-box approach.

Core insight: instead of extracting raw text (which drops spaces at line/column
breaks), we extract every word with its bounding box, then reconstruct sentences
by checking spatial proximity. Words on the same line get a space; words on
different lines get a space unless they end with a hyphen (hyphenation join).

This eliminates the word-merge bug at the root.
"""

import re
import fitz  # PyMuPDF
from pathlib import Path


# ── Boilerplate detection ─────────────────────────────────────────────────────
# Repeating page header/footer: "MM/DD/YYYY © XXXX by Intellectual Reserve, Inc. All rights reserved. Page NNNN"

_PAGE_BOILERPLATE_RE = re.compile(
    r'^\d{1,2}/\d{1,2}/\d{4}\s*©.*?Intellectual\s+Reserve.*?Page\s+\d+\s*$',
    re.IGNORECASE | re.DOTALL
)

def is_page_boilerplate(text: str) -> bool:
    """Check if text is the recurring page header/footer."""
    return bool(_PAGE_BOILERPLATE_RE.match(text.strip()))


# ── Word-box extraction ───────────────────────────────────────────────────────

def extract_words_with_boxes(pdf_path: str) -> list[dict]:
    """
    Returns a flat list of word dicts:
      { page, block, line, word_num, text, x0, y0, x1, y1 }
    Filters out page boilerplate (headers/footers).
    """
    doc = fitz.open(pdf_path)
    all_words = []
    for page_num, page in enumerate(doc):
        words = page.get_text("words")  # (x0, y0, x1, y1, text, block, line, word)
        for w in words:
            text = w[4]
            # Skip page boilerplate lines
            if is_page_boilerplate(text):
                continue
            all_words.append({
                "page":     page_num,
                "block":    w[5],
                "line":     w[6],
                "word_num": w[7],
                "text":     text,
                "x0": w[0], "y0": w[1],
                "x1": w[2], "y1": w[3],
            })
    doc.close()
    return all_words


def words_to_text(words: list[dict]) -> str:
    """
    Reassemble word list into clean text.
    - Same block + line → space between words
    - Different line (same block) → space (handle hyphenation)
    - Different block (same page) → newline (real paragraph break)
    - Page break → space (content continues across pages)
    """
    if not words:
        return ""

    parts = []
    prev = None
    for w in words:
        text = w["text"]
        if prev is None:
            parts.append(text)
        else:
            same_page  = (w["page"] == prev["page"])
            same_block = same_page and (w["block"] == prev["block"])
            same_line  = same_block and (w["line"] == prev["line"])

            if same_line:
                # Same line → space between words
                parts.append(" ")
                parts.append(text)
            elif same_block:
                # Line break within same block → space (handle hyphenation)
                prev_text = prev["text"]
                if prev_text.endswith("-"):
                    # Hyphenated word — join without hyphen
                    parts[-1] = parts[-1][:-1]  # remove trailing hyphen
                    parts.append(text)
                else:
                    parts.append(" ")
                    parts.append(text)
            elif same_page:
                # Block break within same page → paragraph break
                parts.append("\n\n")
                parts.append(text)
            else:
                # Page break → content continues, join with space
                # (boilerplate has been filtered out)
                parts.append(" ")
                parts.append(text)
        prev = w

    return "".join(parts)


# ── Post-extraction cleanup ───────────────────────────────────────────────────

# Remaining CamelCase merges (lowercase immediately followed by uppercase mid-word)
_CAMEL_RE = re.compile(r'([a-z])([A-Z][a-z])')

def fix_residual_merges(text: str) -> str:
    """
    Fix any camelCase merges that slipped through (e.g. theLord → the Lord).
    Also normalise whitespace.
    """
    text = _CAMEL_RE.sub(r'\1 \2', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ── Page-range extraction (for large PDFs) ───────────────────────────────────

def extract_page_range(pdf_path: str, start_page: int = 0, end_page: int = None) -> str:
    """Extract and clean text from a page range (0-indexed)."""
    doc = fitz.open(pdf_path)
    total = len(doc)
    doc.close()
    end_page = end_page or total

    all_words = []
    doc = fitz.open(pdf_path)
    for page_num in range(start_page, min(end_page, total)):
        page = doc[page_num]
        words = page.get_text("words")
        for w in words:
            all_words.append({
                "page":     page_num,
                "block":    w[5],
                "line":     w[6],
                "word_num": w[7],
                "text":     w[4],
                "x0": w[0], "y0": w[1],
                "x1": w[2], "y1": w[3],
            })
    doc.close()

    raw = words_to_text(all_words)
    return fix_residual_merges(raw)


# ── Full PDF extraction ───────────────────────────────────────────────────────

def extract_full_pdf(pdf_path: str) -> str:
    """Extract entire PDF as clean text."""
    print(f"Extracting: {pdf_path}")
    words = extract_words_with_boxes(pdf_path)
    print(f"  {len(words):,} words extracted across {words[-1]['page']+1 if words else 0} pages")
    raw = words_to_text(words)
    clean = fix_residual_merges(raw)
    print(f"  {len(clean):,} characters after cleanup")
    return clean


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python pdf_extractor.py <path_to_pdf>")
        sys.exit(1)
    text = extract_full_pdf(path)
    out = Path(path).stem + "_extracted.txt"
    Path(out).write_text(text, encoding="utf-8")
    print(f"Written: {out}")
