# Entity registry — next tranche (content)

Prioritize entities that appear in **high-traffic scripture** and in **verse discovery / graph** edges.

## Tranche 1 (suggested)

- **Gospels**: named figures (disciples, Herod, Pilate, Mary Magdalene, etc.) — ensure non-stub profiles.
- **Genesis 1–11**: Adam, Eve, Cain, Abel, Noah — full `christ_connection`, `scripture_refs`, `excerpts`.
- **Book of Mormon anchors**: Nephi, Alma, Mormon, Moroni — cross-link related people/places.

## Validation

- Run [`lds_pipeline/validate_entities.py`](../lds_pipeline/validate_entities.py) with `--strict` while backfilling; `--only <substring>` narrows output but matches any id **containing** that substring, so prefer checking specific rows in the file or running a full pass periodically.
- Keep [`docs/ENTITY_SCHEMA.md`](ENTITY_SCHEMA.md) as the contract.
- After edits: `python3 lds_pipeline/validate_entities.py` (non-strict) for structure; `--strict` remains a **gate** until the indexed backlog is cleared.

## Backlog export

```bash
python3 lds_pipeline/entity_backlog_candidates.py --limit 40
```

Lists indexed people missing `christ_connection` or `scripture_refs` (people file only).
