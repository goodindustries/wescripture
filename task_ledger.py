#!/usr/bin/env python3
"""
WeScripture task ledger — multi-agent, cross-session, Fibonacci-decomposed.

One file:     task-ledger.jsonl  (append-only, fcntl-locked on write).
One snapshot: ledger-state.json  (rebuilt after every write; agent's entry point).

Event types:
    task_add      {id, title, plan?, phase?, priority?, source?, parent?, points?}
    task_estimate {id, agent, points, rationale?}
    task_split    {id, agent, children:[child_ids], rationale?}
    task_status   {id, agent, status, note?, commit?}
                  status ∈ pending|in_progress|blocked|completed|cancelled
    session_start {agent, goal?}
    session_end   {agent, handoff?, decisions[]}

Fibonacci SWE scale:
    1pt   ~30 min     single file, single concept
    2pt   ~1 h        single file or trivial multi
    3pt   ~2-3 h      multi-file, well-bounded
    5pt   ~half day   cross-system, single concern
    8pt   ~full day   requires design choice
    13pt+ epic, must split before working

Stop rule: split until every leaf is 1pt. `LEDGER_MAX_DEPTH` (default 5) is safety cap.

Commands:
    python3 task_ledger.py                          # brief (default)
    python3 task_ledger.py brief [--plan P]
    python3 task_ledger.py ls [--status S] [--plan P] [--phase P] [--points]
    python3 task_ledger.py tree [<id>] [--points] [--status]
    python3 task_ledger.py add <title> [--plan P] [--phase P] [--priority P]
                                       [--parent ID] [--points N] [--source S] [--id ID]
    python3 task_ledger.py status <id> --agent A --status S [--note N] [--commit C]
    python3 task_ledger.py estimate <id> [--agent A] [--apply] [--points N] [--rationale R]
    python3 task_ledger.py split <id> --agent A [--apply] [--child TITLE]... [--rationale R]
    python3 task_ledger.py decompose <id> --agent A [--max-depth D]
    python3 task_ledger.py session {start|end} --agent A [--goal G] [--handoff H]
                                               [--decision D]...

LLM provider chain (for estimate/split without explicit --points/--child):
    1. Ollama at 127.0.0.1:11434 if reachable (OLLAMA_MODEL env, default llama3.2:3b)
    2. Anthropic API if ANTHROPIC_API_KEY set (ANTHROPIC_MODEL env)
    3. Prints a parseable prompt to stdout, exits 2. Agent fulfills by rerunning
       with --apply + the explicit data.

Agent protocol:
    1. `python3 task_ledger.py`                         # read brief
    2. `session start --agent X --goal "..."`
    3. For [NEEDS-EST] or [NEEDS-SPLIT] markers: `decompose T-XXXX --agent X`
       (may exit 2 with a prompt; fulfill and rerun)
    4. Claim a 1pt leaf via `status T-XXXX --agent X --status in_progress`
    5. Work. `status ... --status completed --commit <sha> --note "..."`
    6. `session end --agent X --handoff "..." --decision "..."`
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import urllib.error
import urllib.request
from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(os.environ.get("LEDGER_DIR", str(Path(__file__).resolve().parent)))
LEDGER = ROOT / "task-ledger.jsonl"
STATE = ROOT / "ledger-state.json"

VALID_STATUS = {"pending", "in_progress", "blocked", "completed", "cancelled"}
TERMINAL_STATUS = {"completed", "cancelled"}

FIB_POINTS: tuple[int, ...] = (1, 2, 3, 5, 8, 13, 21)
MAX_DEPTH = int(os.environ.get("LEDGER_MAX_DEPTH", "5"))
MIN_TITLE_LEN = int(os.environ.get("LEDGER_MIN_TITLE_LEN", "12"))
LEDGER_LLM = os.environ.get("LEDGER_LLM", "auto").lower()  # auto|ollama|anthropic|stdout
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

STUB_SENTINEL = object()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ── io ─────────────────────────────────────────────────────────────────────

def read_events() -> list[dict[str, Any]]:
    if not LEDGER.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _write_line(fh, event: dict[str, Any]) -> dict[str, Any]:
    event = {"ts": now_iso(), **event}
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    if len(line.encode("utf-8")) >= 4000:
        raise SystemExit("event too large; shorten fields")
    fh.write(line + "\n")
    return event


def append_event(event: dict[str, Any]) -> dict[str, Any]:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            written = _write_line(fh, event)
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    write_state(project(read_events()))
    return written


def append_batch(builder: Callable[[list[dict[str, Any]]], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Atomic multi-event append. `builder(current_events)` returns events to write."""
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.seek(0)
            current: list[dict[str, Any]] = []
            for line in fh.read().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    current.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            events = builder(current)
            written: list[dict[str, Any]] = []
            for ev in events:
                written.append(_write_line(fh, ev))
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    write_state(project(read_events()))
    return written


