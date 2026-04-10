# Agent backlog — entity registry

Use with `lds_pipeline/task_ledger.py` when filing follow-on work.

## Template (queue)

```
Title: [entities] Backfill scripture_refs + christ_connection — {book or domain}
Type: queue
Notes: Run validate_entities.py --strict on touched files; prefer excerpts with source_doc_id.
```

## Suggested tasks

1. **Gospels sweep** — ensure named people/places in Matthew–John have `scripture_refs` covering major pericopes.
2. **Index variants** — add missing `judaea`-style spelling variants to `places_index.json` as discovered.
3. **Excerpts** — attach 2–5 corpus excerpts per high-traffic entity from `source_links.json` anchors.
