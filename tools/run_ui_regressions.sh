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

TESTS=(
  test-verse-discovery-panel.js
  test-library-commentary-links.js
  test-library-buttons.js
  test-toc-volume-covers.js
  test-library-mobile-channel.js
  test-search-quality.js
  test-title-inline-nav.js
  test-nav-fixed.js
  test-library-sources.js
  test-home-iframe-inline-nav.js
  test-title-page-dashboard.js
)

for t in "${TESTS[@]}"; do
  echo "==> node $t"
  node "$t"
done
echo "All UI regression scripts passed."
