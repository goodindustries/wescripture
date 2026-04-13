#!/usr/bin/env python3
"""
build_graph.py
==============
Pre-compute per-chapter graph JSON files from correlation cache.

Output: library/chapters/{slug}_graph.json
Format:
  {
    "nodes": [
      {"id": "v1",  "t": "v", "n": 1,   "x": "verse text..."},
      {"id": "p_0", "t": "p", "src": "donaldson", "lb": "label...", "x": "passage text..."}
    ],
    "edges": [
      {"s": "v1", "t": "p_0", "w": 0.41}
    ]
  }

Node types:  v = verse, p = passage
Source keys map to colors in the reader.

Run from repo root:
    python3 lds_pipeline/build_graph.py [--books genesis] [--min-score 0.25]
"""

import argparse
import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

REPO        = Path(__file__).parent.parent
CORR_DIR    = Path(__file__).parent / "cache" / "correlations"
CHAPTERS    = REPO / "library" / "chapters"
LIBRARY     = REPO / "library"
SOURCE_TOC  = LIBRARY / "source_toc.json"

MIN_SCORE   = 0.25
MAX_MATCHES = 12   # top N matches per verse to include (UI shows 5 + "show 5 more")
DEEP_MAX_MATCHES = 16  # pilot chapters (e.g. John) when --deep-books is set

# Truncate passage text for the graph (shown in hover/popover)
MAX_TEXT_LEN = 400

_SOURCE_DOCS = None
_SOURCE_LABELS = None
_SOURCE_PARAS = {}


def book_to_slug_prefix(book: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', book.lower()).strip('_')


def chapter_slug(book: str, chapter: int) -> str:
    return f"{book_to_slug_prefix(book)}_{chapter}"


def truncate(text: str, limit: int = MAX_TEXT_LEN) -> str:
    if not text or len(text) <= limit:
        return text
    cut = text[:limit]
    pos = cut.rfind(' ')
    return (cut[:pos] + '\u2026') if pos > limit // 2 else cut + '\u2026'


def load_source_catalog() -> tuple[dict, dict]:
    global _SOURCE_DOCS, _SOURCE_LABELS
    if _SOURCE_DOCS is not None and _SOURCE_LABELS is not None:
        return _SOURCE_DOCS, _SOURCE_LABELS

    docs = {}
    labels = defaultdict(list)
    if SOURCE_TOC.exists():
        try:
            data = json.loads(SOURCE_TOC.read_text(encoding='utf-8'))
        except Exception:
            data = []
        for collection in data:
            raw_items = collection.get('items', [])
            flat_items = []
            for it in raw_items:
                if it.get('type') == 'group':
                    flat_items.extend(it.get('items', []))
                else:
                    flat_items.append(it)
            for item in flat_items:
                meta = {
                    'id': item['id'],
                    'label': item['label'],
                    'href': item['href'],
                    'collection': collection.get('id', ''),
                    'meta': item.get('meta', ''),
                }
                docs[item['id']] = meta
                labels[item['label']].append(meta)

    _SOURCE_DOCS = docs
    _SOURCE_LABELS = labels
    return docs, labels


def normalize_excerpt(text: str) -> str:
    text = html.unescape(text or '').replace('\u2026', ' ')
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'[^a-z0-9]+', ' ', text.lower())
    return re.sub(r'\s+', ' ', text).strip()


def load_source_paragraphs(doc_id: str) -> list[str]:
    cached = _SOURCE_PARAS.get(doc_id)
    if cached is not None:
        return cached

    docs, _ = load_source_catalog()
    meta = docs.get(doc_id)
    if not meta:
        _SOURCE_PARAS[doc_id] = []
        return []

    path = LIBRARY / meta['href']
    if not path.exists():
        _SOURCE_PARAS[doc_id] = []
        return []

    html_text = path.read_text(encoding='utf-8', errors='replace')
    paragraphs = []
    for raw in re.findall(r'<p[^>]*class="[^"]*source-para[^"]*"[^>]*>(.*?)</p>', html_text, re.S | re.I):
        text = re.sub(r'<[^>]+>', ' ', raw)
        text = re.sub(r'\s+', ' ', html.unescape(text)).strip()
        paragraphs.append(text)
    _SOURCE_PARAS[doc_id] = paragraphs
    return paragraphs


def _label_slug_after_colon(label: str) -> Optional[str]:
    """Text after 'Collection: ' in correlation labels (e.g. millennial_star_1840_1859)."""
    if not label:
        return None
    s = label.strip()
    m = re.match(r"^[^:]+:\s*(.+)$", s)
    if m:
        return m.group(1).strip()
    return None


