#!/usr/bin/env python3
"""
annotate_entity_spans.py
========================
Pre-annotate chapter HTML files with entity data-attributes so that
person/place/thing chips appear in the discovery panel without requiring
all entity index data to be loaded client-side before the first verse click.

Two-step annotation (mirrors annotateChapterEntities() in index.html):
  1. Add data-entity / data-place / data-thing to existing span.w nodes
     whose text content exactly matches a known entity variant (case-insensitive).
  2. Wrap multi-word entity name matches in plain text nodes with
     <span class="ent-link" data-entity|place|thing="id">.
     (Only multi-word keys ≥ 5 chars; single-word variants are handled in step 1.)

Rules (same as JS _buildAnnotationKeys):
  - People  : only scripture figures (those with a 'group' field in people.json)
  - Places  : all entries, key length ≥ 4
  - Things  : all entries, key length ≥ 5

Run from repo root:
    python3 lds_pipeline/annotate_entity_spans.py [--books genesis exodus] [--dry-run] [--force]
"""

import argparse
import json
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

REPO     = Path(__file__).parent.parent
CHAPTERS = REPO / 'library' / 'chapters'
ENTITIES = REPO / 'library' / 'entities'


# ---------------------------------------------------------------------------
# Index loading
# ---------------------------------------------------------------------------

def load_indexes():
    """Return (person_idx, person_keys, place_idx, place_keys, thing_idx, thing_keys)."""
    people = json.loads((ENTITIES / 'people.json').read_text('utf-8'))
    scripture_ids = {p['id'] for p in people if p.get('group')}

    raw_person = json.loads((ENTITIES / 'people_index.json').read_text('utf-8'))
    person_idx = {k: v for k, v in raw_person.items() if v in scripture_ids}

    raw_place = json.loads((ENTITIES / 'places_index.json').read_text('utf-8'))
    place_idx = {k: v for k, v in raw_place.items() if len(k) >= 4}

    raw_thing = json.loads((ENTITIES / 'things_index.json').read_text('utf-8'))
    thing_idx = {k: v for k, v in raw_thing.items() if len(k) >= 5}

    # Longest-first for greedy matching
    person_keys = sorted(person_idx, key=len, reverse=True)
    place_keys  = sorted(place_idx,  key=len, reverse=True)
    thing_keys  = sorted(thing_idx,  key=len, reverse=True)

    return person_idx, person_keys, place_idx, place_keys, thing_idx, thing_keys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _word_boundary(text, start, length):
    """True if the match at [start:start+length] sits on word boundaries."""
    before = text[start - 1] if start > 0 else ' '
    after  = text[start + length] if start + length < len(text) else ' '
    return not (before.isalpha() or after.isalpha())


def _collect_text_nodes(element):
    """Return NavigableString nodes that are NOT inside span.w or span.ent-link."""
    result = []
    for node in element.descendants:
        if not isinstance(node, NavigableString):
            continue
        parent = node.parent
        if not isinstance(parent, Tag):
            continue
        cls = parent.get('class') or []
        if 'w' in cls or 'ent-link' in cls:
            continue
        result.append(node)
    return result


def _split_text_node(text_node, idx, length, attr_name, entity_id):
    """Replace a NavigableString with before + <span class="ent-link"> + after."""
    text   = str(text_node)
    before = text[:idx]
    match  = text[idx:idx + length]
    after  = text[idx + length:]

    parent   = text_node.parent
    contents = list(parent.contents)
    pos      = contents.index(text_node)
    text_node.extract()

    # Insert in reverse order so final order is before → span → after
    if after:
        parent.insert(pos, NavigableString(after))

    span_tag = Tag(name='span')
    span_tag['class'] = 'ent-link'
    span_tag[f'data-{attr_name}'] = entity_id
    span_tag.string = match
    parent.insert(pos, span_tag)

    if before:
        parent.insert(pos, NavigableString(before))


# ---------------------------------------------------------------------------
# Per-verse annotation
# ---------------------------------------------------------------------------

def _annotate_w_span(span, person_idx, person_keys, place_idx, place_keys,
                     thing_idx, thing_keys):
    """Step 1: add data-entity/place/thing to a single span.w if it matches."""
    if span.get('data-entity') or span.get('data-place') or span.get('data-thing'):
        return
    t = span.get_text().lower()
    for key in person_keys:
        if key == t:
            span['data-entity'] = person_idx[key]
            return
    for key in place_keys:
        if key == t:
            span['data-place'] = place_idx[key]
            return
    for key in thing_keys:
        if key == t:
            span['data-thing'] = thing_idx[key]
            return


