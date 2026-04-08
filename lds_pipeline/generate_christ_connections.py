#!/usr/bin/env python3
"""
generate_christ_connections.py
==============================
Generate a `christ_connection` field for every entity in the registry:
scripture figures, places, and things.

The field is 2-3 sentences explaining how this person/place/thing points to
Christ — typologically, covenantally, prophetically, or doctrinally.
Style: scholarly but plain. No AI filler. Dense and precise.

Outputs directly into the entity JSON files (adds/overwrites christ_connection).

Run from repo root:
    python3 lds_pipeline/generate_christ_connections.py
    python3 lds_pipeline/generate_christ_connections.py --only people
    python3 lds_pipeline/generate_christ_connections.py --workers 2 --limit 20
"""

import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO       = Path(__file__).resolve().parent.parent
ENTITIES   = REPO / "library" / "entities"
OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3:1.7b"

SYSTEM = (
    "You write precise theological notes for a scripture study library. "
    "Given an entity (person, place, or object) from scripture, write 2-3 sentences "
    "explaining how this entity points to, typifies, prophesies of, or connects to "
    "Jesus Christ — whether through covenant, type, prophecy, ordinance, doctrine, "
    "or the arc of sacred history. "
    "Style: scholarly, direct, densely cross-referential. "
    "Use scripture references in the form [Book Chapter:Verse]. "
    "No AI filler, no 'certainly', no bullet points. "
    "Output ONLY the connection text — no labels, no preamble, no thinking tags."
)

PROMPT_PERSON = """\
Entity type: Scripture figure
Name: {name}
Group: {group}
Description: {desc}

How does this person point to or connect with Jesus Christ?\
"""

PROMPT_PLACE = """\
Entity type: Place
Name: {name}
Description: {desc}

How does this place point to or connect with Jesus Christ?\
"""

PROMPT_THING = """\
Entity type: Scriptural object / artifact
Name: {name}
Description: {desc}

How does this object point to or connect with Jesus Christ?\
"""


def ollama_generate(model: str, prompt: str, retries: int = 3) -> str:
    payload = json.dumps({
        "model":  model,
        "prompt": f"/no_think\n\n{SYSTEM}\n\n{prompt}",
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 250},
        "think": False,
    }).encode()

    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                OLLAMA_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read())
                text = result.get("response", "").strip()
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
                return text
        except urllib.error.URLError as e:
            if attempt == retries - 1:
                print(f"  URLError: {e}", flush=True)
                return ""
            time.sleep(2)
        except Exception as e:
            if attempt == retries - 1:
                print(f"  error: {e}", flush=True)
                return ""
            time.sleep(1)
    return ""


def process_entity(model: str, entity: dict, etype: str) -> str:
    name = entity.get("name", "")
    desc = entity.get("desc", entity.get("description", ""))
    if not name:
        return ""
    if etype == "person":
        prompt = PROMPT_PERSON.format(
            name=name, group=entity.get("group", "scripture"), desc=desc)
    elif etype == "place":
        prompt = PROMPT_PLACE.format(name=name, desc=desc)
    else:
        prompt = PROMPT_THING.format(name=name, desc=desc)
    return ollama_generate(model, prompt)


def run_file(path: Path, etype: str, model: str, workers: int, limit: int, force: bool):
    data = json.loads(path.read_text(encoding="utf-8"))
    is_list = isinstance(data, list)
    entities = data if is_list else list(data.values())

    todo = [e for e in entities if force or not e.get("christ_connection")]
    if limit:
        todo = todo[:limit]

    print(f"{path.name}: {len(entities)} total, {len(todo)} to generate", flush=True)
    if not todo:
        return

    done = errors = 0
    start = time.time()
    id_map = {e.get("id", e.get("name", "")): e for e in entities}

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(process_entity, model, e, etype): e
            for e in todo
        }
        for fut in futures:
            entity = futures[fut]
            eid = entity.get("id", entity.get("name", "?"))
            try:
                text = fut.result()
            except Exception as ex:
                print(f"  {eid}: unhandled {ex}", flush=True)
                text = ""

            if text:
                entity["christ_connection"] = text
                done += 1
                print(f"  ✓ {entity.get('name', eid)}", flush=True)
            else:
                errors += 1
                print(f"  ✗ {entity.get('name', eid)}", flush=True)

    # Write back
    out = data if is_list else {eid: id_map[eid] for eid in id_map}
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    elapsed = time.time() - start
    print(f"  → {done} done, {errors} errors in {elapsed:.0f}s → {path.name}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",   default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--limit",   type=int, default=0, help="Cap per file (0=all)")
    parser.add_argument("--only",    default="", help="people | places | things | scripture_people")
    parser.add_argument("--force",   action="store_true", help="Overwrite existing connections")
    args = parser.parse_args()

    # Verify Ollama
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=3)
    except Exception:
        print("ERROR: Ollama not reachable at localhost:11434", file=sys.stderr)
        sys.exit(1)

    targets = {
        "scripture_people": ("scripture_people.json", "person"),
        "people":  ("people.json",  "person"),
        "places":  ("places.json",  "place"),
        "things":  ("things.json",  "thing"),
    }

    # Default: scripture figures + places + things (skip the 1660-entry people.json unless specified)
    if args.only:
        run_keys = [args.only] if args.only in targets else []
    else:
        run_keys = ["scripture_people", "places", "things"]

    for key in run_keys:
        fname, etype = targets[key]
        path = ENTITIES / fname
        if not path.exists():
            print(f"  skip {fname} (not found)", flush=True)
            continue
        run_file(path, etype, args.model, args.workers, args.limit, args.force)

    print("\nDone.", flush=True)


if __name__ == "__main__":
    main()