def write_state(state: dict[str, Any]) -> None:
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


# ── helpers ────────────────────────────────────────────────────────────────

def next_task_id(events: list[dict[str, Any]], offset: int = 0) -> str:
    n = 0
    for e in events:
        tid = e.get("id", "")
        if e.get("type") == "task_add" and isinstance(tid, str) and tid.startswith("T-"):
            try:
                n = max(n, int(tid[2:]))
            except ValueError:
                pass
    return f"T-{n + 1 + offset:04d}"


def snap_fib(n: int | float) -> int:
    """Snap an arbitrary number to the nearest Fibonacci point value."""
    n = max(1, int(round(float(n))))
    return min(FIB_POINTS, key=lambda f: (abs(f - n), f < n))


def norm_title(t: str) -> str:
    return " ".join(str(t or "").strip().lower().split())


# ── projection ─────────────────────────────────────────────────────────────

def project(events: list[dict[str, Any]]) -> dict[str, Any]:
    tasks: OrderedDict[str, dict[str, Any]] = OrderedDict()
    sessions: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None

    for e in events:
        t = e.get("type")
        ts = e.get("ts", "")

        if t == "task_add":
            tid = e["id"]
            tasks[tid] = {
                "id": tid,
                "title": e.get("title", ""),
                "plan": e.get("plan", ""),
                "phase": e.get("phase", ""),
                "priority": e.get("priority", "normal"),
                "source": e.get("source", ""),
                "parent": e.get("parent", "") or "",
                "points": e.get("points"),
                "points_rationale": "",
                "status": "pending",
                "agent": "",
                "commit": "",
                "notes": [],
                "children": [],
                "depth": 0,
                "created_ts": ts,
                "updated_ts": ts,
            }

        elif t == "task_estimate":
            tid = e.get("id")
            if tid not in tasks:
                continue
            pts = e.get("points")
            if isinstance(pts, int) and pts in FIB_POINTS:
                tasks[tid]["points"] = pts
            elif isinstance(pts, (int, float)):
                tasks[tid]["points"] = snap_fib(pts)
            tasks[tid]["points_rationale"] = e.get("rationale", "")
            tasks[tid]["updated_ts"] = ts

        elif t == "task_split":
            tid = e.get("id")
            if tid in tasks:
                tasks[tid]["updated_ts"] = ts

        elif t == "task_status":
            tid = e.get("id")
            if tid not in tasks:
                continue
            s = e.get("status")
            agent = e.get("agent", "")
            if s in VALID_STATUS:
                tasks[tid]["status"] = s
            if s in TERMINAL_STATUS or s == "pending":
                tasks[tid]["agent"] = "" if s == "pending" else agent
            else:
                tasks[tid]["agent"] = agent or tasks[tid]["agent"]
            if e.get("commit"):
                tasks[tid]["commit"] = e["commit"]
            if e.get("note"):
                tasks[tid]["notes"].append({"ts": ts, "agent": agent, "note": e["note"]})
            tasks[tid]["updated_ts"] = ts

        elif t == "session_start":
            active = {"agent": e.get("agent", ""), "goal": e.get("goal", ""), "ts": ts}
            sessions.append({**active, "kind": "start"})

        elif t == "session_end":
            sess = {
                "agent": e.get("agent", ""),
                "handoff": e.get("handoff", ""),
                "decisions": e.get("decisions", []),
                "ts": ts,
                "kind": "end",
            }
            sessions.append(sess)
            if active and active.get("agent") == sess["agent"]:
                active = None

    # back-link children
    for tid, task in tasks.items():
        p = task["parent"]
        if p and p in tasks:
            tasks[p]["children"].append(tid)

    # compute depth (walk parent chain; cycles guarded by hop cap)
    for tid, task in tasks.items():
        depth = 0
        cur = task["parent"]
        hops = 0
        while cur and cur in tasks and hops < 32:
            depth += 1
            cur = tasks[cur]["parent"]
            hops += 1
        task["depth"] = depth

    # composite auto-rollup: parent completes when all children terminal and ≥1 completed
    for _ in range(MAX_DEPTH + 2):
        changed = False
        for tid, task in tasks.items():
            if not task["children"]:
                continue
            if task["status"] in TERMINAL_STATUS:
                continue
            children = [tasks[c] for c in task["children"] if c in tasks]
            if not children:
                continue
            all_terminal = all(c["status"] in TERMINAL_STATUS for c in children)
            any_completed = any(c["status"] == "completed" for c in children)
            if all_terminal and any_completed:
                task["status"] = "completed"
                task["agent"] = ""
                changed = True
        if not changed:
            break

    # leaf_points rollup (post-order, memoized)
    memo: dict[str, int] = {}

    def leaf_points(tid: str, seen: set[str] | None = None) -> int:
        seen = seen or set()
        if tid in memo:
            return memo[tid]
        if tid in seen:
            return 0
        seen = seen | {tid}
        task = tasks[tid]
        if not task["children"]:
            if task["status"] == "cancelled":
                memo[tid] = 0
            else:
                memo[tid] = int(task["points"] or 0)
        else:
            memo[tid] = sum(leaf_points(c, seen) for c in task["children"] if c in tasks)
        return memo[tid]

    for tid in tasks:
        tasks[tid]["leaf_points"] = leaf_points(tid)
        tasks[tid]["kind"] = "leaf" if not tasks[tid]["children"] else "composite"

    task_list = list(tasks.values())
    counts = {s: 0 for s in VALID_STATUS}
    for tk in task_list:
        counts[tk["status"]] = counts.get(tk["status"], 0) + 1

    # by_plan only lists root tasks (no parent)
    by_plan: dict[str, dict[str, list[str]]] = {}
    for tk in task_list:
        if tk["parent"]:
            continue
        plan = tk["plan"] or "_"
        phase = tk["phase"] or "_"
        by_plan.setdefault(plan, {}).setdefault(phase, []).append(tk["id"])

    last_end = next((s for s in reversed(sessions) if s["kind"] == "end"), None)

    return {
        "generated_ts": now_iso(),
        "active_session": active,
        "last_session_end": last_end,
        "counts": counts,
        "tasks": task_list,
        "by_plan": by_plan,
    }


