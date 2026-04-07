#!/usr/bin/env python3
"""
generate_strongs_plain.py
=========================
Generate rich `plain` field text for all unique Strong's Concordance entries
across the corpus, using claude-haiku for cost efficiency.

Output: library/strongs_plain.json  — { "G3056": "...", "H6440": "...", ... }

Supports resuming: already-generated entries are skipped.

Run from repo root:
    python3 lds_pipeline/generate_strongs_plain.py
    python3 lds_pipeline/generate_strongs_plain.py --workers 10  # parallel
    python3 lds_pipeline/generate_strongs_plain.py --limit 100   # test run
"""

import argparse
import json
import os
import sys
import time
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic

REPO        = Path(__file__).resolve().parent.parent
STRONGS_DIR = REPO / "library" / "chapters"
OUTPUT_FILE = REPO / "library" / "strongs_plain.json"

MODEL = "claude-haiku-4-5-20251001"

SYSTEM = """You write scholarly word-study notes for a scripture reader.
Given a Strong's Concordance entry, write 2-4 sentences that explain:
1. The original word's etymology (root verb or noun it comes from, what that root means)
2. How the word was used in the ancient world — cultural, philosophical, or religious weight
3. What it means for a reader encountering it in scripture

Style rules:
- Use bracketed clarifications like [Greek: logos] or [meaning 'to be'] to inject original terms
- Write in plain, direct English — no jargon without explanation
- No AI phrases ("It is worth noting", "delves into", "It's important to understand")
- No bullet points. Flowing prose only.
- 2-4 sentences maximum. Dense and precise.
- If the derivation field is empty or unhelpful, work from the gloss and KJV usage alone."""

PROMPT_TEMPLATE = """Strong's number: {sn}
Original script: {lm}
Transliteration: {xl} ({pr})
Gloss: {gl}
KJV usage: {kj}
Derivation: {dv}

Write the plain-text word study note for this entry."""


def collect_strongs_entries() -> dict:
    """Read all _strongs.json files and collect unique entries by Strong's number."""
    entries = {}
    for path in sorted(STRONGS_DIR.glob("*_strongs.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for verse_list in data.values():
                for e in verse_list:
                    sn = e.get("sn", "").strip()
                    if sn and sn not in entries:
                        entries[sn] = e
        except Exception:
            pass
    return entries


def build_prompt(entry: dict) -> str:
    return PROMPT_TEMPLATE.format(
        sn  = entry.get("sn", ""),
        lm  = entry.get("lm", ""),
        xl  = entry.get("xl", ""),
        pr  = entry.get("pr", ""),
        gl  = (entry.get("gl", "") or "").strip(),
        kj  = (entry.get("kj", "") or "").strip()[:300],
        dv  = (entry.get("dv", "") or "").strip()[:400],
    )


def generate_plain(client: anthropic.Anthropic, sn: str, entry: dict, retries: int = 3) -> str:
    prompt = build_prompt(entry)
    for attempt in range(retries):
        try:
            msg = client.messages.create(
                model    = MODEL,
                max_tokens = 400,
                system   = SYSTEM,
                messages = [{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except anthropic.RateLimitError:
            wait = 2 ** (attempt + 2)
            print(f"  rate limit on {sn}, waiting {wait}s…", flush=True)
            time.sleep(wait)
        except Exception as e:
            print(f"  error on {sn}: {e}", flush=True)
            if attempt == retries - 1:
                return ""
            time.sleep(2)
    return ""


def main():
    parser = argparse.ArgumentParser(description="Generate Strong's plain-text word studies.")
    parser.add_argument("--workers", type=int, default=6, help="Parallel API threads (default 6)")
    parser.add_argument("--limit",   type=int, default=0,  help="Cap total entries (0 = all)")
    parser.add_argument("--only",    type=str, default="", help="Only G or H entries (e.g. G or H)")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Load existing output (for resume)
    existing: dict = {}
    if OUTPUT_FILE.exists():
        try:
            existing = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            print(f"Loaded {len(existing)} existing entries from {OUTPUT_FILE.name}")
        except Exception:
            pass

    # Collect all unique Strong's entries
    all_entries = collect_strongs_entries()
    print(f"Found {len(all_entries)} unique Strong's numbers across corpus")

    # Filter
    todo = {sn: e for sn, e in all_entries.items() if sn not in existing}
    if args.only:
        todo = {sn: e for sn, e in todo.items() if sn.startswith(args.only.upper())}
    if args.limit:
        todo = dict(list(todo.items())[:args.limit])

    print(f"Generating {len(todo)} new entries with {args.workers} workers on {MODEL}…")
    if not todo:
        print("Nothing to do.")
        return

    results = dict(existing)
    done = 0
    errors = 0

    def save():
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_FILE.write_text(
            json.dumps(results, ensure_ascii=False, sort_keys=True, indent=2),
            encoding="utf-8"
        )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(generate_plain, client, sn, entry): sn
                   for sn, entry in todo.items()}
        for fut in as_completed(futures):
            sn = futures[fut]
            try:
                plain = fut.result()
            except Exception as e:
                print(f"  unhandled error {sn}: {e}", flush=True)
                plain = ""

            if plain:
                results[sn] = plain
                done += 1
            else:
                errors += 1

            if (done + errors) % 50 == 0:
                save()
                print(f"  checkpoint: {done} done, {errors} errors, {len(results)} total", flush=True)

    save()
    print(f"\nDone. {done} generated, {errors} errors. Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
