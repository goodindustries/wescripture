#!/usr/bin/env python3
"""Validate library/entities/*.json against docs/ENTITY_SCHEMA.md."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENT = REPO / "library" / "entities"

FILES = [
    ("people.json", "person:"),
    ("places.json", "place:"),
    ("things.json", "thing:"),
    ("topics.json", "topic:"),
]


def load_index(name: str) -> dict:
    p = ENT / name
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true", help="Strict mode (defaults to people only)")
    ap.add_argument("--strict-places", action="store_true", help="Strict for places too")
    ap.add_argument("--strict-things", action="store_true", help="Strict for things too")
    ap.add_argument("--strict-topics", action="store_true", help="Strict for topics too")
    ap.add_argument("--only", type=str, default="", help="Validate only ids containing this substring (optional)")
    args = ap.parse_args()

    err = 0
    warned = 0
    indexed_ids = {
        "people.json": set(load_index("people_index.json").values()),
        "places.json": set(load_index("places_index.json").values()),
        "things.json": set(load_index("things_index.json").values()),
        "topics.json": set(),  # no index gate by default
    }
    for fname, prefix in FILES:
        path = ENT / fname
        if not path.is_file():
            print(f"SKIP missing {path}", file=sys.stderr)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            print(f"ERROR {fname}: root must be array", file=sys.stderr)
            err += 1
            continue
        for i, row in enumerate(data):
            if not isinstance(row, dict):
                print(f"ERROR {fname}[{i}]: not an object", file=sys.stderr)
                err += 1
                continue
            eid = row.get("id", "")
            if args.only and (not isinstance(eid, str) or args.only not in eid):
                continue
            if not eid or not isinstance(eid, str):
                print(f"ERROR {fname}[{i}]: missing id", file=sys.stderr)
                err += 1
            elif prefix and not eid.startswith(prefix):
                print(f"WARN {fname} id={eid!r}: expected prefix {prefix}", file=sys.stderr)
                warned += 1
            if not row.get("name"):
                print(f"ERROR {fname} id={eid}: missing name", file=sys.stderr)
                err += 1
            refs = row.get("scripture_refs") or row.get("related_scriptures")
            strict_here = bool(args.strict)
            if fname == "places.json" and not args.strict_places:
                strict_here = False
            if fname == "things.json" and not args.strict_things:
                strict_here = False
            if fname == "topics.json" and not args.strict_topics:
                strict_here = False
            if strict_here and indexed_ids.get(fname):
                strict_here = eid in indexed_ids[fname]
            if strict_here:
                if not row.get("christ_connection"):
                    print(f"STRICT {fname} id={eid}: missing christ_connection", file=sys.stderr)
                    err += 1
                if not refs:
                    print(f"STRICT {fname} id={eid}: missing scripture_refs/related_scriptures", file=sys.stderr)
                    err += 1

    # Index / record consistency (lightweight)
    for idx_name in ("people_index.json", "places_index.json", "things_index.json"):
        ix = load_index(idx_name)
        if not ix:
            continue
        # spot-check: values should match id prefixes
        bad = sum(1 for v in ix.values() if not isinstance(v, str) or ":" not in v)
        if bad:
            print(f"WARN {idx_name}: {bad} malformed index values", file=sys.stderr)
            warned += 1

    print(
        f"validate_entities: {'FAIL' if err else 'OK'} "
        f"({err} errors, {warned} warnings; strict={args.strict})"
    )
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