def _prefix_doc_candidates(src: str, slug: str, docs: dict) -> list[str]:
    """Doc ids whose id tail extends a coarse slug prefix (merged OCR / correlation stems)."""
    slug = (slug or "").strip()
    if not slug:
        return []
    prefix = f"{src}:"
    out: list[str] = []
    for did in docs:
        if not did.startswith(prefix):
            continue
        rest = did[len(prefix) :]
        if rest.startswith(slug):
            out.append(did)
        elif len(rest) < len(slug) and slug.startswith(rest):
            out.append(did)
    return out


def _load_para_texts_truncated(doc_id: str, max_chars: int = 65536) -> list[str]:
    """First paragraphs from start of HTML only — fast path for doc disambiguation."""
    docs, _ = load_source_catalog()
    meta = docs.get(doc_id)
    if not meta:
        return []
    path = LIBRARY / meta['href']
    if not path.exists():
        return []
    html_text = path.read_text(encoding='utf-8', errors='replace')
    if len(html_text) > max_chars:
        html_text = html_text[:max_chars]
    paragraphs: list[str] = []
    for raw in re.findall(r'<p[^>]*class="[^"]*source-para[^"]*"[^>]*>(.*?)</p>', html_text, re.S | re.I):
        text = re.sub(r'<[^>]+>', ' ', raw)
        text = re.sub(r'\s+', ' ', html.unescape(text)).strip()
        paragraphs.append(text)
    return paragraphs


def _excerpt_fit_score(doc_id: str, excerpt: str) -> tuple[int, Optional[int]]:
    """Return (overlap_score, best_para_index_1based) for ranking candidate docs."""
    paragraphs = _load_para_texts_truncated(doc_id)
    if not paragraphs:
        return 0, None
    target = normalize_excerpt(excerpt)
    if not target:
        return 0, None
    target_words = [w for w in target.split() if len(w) > 2][:22]
    if not target_words:
        return 0, None
    best_score = 0
    best_idx: Optional[int] = None
    for idx, para in enumerate(paragraphs, start=1):
        hay = normalize_excerpt(para)
        if not hay:
            continue
        if target[:200] and target[:200] in hay:
            return max(len(target_words), 12), idx
        overlap = sum(1 for w in target_words if w in hay)
        if overlap > best_score:
            best_score = overlap
            best_idx = idx
    return best_score, best_idx


def _pick_best_doc_by_excerpt(candidates: list[str], excerpt: str) -> Optional[str]:
    if not candidates or not (excerpt or "").strip():
        return candidates[0] if len(candidates) == 1 else None
    best_id: Optional[str] = None
    best_s = -1
    for did in candidates:
        s, _ = _excerpt_fit_score(did, excerpt)
        if s > best_s:
            best_s = s
            best_id = did
    if best_s >= 3:
        return best_id
    return None


def resolve_source_doc_id(src: str, label: str, excerpt: Optional[str] = None) -> Optional[str]:
    docs, labels = load_source_catalog()
    exact = labels.get(label, [])
    if len(exact) == 1:
        return exact[0]['id']

    if src == 'journal_of_discourses':
        match = re.search(r'JD Vol\s+(\d+)', label, re.I)
        if match:
            candidate = f"journal_of_discourses:vol_{int(match.group(1)):02d}"
            if candidate in docs:
                return candidate

    if src == 'history_of_church':
        match = re.search(r'Vol\.?\s*(\d+)', label, re.I)
        if match:
            candidate = f"history_of_church:vol{int(match.group(1))}"
            if candidate in docs:
                return candidate

    if src == 'general_conference':
        # Common graph label form: "GC 1974/04 — Elder Howard W. Hunter"
        m = re.match(r"GC\s+(\d{4})/(\d{2})\s*[—\-]\s*(.+)$", (label or "").strip())
        if m:
            year = m.group(1)
            mo = m.group(2)
            speaker = m.group(3).strip().lower()
            session_label = f"{'April' if mo == '04' else 'October'} {year}"
            for meta in docs.values():
                if meta.get("collection") != "general_conference":
                    continue
                meta_str = (meta.get("meta") or "").lower()
                if session_label.lower() in meta_str and speaker and speaker in meta_str:
                    return meta.get("id")
        for candidate in exact:
            if candidate.get('collection') == 'general_conference':
                return candidate.get('id')
        for meta in docs.values():
            if meta.get('collection') == 'general_conference' and meta.get('label') == label:
                return meta.get('id')

    # ── Collection slug → source_toc doc id (periodicals, gutenberg, church_fathers, JSP, pioneer) ──
    slug = _label_slug_after_colon(label or "")
    if slug:
        direct = f"{src}:{slug}"
        if direct in docs:
            return direct
        cands = _prefix_doc_candidates(src, slug, docs)
        if not cands:
            for n in (72, 56, 48, 40, 32):
                if len(slug) > n:
                    cands = _prefix_doc_candidates(src, slug[:n], docs)
                    if cands:
                        break
        # Cap disambiguation work (large periodical corpora share one OCR stem).
        MAX_CANDS = 14
        if len(cands) > MAX_CANDS:
            cands = sorted(cands)[:MAX_CANDS]
        if len(cands) == 1:
            return cands[0]
        if len(cands) > 1 and excerpt:
            picked = _pick_best_doc_by_excerpt(cands, excerpt)
            if picked:
                return picked
            return cands[0]

    return None


