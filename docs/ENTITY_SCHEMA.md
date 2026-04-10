# Entity registry JSON contract

People, places, things, and topics live under `library/entities/` as JSON arrays (except indexes). The reader uses `id` for chips and profiles.

## Required (all types)

| Field | Type | Notes |
|-------|------|--------|
| `id` | string | Stable id: `person:…`, `place:…`, `thing:…`, `topic:…` |
| `name` | string | Display title |

## Strongly recommended

| Field | Type | Notes |
|-------|------|--------|
| `variants` | string[] | Lowercase lookup keys (also in `*_index.json`) |
| `christ_connection` | string | Scripture-centered Christ typology (reader surfaces this) |
| `scripture_refs` or `related_scriptures` | array | Verse labels or `{label, …}`; used for “Scripture” blocks in profiles |
| `excerpts` | array | `{text, …}` from corpus; prefer `source_doc_id` + para when available |

## Optional

| Field | Type | Notes |
|-------|------|--------|
| `desc` | string | Short scripture-focused description |
| `born`, `died` | string | Historical persons |
| `lat`, `lon` | number | Places (map link) |
| `wikipedia_thumbnail` | string | URL to **stored** image only (no live Wikipedia dependency in UI) |
| `related_people`, `related_places`, `related_things`, `related_topics` | string[] | Other entity ids |
| `doc_ids` | string[] | LDS corpus document ids (modern figures) |

## Validation

Run from repo root:

```bash
python3 lds_pipeline/validate_entities.py
python3 lds_pipeline/validate_entities.py --strict
```

`--strict` treats missing `christ_connection` or empty scripture ref lists as errors for indexed entities.