def _annotate_text_nodes(verse_text, keys, lookup, attr_name):
    """Step 2: wrap first multi-word match in each eligible text node."""
    for text_node in _collect_text_nodes(verse_text):
        text  = str(text_node)
        lower = text.lower()
        found = None
        for key in keys:
            if len(key) < 5:
                continue  # single-word variants handled in step 1
            idx = lower.find(key)
            if idx == -1:
                continue
            if not _word_boundary(lower, idx, len(key)):
                continue
            found = (idx, key, lookup[key])
            break
        if not found:
            continue
        idx, key, entity_id = found
        _split_text_node(text_node, idx, len(key), attr_name, entity_id)


# ---------------------------------------------------------------------------
# Chapter processing
# ---------------------------------------------------------------------------

def process_chapter(path, person_idx, person_keys, place_idx, place_keys,
                    thing_idx, thing_keys, dry_run):
    html_text = path.read_text('utf-8')
    soup      = BeautifulSoup(html_text, 'html.parser')

    verse_count = annotated = 0
    for verse_div in soup.select('div.verse[id]'):
        verse_id = verse_div.get('id', '')
        if not (verse_id.startswith('v') and verse_id[1:].isdigit()):
            continue
        verse_text = verse_div.find('span', class_='verse-text')
        if not verse_text:
            continue
        verse_count += 1

        # Step 1: annotate span.w nodes
        for span in verse_text.find_all('span', class_='w'):
            _annotate_w_span(span, person_idx, person_keys,
                             place_idx, place_keys, thing_idx, thing_keys)

        # Step 2: wrap multi-word matches in plain text nodes
        _annotate_text_nodes(verse_text, person_keys, person_idx, 'entity')
        _annotate_text_nodes(verse_text, place_keys,  place_idx,  'place')
        _annotate_text_nodes(verse_text, thing_keys,  thing_idx,  'thing')

        # Count annotated spans for reporting
        for span in verse_text.find_all(True):
            if span.get('data-entity') or span.get('data-place') or span.get('data-thing'):
                annotated += 1

    new_html = str(soup)
    changed  = new_html != html_text
    if not dry_run and changed:
        path.write_text(new_html, 'utf-8')

    return {'verses': verse_count, 'annotated': annotated, 'changed': changed}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--books',   nargs='+',
                        help='Limit to these book slugs (e.g. genesis exodus)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Parse and annotate but do not write files')
    parser.add_argument('--force',   action='store_true',
                        help='Re-annotate chapters that are already annotated')
    args = parser.parse_args()

    print('Loading entity indexes…')
    person_idx, person_keys, place_idx, place_keys, thing_idx, thing_keys = load_indexes()
    print(f'  {len(person_idx)} scripture-person variants, '
          f'{len(place_idx)} place variants, '
          f'{len(thing_idx)} thing variants')

    files = sorted(
        f for f in CHAPTERS.glob('*.html')
        if not any(s in f.name for s in ('_notes', '_words', '_graph'))
    )

    if args.books:
        books = [b.lower().replace(' ', '_') for b in args.books]
        files = [f for f in files
                 if any(f.stem.startswith(b) for b in books)]

    if not args.force:
        # Skip chapters that already have entity annotations
        files = [
            f for f in files
            if 'data-entity' not in f.read_text('utf-8', errors='ignore')
            and 'data-place'  not in f.read_text('utf-8', errors='ignore')
            and 'data-thing'  not in f.read_text('utf-8', errors='ignore')
        ]

    print(f'Annotating {len(files)} chapters…' + (' (dry run)' if args.dry_run else ''))

    total_verses = total_annotated = changed_count = errors = 0

    for i, path in enumerate(files):
        try:
            s = process_chapter(
                path,
                person_idx, person_keys,
                place_idx,  place_keys,
                thing_idx,  thing_keys,
                args.dry_run,
            )
            total_verses    += s['verses']
            total_annotated += s['annotated']
            if s['changed']:
                changed_count += 1
        except Exception as e:
            print(f'  ERROR {path.name}: {e}')
            errors += 1

        if (i + 1) % 500 == 0:
            print(f'  … {i + 1}/{len(files)}')

    print(f'\nDone. {changed_count} chapters changed, '
          f'{total_verses} verses scanned, '
          f'{total_annotated} entity spans added.')
    if errors:
        print(f'  Errors: {errors}')


if __name__ == '__main__':
    main()
