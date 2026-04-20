#!/usr/bin/env python3
"""
audit_gloss_coverage.py — cross-check corpus stem frequency against gloss shard
presence and emit a coverage report.

Inputs (read-only):
  - library/chapters/*_words.json   (per-chapter stem frequency via existing words index)
  - library/assets/gloss/en.<letter>.json   (current gloss shards)

Outputs:
  - diagnostics/gloss-coverage.json   (full structured report)
  - stdout summary (top-N missing + headline counts)

Usage:
    python3 scripts/audit_gloss_coverage.py               # default: top 100 missing
    python3 scripts/audit_gloss_coverage.py --top 500     # larger report
    python3 scripts/audit_gloss_coverage.py --min-freq 5  # filter rare stems

Design:
  - Stem frequency = number of (chapter, verse) positions where the stem
    appears, summed across chapters. We use appearances rather than match
    weight because gloss coverage prioritizes reader touch, not semantic
    score.
  - A stem is "covered" when present in the shard file matching its first
    character (lowercased). Missing stems are ordered by frequency descending
    so backfill queues tackle high-leverage terms first (T-0123/T-0124).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAPTERS_DIR = ROOT / "library" / "chapters"
GLOSS_DIR = ROOT / "library" / "assets" / "gloss"
REPORT_PATH = ROOT / "diagnostics" / "gloss-coverage.json"


def iter_chapter_words() -> list[Path]:
    return sorted(CHAPTERS_DIR.glob("*_words.json"))


def stem_shard_letter(stem: str) -> str:
    s = (stem or "").strip().lower()
    if not s:
        return ""
    c = s[0]
    return c if c.isalpha() else "_"


def load_gloss_stems() -> dict[str, set[str]]:
    """Return { shard_letter: {stem, ...} } for stems present in each shard."""
    out: dict[str, set[str]] = {}
    for shard_path in sorted(GLOSS_DIR.glob("en.*.json")):
        letter = shard_path.stem.split(".", 1)[-1]  # e.g. en.a → a
        try:
            data = json.loads(shard_path.read_text())
        except (OSError, json.JSONDecodeError) as err:
            print(f"[warn] cannot read {shard_path.name}: {err}", file=sys.stderr)
            continue
        stems = data.get("stems") or {}
        out[letter] = set(stems.keys())
    return out


def compute_stem_frequency() -> Counter:
    counter: Counter = Counter()
    for path in iter_chapter_words():
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as err:
            print(f"[warn] skip {path.name}: {err}", file=sys.stderr)
            continue
        # { verse_num: { stem: pack } }
        if not isinstance(data, dict):
            continue
        for _vnum, pack in data.items():
            if not isinstance(pack, dict):
                continue
            for stem in pack.keys():
                counter[stem] += 1
    return counter


def build_report(top: int, min_freq: int) -> dict:
    gloss = load_gloss_stems()
    freq = compute_stem_frequency()

    present = 0
    missing_rows: list[dict] = []
    for stem, count in freq.most_common():
        if count < min_freq:
            break
        letter = stem_shard_letter(stem)
        shard = gloss.get(letter, set())
        if stem in shard:
            present += 1
        else:
            missing_rows.append({"stem": stem, "freq": count, "shard": letter})

    report = {
        "chapters_scanned": sum(1 for _ in iter_chapter_words()),
        "unique_stems": len(freq),
        "stems_present": present,
        "stems_missing": len(missing_rows),
        "coverage_pct": round(100 * present / max(1, present + len(missing_rows)), 2),
        "min_freq_filter": min_freq,
        "missing_top": missing_rows[:top],
    }
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100, help="cap on missing rows in report")
    ap.add_argument("--min-freq", type=int, default=3, help="ignore stems with freq < N")
    args = ap.parse_args()

    report = build_report(args.top, args.min_freq)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n")

    print(f"chapters scanned:   {report['chapters_scanned']}")
    print(f"unique stems:       {report['unique_stems']}")
    print(f"present in gloss:   {report['stems_present']}")
    print(f"missing from gloss: {report['stems_missing']}")
    print(f"coverage:           {report['coverage_pct']}%")
    print(f"report written to:  {REPORT_PATH.relative_to(ROOT)}")
    if report["missing_top"]:
        print("top missing (freq):")
        for row in report["missing_top"][:20]:
            print(f"  {row['freq']:>6}  {row['stem']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