# ── LLM provider chain ─────────────────────────────────────────────────────

ESTIMATE_PROMPT = """\
You are estimating a software engineering task on the Fibonacci point scale.

Scale (strict — pick one):
  1   ~30 min     single file, single concept
  2   ~1 h        single file or trivial multi
  3   ~2-3 h      multi-file, well-bounded
  5   ~half day   cross-system, single concern
  8   ~full day   requires design choice
  13  ~2-3 days   epic, must be split
  21  multi-week  must be split into multiple plans

Task:
  id:    {id}
  plan:  {plan}
  phase: {phase}
  title: {title}

Return STRICT JSON only, nothing else:
  {{"points": <1|2|3|5|8|13|21>, "rationale": "<one sentence>"}}
"""

SPLIT_PROMPT = """\
You are splitting a software engineering task into sub-tasks.

Each sub-task MUST be 1 point on the Fibonacci scale (roughly 30 minutes of
focused work: single file OR single concept OR one test case OR one migration
step). Propose 2 to 8 children. Children must:
  - each be self-contained (no undefined dependency on a later sibling)
  - each describe a single concrete artifact or verifiable change
  - collectively cover the parent (no gaps)
  - have titles at least 12 characters long
  - have titles that differ from the parent title

Parent task:
  id:     {id}
  plan:   {plan}
  phase:  {phase}
  points: {points}
  title:  {title}

Return STRICT JSON only, nothing else:
  {{"children": [{{"title": "..."}}, ...], "rationale": "<one sentence>"}}
"""


def _parse_json_strict(text: str) -> dict[str, Any] | None:
    text = text.strip()
    # strip common LLM code-fence wrappers
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def _ollama_up() -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError, TimeoutError):
        return False


def _ollama_call(prompt: str) -> dict[str, Any] | None:
    try:
        body = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.2},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"[ledger] ollama error: {exc}", file=sys.stderr)
        return None
    return _parse_json_strict(payload.get("response", ""))


