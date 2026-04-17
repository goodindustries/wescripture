#!/usr/bin/env bash
# One-line + JSON pretty view of gloss build state (local pipeline).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="${ROOT}/diagnostics/gloss-build-state.json"
if [[ ! -f "$STATE" ]]; then
  echo "No state file yet: $STATE (pipeline not started?)"
  exit 1
fi
python3 - "$STATE" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text(encoding="utf-8"))
st = d.get("status", "?")
done, fail, sk = d.get("done", 0), d.get("failed", 0), d.get("skipped", 0)
wt = d.get("work_total")
idx = d.get("stems_in_index")
print(
    f"{st}  ok={done} fail={fail} skip={sk} queue={wt} index={idx}  "
    f"phase={d.get('phase')}  pid={d.get('pid')}"
)
PY
echo "---"
python3 -m json.tool "$STATE" | head -40
