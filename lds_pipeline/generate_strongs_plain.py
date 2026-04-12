#!/usr/bin/env python3
"""
generate_strongs_plain.py
=========================
Generate rich `plain` field text for all unique Strong's Concordance entries
across the corpus, using a local Ollama model.

Output: library/strongs_plain.json  — { "G3056": "...", "H6440": "...", ... }

Supports resuming: already-generated entries are skipped.

Run from repo root:
    python3 lds_pipeline/generate_strongs_plain.py
    python3 lds_pipeline/generate_strongs_plain.py --model qwen3.5:9b
    python3 lds_pipeline/generate_strongs_plain.py --workers 4 --limit 100
"""

import argparse
import json
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

REPO        = Path(__file__).resolve().parent.parent
STRONGS_DIR = REPO / "library" / "chapters"
OUTPUT_FILE = REPO / "library" / "strongs_plain.json"

OLLAMA_URL  = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3:1.7b"

SYSTEM = (
    "You write compact original-language word studies for scripture readers ($definition style). "
    "Trace the headword to the underlying Hebrew, Aramaic, or Greek as given; name the original "
    "word or gloss, its root sense and short semantic range, then its literal force. "
    "Explain how that sense would operate in a verse where the English rendering appears, and "
    "what covenantal or spiritual weight the choice of term typically carries. "
    "Optional: one short clause tying a related passage or idiom only if it genuinely clarifies. "
    "Output 2–4 sentences as one or two clear paragraphs—no headings, bullets, or numbered lists. "
    "Never output concordance numbers (no H#### / G####). No 'Strong's' wording. "
    "No AI filler. Output ONLY the study prose—no preamble or tags."
)

PROMPT_TEMPLATE = """\
Lexical entry (reference data only; do not echo catalog numbers in your answer):
Original script: {lm}
Transliteration: {xl} ({pr})
Lexicon gloss: {gl}
Traditional English renderings: {kj}
Morphology / derivation notes: {dv}

Write the plain-text word study."""


def collect_strongs_entries() -> dict:
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


def ollama_generate(model: str, prompt: str, retries: int = 3) -> str:
    payload = json.dumps({
        "model":  model,
        "prompt": f"/no_think\n\n{SYSTEM}\n\n{prompt}",
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 300},
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
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                text = result.get("response", "").strip()
                # Strip any <think>...</think> blocks (qwen3 reasoning mode)
                import re
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


def generate_plain(model: str, sn: str, entry: dict) -> str:
    prompt = PROMPT_TEMPLATE.format(
        lm  = entry.get("lm", ""),
        xl  = entry.get("xl", ""),
        pr  = entry.get("pr", ""),
        gl  = (entry.get("gl", "") or "").strip(),
        kj  = (entry.get("kj", "") or "").strip()[:300],
        dv  = (entry.get("dv", "") or "").strip()[:400],
    )
    return ollama_generate(model, prompt)


def save(results: dict):
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(results, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",   default=DEFAULT_MODEL, help="Ollama model name")
    parser.add_argument("--workers", type=int, default=4,   help="Parallel threads (default 4)")
    parser.add_argument("--limit",   type=int, default=0,   help="Cap total entries (0 = all)")
    parser.add_argument("--only",    default="",            help="Filter: G or H only")
    args = parser.parse_args()

    # Verify Ollama is reachable
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=3)
    except Exception:
        print("ERROR: Ollama not reachable at localhost:11434 — is it running?", file=sys.stderr)
        sys.exit(1)

    # Load existing output for resume
    existing: dict = {}
    if OUTPUT_FILE.exists():
        try:
            existing = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
            print(f"Resuming: {len(existing)} entries already done")
        except Exception:
            pass

    all_entries = collect_strongs_entries()
    print(f"Corpus: {len(all_entries)} unique Strong's numbers")

    todo = {sn: e for sn, e in all_entries.items() if sn not in existing}
    if args.only:
        todo = {sn: e for sn, e in todo.items() if sn.startswith(args.only.upper())}
    if args.limit:
        todo = dict(list(todo.items())[:args.limit])

    print(f"Generating {len(todo)} entries  model={args.model}  workers={args.workers}")
    if not todo:
        print("Nothing to do.")
        return

    results = dict(existing)
    done = errors = 0
    start = time.time()

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(generate_plain, args.model, sn, entry): sn
            for sn, entry in todo.items()
        }
        for fut in as_completed(futures):
            sn = futures[fut]
            try:
                plain = fut.result()
            except Exception as e:
                print(f"  unhandled {sn}: {e}", flush=True)
                plain = ""

            if plain:
                results[sn] = plain
                done += 1
            else:
                errors += 1

            total = done + errors
            if total % 25 == 0:
                save(results)
                elapsed = time.time() - start
                rate = total / elapsed
                remaining = (len(todo) - total) / rate if rate else 0
                print(
                    f"  {total}/{len(todo)} done  "
                    f"{rate:.1f}/s  "
                    f"~{remaining/60:.0f}m remaining",
                    flush=True,
                )

    save(results)
    elapsed = time.time() - start
    print(f"\nDone in {elapsed/60:.1f}m — {done} generated, {errors} errors → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