def _anthropic_call(prompt: str) -> dict[str, Any] | None:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        body = json.dumps({
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"[ledger] anthropic error: {exc}", file=sys.stderr)
        return None
    content = payload.get("content") or []
    text = "".join(part.get("text", "") for part in content if part.get("type") == "text")
    return _parse_json_strict(text)


def call_splitter(kind: str, prompt: str, *, payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return parsed response dict, or None if stdout-fallback prompt was emitted.
    kind ∈ 'estimate'|'split'. payload is the task info for stdout rendering."""
    chain = []
    if LEDGER_LLM in ("auto", "ollama") and _ollama_up():
        chain.append(("ollama", _ollama_call))
    if LEDGER_LLM in ("auto", "anthropic") and ANTHROPIC_API_KEY:
        chain.append(("anthropic", _anthropic_call))

    for name, fn in chain:
        result = fn(prompt)
        if result is not None:
            result["_provider"] = name
            return result

    # stdout fallback — print parseable prompt for the Cursor agent to fulfill
    tid = payload.get("id", "")
    if kind == "estimate":
        fulfill = f'python3 task_ledger.py estimate {tid} --apply --points <N> --rationale "<one sentence>"'
    else:
        fulfill = (
            f'python3 task_ledger.py split {tid} --agent <you> --apply '
            f'--child "child 1 title" --child "child 2 title" ... --rationale "<one sentence>"'
        )
    sys.stdout.write(f"\n=== LEDGER_PROMPT kind={kind} id={tid} ===\n")
    sys.stdout.write(prompt)
    sys.stdout.write("\n=== LEDGER_FULFILL_COMMAND ===\n")
    sys.stdout.write(fulfill + "\n")
    sys.stdout.write("=== END ===\n\n")
    sys.stdout.flush()
    return None


def _build_estimate_prompt(task: dict[str, Any]) -> str:
    return ESTIMATE_PROMPT.format(
        id=task["id"],
        plan=task.get("plan") or "(none)",
        phase=task.get("phase") or "(none)",
        title=task["title"],
    )


def _build_split_prompt(task: dict[str, Any]) -> str:
    return SPLIT_PROMPT.format(
        id=task["id"],
        plan=task.get("plan") or "(none)",
        phase=task.get("phase") or "(none)",
        points=task.get("points") or "?",
        title=task["title"],
    )


# ── core operations ────────────────────────────────────────────────────────

def _task_by_id(state: dict[str, Any], tid: str) -> dict[str, Any] | None:
    for t in state["tasks"]:
        if t["id"] == tid:
            return t
    return None


def apply_estimate(task_id: str, agent: str, points: int, rationale: str) -> dict[str, Any]:
    if points not in FIB_POINTS:
        points = snap_fib(points)
    return append_event({
        "type": "task_estimate",
        "id": task_id,
        "agent": agent,
        "points": points,
        "rationale": rationale or "",
    })


def apply_split(task_id: str, agent: str, child_titles: list[str], rationale: str) -> list[dict[str, Any]]:
    clean = [c.strip() for c in child_titles if c and c.strip()]
    if len(clean) < 2:
        raise SystemExit("split requires at least 2 children")
    if len(clean) > 8:
        raise SystemExit("split refuses more than 8 children (hallucination guard)")
    for title in clean:
        if len(title) < MIN_TITLE_LEN:
            raise SystemExit(f"child title too short (<{MIN_TITLE_LEN}): {title!r}")

    def builder(current: list[dict[str, Any]]) -> list[dict[str, Any]]:
        parent = None
        for e in current:
            if e.get("type") == "task_add" and e.get("id") == task_id:
                parent = e
        if parent is None:
            raise SystemExit(f"parent task not found: {task_id}")
        parent_title_n = norm_title(parent.get("title", ""))
        existing_titles = {
            norm_title(e.get("title", ""))
            for e in current
            if e.get("type") == "task_add" and e.get("parent") == task_id
        }
        out: list[dict[str, Any]] = []
        child_ids: list[str] = []
        for i, title in enumerate(clean):
            if norm_title(title) == parent_title_n:
                raise SystemExit(f"child title matches parent: {title!r}")
            if norm_title(title) in existing_titles:
                raise SystemExit(f"duplicate child title under this parent: {title!r}")
            existing_titles.add(norm_title(title))
            cid = next_task_id(current + out, offset=0)
            # next_task_id counts only task_add events in `current + out`
            child_ids.append(cid)
            out.append({
                "type": "task_add",
                "id": cid,
                "title": title,
                "plan": parent.get("plan", ""),
                "phase": parent.get("phase", ""),
                "priority": parent.get("priority", "normal"),
                "source": f"split:{task_id}",
                "parent": task_id,
                "points": 1,
            })
        out.append({
            "type": "task_split",
            "id": task_id,
            "agent": agent,
            "children": child_ids,
            "rationale": rationale or "",
        })
        return out

    return append_batch(builder)


def estimate_task(tid: str, agent: str, apply: bool) -> tuple[dict[str, Any] | None, int]:
    state = project(read_events())
    task = _task_by_id(state, tid)
    if task is None:
        raise SystemExit(f"unknown task: {tid}")
    if task["points"] and not apply:
        print(json.dumps({"id": tid, "points": task["points"], "already_estimated": True}, indent=2))
        return task, 0
    prompt = _build_estimate_prompt(task)
    result = call_splitter("estimate", prompt, payload={"id": tid})
    if result is None:
        return None, 2  # stdout-fallback, agent must fulfill
    raw = result.get("points")
    try:
        pts = snap_fib(int(raw))
    except (TypeError, ValueError):
        raise SystemExit(f"estimator returned bad points: {raw!r}")
    rationale = result.get("rationale", "")
    if apply:
        apply_estimate(tid, agent, pts, rationale)
    state = project(read_events())
    updated = _task_by_id(state, tid) or task
    print(json.dumps({
        "id": tid,
        "points": pts,
        "rationale": rationale,
        "provider": result.get("_provider", "llm"),
        "applied": bool(apply),
    }, indent=2))
    return updated, 0


def split_task(tid: str, agent: str, apply: bool) -> tuple[list[str], int]:
    state = project(read_events())
    task = _task_by_id(state, tid)
    if task is None:
        raise SystemExit(f"unknown task: {tid}")
    if not task["points"]:
        raise SystemExit(f"task {tid} has no estimate; run `estimate` first")
    if task["points"] == 1:
        raise SystemExit(f"task {tid} is already 1pt; nothing to split")
    if task["children"]:
        raise SystemExit(f"task {tid} is already split into {len(task['children'])} children")
    if task["depth"] >= MAX_DEPTH:
        raise SystemExit(f"task {tid} at MAX_DEPTH={MAX_DEPTH}; refusing to split further")

    prompt = _build_split_prompt(task)
    result = call_splitter("split", prompt, payload={"id": tid})
    if result is None:
        return [], 2
    titles = [c.get("title", "") for c in result.get("children", []) if isinstance(c, dict)]
    rationale = result.get("rationale", "")
    if apply:
        apply_split(tid, agent, titles, rationale)
    print(json.dumps({
        "id": tid,
        "children_proposed": titles,
        "rationale": rationale,
        "provider": result.get("_provider", "llm"),
        "applied": bool(apply),
    }, indent=2))
    return titles, 0


# ── commands ───────────────────────────────────────────────────────────────

def _task_marker(task: dict[str, Any]) -> str:
    if task["status"] in TERMINAL_STATUS:
        return f"[{task['status']}]"
    if task["children"]:
        return f"[composite {task['leaf_points']}p / {_leaf_count(task)}leaves]"
    if task["points"] is None:
        return "[NEEDS-EST]"
    if task["points"] == 1:
        return "[1p]"
    return f"[NEEDS-SPLIT ({task['points']}p)]"


def _leaf_count(task: dict[str, Any], _state: dict[str, Any] | None = None) -> int:
    # Crude: walk children recursively in the global state. Fast for small trees.
    state = _state or project(read_events())
    by_id = {t["id"]: t for t in state["tasks"]}

    def walk(tid: str) -> int:
        t = by_id.get(tid)
        if not t:
            return 0
        if not t["children"]:
            return 1
        return sum(walk(c) for c in t["children"])

    return walk(task["id"])


def _render_tree(
    state: dict[str, Any],
    root_ids: list[str],
    indent: str = "    ",
    show_points: bool = True,
    show_status: bool = False,
) -> list[str]:
    by_id = {t["id"]: t for t in state["tasks"]}
    lines: list[str] = []

    def walk(tid: str, depth: int) -> None:
        t = by_id.get(tid)
        if not t:
            return
        pad = indent * (depth + 1)
        marker = _task_marker(t) if show_points else ""
        status_glyph = ""
        if show_status:
            sym = {"completed": "✓", "in_progress": "▶", "blocked": "!", "cancelled": "×"}
            status_glyph = sym.get(t["status"], "·") + " "
        lines.append(f"{pad}{status_glyph}{t['id']}  {t['title']}  {marker}".rstrip())
        for c in t["children"]:
            walk(c, depth + 1)

    for rid in root_ids:
        walk(rid, 0)
    return lines


def cmd_brief(args: argparse.Namespace) -> int:
    state = project(read_events())
    out: list[str] = []
    out.append("── WESCRIPTURE LEDGER ──────────────────────────────────────")
    out.append(f"   generated {state['generated_ts']}")
    out.append("")

    last = state["last_session_end"]
    if last:
        out.append(f"Last session: {last['agent']} (ended {last['ts']})")
        if last.get("handoff"):
            out.append(f"  Handoff: {last['handoff']}")
        for d in last.get("decisions", []):
            out.append(f"  · decision: {d}")
    else:
        out.append("Last session: (none)")
    out.append("")

    active = state["active_session"]
    if active:
        out.append(f"ACTIVE SESSION: {active['agent']} — {active.get('goal', '')} (since {active['ts']})")
        out.append("")

    c = state["counts"]
    out.append(
        f"Counts: pending={c.get('pending',0)} in_progress={c.get('in_progress',0)} "
        f"blocked={c.get('blocked',0)} completed={c.get('completed',0)} cancelled={c.get('cancelled',0)}"
    )

    needs_est = [t for t in state["tasks"] if t["points"] is None and t["status"] not in TERMINAL_STATUS]
    needs_split = [
        t for t in state["tasks"]
        if t["points"] and t["points"] > 1 and not t["children"] and t["status"] not in TERMINAL_STATUS
    ]
    if needs_est or needs_split:
        out.append(f"Decomposition: needs_est={len(needs_est)} needs_split={len(needs_split)}")
    out.append("")

    by_id = {t["id"]: t for t in state["tasks"]}

    in_prog = [t for t in state["tasks"] if t["status"] == "in_progress"]
    if in_prog:
        out.append("IN PROGRESS:")
        for t in in_prog:
            out.append(f"  {t['id']}  [{t['agent']}]  {t['title']}  {_task_marker(t)}".rstrip())
        out.append("")

    blocked = [t for t in state["tasks"] if t["status"] == "blocked"]
    if blocked:
        out.append("BLOCKED:")
        for t in blocked:
            last_note = t["notes"][-1]["note"] if t["notes"] else ""
            out.append(f"  {t['id']}  {t['title']}  — {last_note}")
        out.append("")

    plan_filter = getattr(args, "plan", None)
    for plan, phases in state["by_plan"].items():
        if plan_filter and plan != plan_filter:
            continue
        root_ids = [tid for ph in phases.values() for tid in ph]
        pending_roots = [tid for tid in root_ids if by_id[tid]["status"] == "pending"]
        if not pending_roots:
            continue
        total_pts = sum(by_id[tid]["leaf_points"] for tid in pending_roots)
        unest = sum(1 for tid in pending_roots if by_id[tid]["points"] is None)
        out.append(f"PLAN {plan}  ({len(pending_roots)} pending, {total_pts}p, {unest} unest):")
        for phase, ids in phases.items():
            phase_pending = [i for i in ids if by_id[i]["status"] == "pending"]
            if not phase_pending:
                continue
            out.append(f"  [{phase}]")
            out.extend(_render_tree(state, phase_pending, indent="    ", show_points=True))
        out.append("")

    notes_recent = sorted(
        ((n, t["id"], t["title"]) for t in state["tasks"] for n in t["notes"]),
        key=lambda x: x[0]["ts"],
        reverse=True,
    )[:5]
    if notes_recent:
        out.append("Recent notes:")
        for n, tid, _title in notes_recent:
            out.append(f"  {n['ts']}  {tid} [{n['agent']}]: {n['note']}")
        out.append("")

    out.append("To start a session:   python3 task_ledger.py session start --agent <you> --goal \"...\"")
    out.append("To estimate/split:    python3 task_ledger.py decompose T-XXXX --agent <you>")
    out.append("To claim a 1pt leaf:  python3 task_ledger.py status T-XXXX --agent <you> --status in_progress")
    out.append("To end a session:     python3 task_ledger.py session end --agent <you> --handoff \"...\" --decision \"...\"")
    print("\n".join(out))
    return 0


def cmd_ls(args: argparse.Namespace) -> int:
    state = project(read_events())
    rows = state["tasks"]
    if args.status:
        rows = [t for t in rows if t["status"] == args.status]
    if args.plan:
        rows = [t for t in rows if t["plan"] == args.plan]
    if args.phase:
        rows = [t for t in rows if t["phase"] == args.phase]
    if args.points:
        keep = {"id", "title", "plan", "phase", "points", "status", "parent", "children", "depth", "leaf_points", "kind"}
        rows = [{k: v for k, v in t.items() if k in keep} for t in rows]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


def cmd_tree(args: argparse.Namespace) -> int:
    state = project(read_events())
    by_id = {t["id"]: t for t in state["tasks"]}
    if args.id:
        if args.id not in by_id:
            raise SystemExit(f"unknown task: {args.id}")
        roots = [args.id]
    else:
        roots = [t["id"] for t in state["tasks"] if not t["parent"]]
    lines = _render_tree(
        state, roots, indent="  ",
        show_points=not args.no_points,
        show_status=args.status,
    )
    print("\n".join(lines))
    return 0


def cmd_add(args: argparse.Namespace) -> int:
    events = read_events()
    tid = args.id or next_task_id(events)
    existing = {e.get("id") for e in events if e.get("type") == "task_add"}
    if tid in existing:
        raise SystemExit(f"task id already exists: {tid}")
    points = None
    if args.points is not None:
        points = snap_fib(args.points)
    ev = append_event({
        "type": "task_add",
        "id": tid,
        "title": args.title,
        "plan": args.plan or "",
        "phase": args.phase or "",
        "priority": args.priority,
        "source": args.source or "",
        "parent": args.parent or "",
        "points": points,
    })
    print(json.dumps(
        {"id": tid, "title": args.title, "points": points, "parent": args.parent or "", "ts": ev["ts"]},
        ensure_ascii=False, indent=2,
    ))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    if args.status not in VALID_STATUS:
        raise SystemExit(f"status must be one of: {sorted(VALID_STATUS)}")
    ev = {"type": "task_status", "id": args.id, "agent": args.agent, "status": args.status}
    if args.note:
        ev["note"] = args.note
    if args.commit:
        ev["commit"] = args.commit
    append_event(ev)
    print(json.dumps({"id": args.id, "status": args.status, "agent": args.agent}, indent=2))
    return 0


def cmd_session(args: argparse.Namespace) -> int:
    if args.action == "start":
        append_event({"type": "session_start", "agent": args.agent, "goal": args.goal or ""})
        print(json.dumps({"session": "start", "agent": args.agent, "goal": args.goal or ""}, indent=2))
    elif args.action == "end":
        append_event({
            "type": "session_end",
            "agent": args.agent,
            "handoff": args.handoff or "",
            "decisions": args.decision or [],
        })
        print(json.dumps({
            "session": "end",
            "agent": args.agent,
            "handoff": args.handoff or "",
            "decisions": args.decision or [],
        }, indent=2))
    return 0


def cmd_estimate(args: argparse.Namespace) -> int:
    # manual override path (no LLM)
    if args.points is not None:
        if not args.apply:
            print(json.dumps({"id": args.id, "points": snap_fib(args.points), "applied": False}, indent=2))
            return 0
        apply_estimate(args.id, args.agent or "manual", snap_fib(args.points), args.rationale or "")
        print(json.dumps({"id": args.id, "points": snap_fib(args.points), "applied": True}, indent=2))
        return 0
    # LLM path
    _task, rc = estimate_task(args.id, args.agent or "llm", apply=args.apply)
    return rc


def cmd_split(args: argparse.Namespace) -> int:
    # manual / agent-fulfill path (explicit --child)
    if args.child:
        state = project(read_events())
        task = _task_by_id(state, args.id)
        if task is None:
            raise SystemExit(f"unknown task: {args.id}")
        if not task["points"]:
            raise SystemExit(f"task {args.id} has no estimate; run `estimate` first")
        if task["points"] == 1:
            raise SystemExit(f"task {args.id} is already 1pt; nothing to split")
        if task["children"]:
            raise SystemExit(f"task {args.id} is already split")
        if task["depth"] >= MAX_DEPTH:
            raise SystemExit(f"task {args.id} at MAX_DEPTH={MAX_DEPTH}")
        if not args.apply:
            print(json.dumps({"id": args.id, "children_proposed": args.child, "applied": False}, indent=2))
            return 0
        events = apply_split(args.id, args.agent, list(args.child), args.rationale or "")
        child_ids = next(e["children"] for e in events if e["type"] == "task_split")
        print(json.dumps({"id": args.id, "children": child_ids, "applied": True}, indent=2))
        return 0
    # LLM path
    _titles, rc = split_task(args.id, args.agent, apply=args.apply)
    return rc


def cmd_decompose(args: argparse.Namespace) -> int:
    """Recursive: estimate → split if >1pt → recurse on children. Exits 2 on stdout-fallback."""
    target = args.id
    max_depth = args.max_depth if args.max_depth is not None else MAX_DEPTH
    visited: set[str] = set()
    queue: list[str] = [target]

    while queue:
        tid = queue.pop(0)
        if tid in visited:
            continue
        visited.add(tid)
        state = project(read_events())
        task = _task_by_id(state, tid)
        if task is None:
            raise SystemExit(f"unknown task: {tid}")
        if task["status"] in TERMINAL_STATUS:
            continue
        if task["depth"] >= max_depth:
            # force estimate=1 if missing, then continue
            if not task["points"]:
                apply_estimate(tid, args.agent, 1, f"depth cap {max_depth}; forcing 1pt leaf")
            continue
        if not task["points"]:
            _, rc = estimate_task(tid, args.agent, apply=True)
            if rc == 2:
                print(f"[decompose] prompt emitted for {tid}; fulfill and rerun `decompose {target}`", file=sys.stderr)
                return 2
            state = project(read_events())
            task = _task_by_id(state, tid) or task
        if task["points"] and task["points"] > 1 and not task["children"]:
            _, rc = split_task(tid, args.agent, apply=True)
            if rc == 2:
                print(f"[decompose] prompt emitted for {tid}; fulfill and rerun `decompose {target}`", file=sys.stderr)
                return 2
            state = project(read_events())
            task = _task_by_id(state, tid) or task
        queue.extend(task["children"])

    # final report
    state = project(read_events())
    root = _task_by_id(state, target)
    print(json.dumps({
        "root": target,
        "leaf_points": root["leaf_points"] if root else 0,
        "kind": root["kind"] if root else "",
        "status": "decomposed",
    }, indent=2))
    return 0


# ── argparse ───────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="WeScripture task ledger — Fibonacci decomposer.")
    sub = p.add_subparsers(dest="cmd")

    b = sub.add_parser("brief", help="agent session-start briefing (default)")
    b.add_argument("--plan")
    b.set_defaults(func=cmd_brief)

    ls = sub.add_parser("ls", help="list tasks (json)")
    ls.add_argument("--status", choices=sorted(VALID_STATUS))
    ls.add_argument("--plan")
    ls.add_argument("--phase")
    ls.add_argument("--points", action="store_true", help="compact view with point fields only")
    ls.set_defaults(func=cmd_ls)

    tr = sub.add_parser("tree", help="render parent->children tree")
    tr.add_argument("id", nargs="?")
    tr.add_argument("--no-points", action="store_true")
    tr.add_argument("--status", action="store_true", help="prepend status glyph per row")
    tr.set_defaults(func=cmd_tree)

    a = sub.add_parser("add", help="register a new task")
    a.add_argument("title")
    a.add_argument("--plan", default="")
    a.add_argument("--phase", default="")
    a.add_argument("--priority", default="normal")
    a.add_argument("--source", default="")
    a.add_argument("--parent", default="")
    a.add_argument("--points", type=int)
    a.add_argument("--id")
    a.set_defaults(func=cmd_add)

    s = sub.add_parser("status", help="update task status")
    s.add_argument("id")
    s.add_argument("--agent", required=True)
    s.add_argument("--status", required=True, choices=sorted(VALID_STATUS))
    s.add_argument("--note")
    s.add_argument("--commit")
    s.set_defaults(func=cmd_status)

    est = sub.add_parser("estimate", help="estimate Fibonacci points for a task")
    est.add_argument("id")
    est.add_argument("--agent", default="")
    est.add_argument("--apply", action="store_true")
    est.add_argument("--points", type=int, help="manual override (skip LLM)")
    est.add_argument("--rationale", default="")
    est.set_defaults(func=cmd_estimate)

    sp = sub.add_parser("split", help="split an estimated task into 1pt children")
    sp.add_argument("id")
    sp.add_argument("--agent", required=True)
    sp.add_argument("--apply", action="store_true")
    sp.add_argument("--child", action="append", help="explicit child title (may repeat)")
    sp.add_argument("--rationale", default="")
    sp.set_defaults(func=cmd_split)

    dc = sub.add_parser("decompose", help="recursive estimate + split until all leaves are 1pt")
    dc.add_argument("id")
    dc.add_argument("--agent", required=True)
    dc.add_argument("--max-depth", type=int, default=None)
    dc.set_defaults(func=cmd_decompose)

    se = sub.add_parser("session", help="session start/end")
    se.add_argument("action", choices=["start", "end"])
    se.add_argument("--agent", required=True)
    se.add_argument("--goal")
    se.add_argument("--handoff")
    se.add_argument("--decision", action="append")
    se.set_defaults(func=cmd_session)

    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        argv = ["brief"]
    args = build_parser().parse_args(argv)
    if not getattr(args, "func", None):
        build_parser().print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
