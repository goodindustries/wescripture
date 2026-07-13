#!/usr/bin/env bash
# Run Puppeteer UI regression scripts against a local static server (repo root → /library/index.html).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PORT="${HTTP_PORT:-4173}"
BASE="http://127.0.0.1:${PORT}"

HTTP_PID=""
if curl -sf -o /dev/null "$BASE/library/index.html" 2>/dev/null; then
  echo "Using existing HTTP server at $BASE"
else
  python3 -m http.server "$PORT" &
  HTTP_PID=$!
fi

cleanup() {
  if [ -n "$HTTP_PID" ]; then kill "$HTTP_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

if [ -z "$HTTP_PID" ]; then
  for _ in $(seq 1 5); do
    if curl -sf -o /dev/null "$BASE/library/index.html"; then break; fi
    sleep 0.2
  done
else
  for _ in $(seq 1 60); do
    if curl -sf -o /dev/null "$BASE/library/index.html"; then break; fi
    sleep 0.25
  done
fi
if ! curl -sf -o /dev/null "$BASE/library/index.html"; then
  echo "Server not reachable at $BASE (start with: python3 -m http.server $PORT from repo root)" >&2
  exit 1
fi

# CI-blocking acceptance test (must pass for deploy)
SMOKE_TEST=(
  test-smoke-four-legs.js
)

# Optional full suite (runs only with RUN_FULL_SUITE=1, e.g., local testing)
FULL_SUITE=(
  test-verse-discovery-panel.js
  test-library-commentary-links.js
  test-library-mobile-channel.js
  test-search-quality.js
  test-study-panel-heading.js
  test-nav-fixed.js
  test-title-page-dashboard.js
  test-scripture-traversal.js
  test-corpus-book-covers.js
  test-lex-studies-panel.js
)

TESTS=("${SMOKE_TEST[@]}")
if [ "${RUN_FULL_SUITE:-0}" = "1" ]; then
  TESTS+=("${FULL_SUITE[@]}")
fi

for t in "${TESTS[@]}"; do
  echo "==> node $t"
  node "$t"
done
echo "All UI regression scripts passed."
