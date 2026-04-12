#!/usr/bin/env bash
# Smoke-check static JSON endpoints after deploy (fails if HTML is returned).
# Usage:
#   ./tools/smoke_static_deploy.sh https://wescripture.netlify.app
#   BASE_URL=http://localhost ./tools/smoke_static_deploy.sh

set -euo pipefail
BASE="${1:-${BASE_URL:-https://wescripture.netlify.app}}"
BASE="${BASE%/}"

echo "Smoke: $BASE"

check_json() {
  local path="$1"
  local url="${BASE}${path}"
  local ct
  ct="$(curl -fsSIL -o /dev/null -w '%{content_type}' "$url" || true)"
  if [[ "$ct" != *"application/json"* ]]; then
    echo "FAIL $url (content-type: $ct)" >&2
    exit 1
  fi
  curl -fsS "$url" | python3 -c 'import json,sys; json.load(sys.stdin)' >/dev/null
  echo "OK   $path"
}

check_json "/toc.json"
check_json "/source_toc.json"
check_json "/verse_discovery.json"
check_json "/entities/people_index.json"
check_json "/chapters/mark_1_graph.json"

echo "All checks passed."
echo ""
echo "Manual UI spot-check (same origin as BASE):"
echo "  1) Reader: ${BASE}/"
echo "  2) Redirects: ${BASE}/home.html → ${BASE}/index.html; ${BASE}/library/home.html → ${BASE}/library/index.html (302 on Netlify)"
echo "  3) Cold verse: open Mark 1, verse 1; confirm panels load without console errors."
