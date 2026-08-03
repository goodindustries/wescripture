#!/usr/bin/env bash
# Reader verification suite. Each test drives the real reader in a headless
# browser and asserts what the person using it would see, not what the code
# claims. Every one of these was written red-first against a real defect.
#
#   ./tests/reader/run.sh [base-url]
#
# Needs a static server on the repo root, e.g.:
#   python3 -m http.server 8091
set -uo pipefail

BASE="${1:-http://localhost:8091}"
HERE="$(cd "$(dirname "$0")" && pwd)"
export WS_BASE="$BASE"
export WS_SHOTS="${WS_SHOTS:-$(mktemp -d)}"

if ! curl -fsS -o /dev/null "$BASE/library/"; then
  echo "No server at $BASE — start one with: python3 -m http.server 8091"
  exit 2
fi

echo "base: $BASE"
echo "screenshots: $WS_SHOTS"
echo

failed=0
for test in vp-tabs cfm-phase2 cfm-mobile donaldson-bleed translations polish; do
  printf '%-20s ' "$test"
  if out=$(node "$HERE/$test.js" 2>&1); then
    echo "PASS"
  else
    echo "FAIL"
    echo "$out" | sed 's/^/    /'
    failed=1
  fi
done

echo
[ "$failed" -eq 0 ] && echo "all reader tests passed" || echo "reader tests FAILED"
exit "$failed"