def resolve_source_paragraph(doc_id: str, excerpt: str) -> Optional[int]:
    paragraphs = load_source_paragraphs(doc_id)
    if not paragraphs:
        return None

    target = normalize_excerpt(excerpt)
    if not target:
        return None
    target_words = [word for word in target.split() if len(word) > 2][:18]
    if not target_words:
        return None

    best_idx = None
    best_score = 0
    for idx, para in enumerate(paragraphs, start=1):
        hay = normalize_excerpt(para)
        if not hay:
            continue
        if target[:180] and target[:180] in hay:
            return idx
        overlap = sum(1 for word in target_words if word in hay)
        if overlap > best_score:
            best_score = overlap
            best_idx = idx

    return best_idx if best_score >= max(3, min(6, len(target_words) // 2 or 1)) else None


def resolve_source_target(src: str, label: str, excerpt: str) -> Optional[dict]:
    doc_id = resolve_source_doc_id(src, label, excerpt)
    if not doc_id:
        return None
    target: dict = {'d': doc_id}
    para_idx = resolve_source_paragraph(doc_id, excerpt)
    if para_idx is None and excerpt:
        sc, loose = _excerpt_fit_score(doc_id, excerpt)
        if loose is not None and sc >= 2:
            para_idx = loose
    if para_idx is not None:
        target['p'] = para_idx
    return target


def build_chapter_graph(
    book: str,
    chapter: int,
    verse_files: list[Path],
    min_score: float = MIN_SCORE,
    max_matches: int = MAX_MATCHES,
) -> dict:
    """Build graph dict for one chapter from its verse correlation files."""
    nodes = []
    edges = []
    passage_index: dict[str, str] = {}   # (source, label) → node id

    for vf in sorted(verse_files, key=lambda f: int(f.stem.rsplit('_', 1)[-1])):
        try:
            data = json.loads(vf.read_text(encoding='utf-8'))
        except Exception:
            continue

        vnum   = data.get('verse', int(vf.stem.rsplit('_', 1)[-1]))
        vtext  = data.get('text', '')
        vid    = f'v{vnum}'

        nodes.append({
            'id': vid,
            't':  'v',
            'n':  vnum,
            'x':  truncate(vtext, 200),
        })

        matches = sorted(
            data.get('matches', []),
            key=lambda m: m.get('score', 0),
            reverse=True,
        )

        count = 0
        # Keep the “web” broad without letting one shelf dominate.
        per_source_cap = max(2, max_matches // 3)  # e.g. 12 -> 4
        per_source_counts: dict[str, int] = {}
        for m in matches:
            score = m.get('score', 0)
            if score < min_score:
                break
            if count >= max_matches:
                break

            src   = m.get('source', '')
            if src and per_source_counts.get(src, 0) >= per_source_cap:
                continue
            label = m.get('label', src)
            pkey  = f'{src}\x00{label}'

            if pkey not in passage_index:
                pid = f'p_{len(passage_index)}'
                passage_index[pkey] = pid
                node = {
                    'id':  pid,
                    't':   'p',
                    'src': src,
                    'lb':  label,
                    'x':   truncate(m.get('text', ''), MAX_TEXT_LEN),
                }
                if m.get('year') is not None:
                    node['yr'] = m['year']
                if m.get('speaker'):
                    node['sp'] = m['speaker']
                if m.get('collection'):
                    node['coll'] = m['collection']
                target = resolve_source_target(src, label, m.get('text', ''))
                if target:
                    node.update(target)
                nodes.append(node)
            else:
                pid = passage_index[pkey]

            edges.append({'s': vid, 't': pid, 'w': round(score, 3)})
            if src:
                per_source_counts[src] = per_source_counts.get(src, 0) + 1
            count += 1

    return {'nodes': nodes, 'edges': edges}


def enrich_existing_graph(graph: dict) -> tuple[dict, bool]:
    changed = False
    for node in graph.get('nodes', []):
        if node.get('t') != 'p':
            continue
        if node.get('d') and node.get('p'):
            continue
        target = resolve_source_target(node.get('src', ''), node.get('lb', ''), node.get('x', ''))
        if not target:
            continue
        if target.get('d') and node.get('d') != target.get('d'):
            node['d'] = target['d']
            changed = True
        if target.get('p') and node.get('p') != target.get('p'):
            node['p'] = target['p']
            changed = True
    return graph, changed


def slug_matches_books(stem: str, books: Optional[list[str]]) -> bool:
    if not books:
        return True
    lower = stem.lower()
    prefixes = [b.lower().replace(' ', '_') for b in books]
    return any(lower.startswith(prefix) for prefix in prefixes)


def main():
    parser = argparse.ArgumentParser(description='Build per-chapter graph JSON')
    parser.add_argument('--books',     nargs='+', help='process only these book prefixes')
    parser.add_argument('--min-score', type=float, default=MIN_SCORE)
    parser.add_argument(
        '--deep-books',
        nargs='*',
        default=[],
        metavar='BOOK',
        help='Book slugs (e.g. john) get a higher per-verse passage cap from correlations',
    )
    args = parser.parse_args()

    min_score = args.min_score
    deep_slugs = {book_to_slug_prefix(b) for b in (args.deep_books or []) if b}

    # Group correlation files by (book, chapter)
    by_chapter: dict[tuple, list[Path]] = defaultdict(list)
    if CORR_DIR.exists():
        for f in CORR_DIR.iterdir():
            if not f.suffix == '.json':
                continue
            stem = f.stem
            parts = stem.rsplit('_', 2)
            if len(parts) != 3:
                continue
            book, ch_str, ve_str = parts
            try:
                ch = int(ch_str)
                int(ve_str)
            except ValueError:
                continue
            by_chapter[(book, ch)].append(f)

    # Filter by book prefix if requested
    if args.books:
        def matches_filter(book: str) -> bool:
            prefix = book_to_slug_prefix(book)
            return any(prefix.startswith(b.lower()) for b in args.books)
        by_chapter = {k: v for k, v in by_chapter.items() if matches_filter(k[0])}

    if not by_chapter:
        graph_files = sorted(CHAPTERS.glob('*_graph.json'))
        if args.books:
            graph_files = [f for f in graph_files if slug_matches_books(f.stem, args.books)]

        print(f"Enriching existing graphs for {len(graph_files)} chapters...")
        written = 0
        for gf in graph_files:
            try:
                graph = json.loads(gf.read_text(encoding='utf-8'))
            except Exception:
                continue
            graph, changed = enrich_existing_graph(graph)
            if not changed:
                continue
            gf.write_text(
                json.dumps(graph, ensure_ascii=False, separators=(',', ':')),
                encoding='utf-8',
            )
            written += 1
            if written % 50 == 0:
                print(f'  {written} written...', flush=True)

        print(f'\nDone. {written} graph files enriched, {len(graph_files) - written} unchanged.')
        return

    print(f"Building graphs for {len(by_chapter)} chapters...")

    written = 0
    skipped = 0
    for (book, chapter), files in sorted(by_chapter.items()):
        cslug  = chapter_slug(book, chapter)
        outpath = CHAPTERS / f'{cslug}_graph.json'

        max_m = DEEP_MAX_MATCHES if book_to_slug_prefix(book) in deep_slugs else MAX_MATCHES
        graph = build_chapter_graph(book, chapter, files, min_score, max_matches=max_m)

        if not graph['nodes']:
            skipped += 1
            continue

        outpath.write_text(
            json.dumps(graph, ensure_ascii=False, separators=(',', ':')),
            encoding='utf-8',
        )
        written += 1

        if written % 100 == 0:
            print(f'  {written} written...')

    print(f'\nDone. {written} graph files written, {skipped} skipped (no nodes).')


if __name__ == '__main__':
    main()
