#!/usr/bin/env python3
"""Offline tests for task_ledger.py Fibonacci decomposition.

Runs the CLI against an isolated ledger under a temp dir (LEDGER_DIR env var).
Exercises the manual path (--points / --child) end to end, then verifies
projection derivations: depth, leaf_points, composite rollup, cycle guard,
depth cap.

Usage:
    python3 scripts/test_ledger_decompose.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "task_ledger.py"


def run(env: dict[str, str], *args: str, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(
        [sys.executable, str(CLI), *args],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
    )
    if check and r.returncode != 0:
        sys.stderr.write(f"\nCLI failed: args={args}\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}\n")
        raise SystemExit(r.returncode)
    return r


def load_state(state_path: Path) -> dict:
    return json.loads(state_path.read_text())


def find(state: dict, tid: str) -> dict:
    for t in state["tasks"]:
        if t["id"] == tid:
            return t
    raise AssertionError(f"task not found: {tid}")


def assert_eq(got, want, msg: str) -> None:
    if got != want:
        raise AssertionError(f"{msg}: got {got!r}, want {want!r}")


def test_happy_path(tmp: Path) -> None:
    env = {"LEDGER_DIR": str(tmp), "LEDGER_LLM": "stdout"}
    state_path = tmp / "ledger-state.json"

    run(env, "add", "parent task to be decomposed into real children")
    # force stdout LLM so auto-estimate would emit prompt; use manual override instead
    run(env, "estimate", "T-0001", "--apply", "--points", "5", "--rationale", "test estimate")
    run(
        env, "split", "T-0001", "--agent", "tester", "--apply",
        "--child", "first concrete sub-task with enough length",
        "--child", "second concrete sub-task with enough length",
        "--child", "third concrete sub-task with enough length",
        "--child", "fourth concrete sub-task with enough length",
        "--child", "fifth concrete sub-task with enough length",
        "--rationale", "five slices",
    )
    state = load_state(state_path)
    parent = find(state, "T-0001")
    assert_eq(parent["points"], 5, "parent.points")
    assert_eq(len(parent["children"]), 5, "parent.children count")
    assert_eq(parent["kind"], "composite", "parent.kind")
    assert_eq(parent["leaf_points"], 5, "parent.leaf_points (sum of five 1pt leaves)")

    for cid in parent["children"]:
        child = find(state, cid)
        assert_eq(child["parent"], "T-0001", f"{cid}.parent")
        assert_eq(child["points"], 1, f"{cid}.points")
        assert_eq(child["depth"], 1, f"{cid}.depth")
        assert_eq(child["kind"], "leaf", f"{cid}.kind")

    # mark all children completed → parent should auto-roll up
    for cid in parent["children"]:
        run(env, "status", cid, "--agent", "tester", "--status", "completed",
            "--commit", "abcdef1", "--note", f"done {cid}")
    state = load_state(state_path)
    parent = find(state, "T-0001")
    assert_eq(parent["status"], "completed", "parent rollup status")

    print("[ok] happy path: 5pt parent → 5 × 1pt children, rollup on completion")


def test_depth_cap(tmp: Path) -> None:
    env = {"LEDGER_DIR": str(tmp), "LEDGER_LLM": "stdout", "LEDGER_MAX_DEPTH": "2"}
    run(env, "add", "root task for depth cap test run")
    run(env, "estimate", "T-0001", "--apply", "--points", "8", "--rationale", "big")
    run(
        env, "split", "T-0001", "--agent", "tester", "--apply",
        "--child", "child one that itself must be split again",
        "--child", "child two that itself must be split again",
    )
    # children were allocated points=1 by split (that's the contract).
    # Depth cap is really about preventing further splits; let's try forcing it.
    state_path = tmp / "ledger-state.json"
    state = load_state(state_path)
    parent = find(state, "T-0001")
    c1 = parent["children"][0]

    # manually re-estimate c1 as 5pt so a split attempt is valid
    run(env, "estimate", c1, "--apply", "--points", "5", "--rationale", "bigger than expected")
    # split c1 to produce depth-2 leaves
    r = run(
        env, "split", c1, "--agent", "tester", "--apply",
        "--child", "depth two child alpha with padding here",
        "--child", "depth two child bravo with padding here",
        check=True,
    )
    state = load_state(state_path)
    grandkids = find(state, c1)["children"]
    for gk in grandkids:
        assert_eq(find(state, gk)["depth"], 2, f"{gk}.depth")

    # now try to split a grandchild — depth would be 3, MAX_DEPTH=2 → must refuse
    gk = grandkids[0]
    run(env, "estimate", gk, "--apply", "--points", "3", "--rationale", "still too big")
    r = run(env, "split", gk, "--agent", "tester", "--apply",
            "--child", "this would be depth three which is banned",
            "--child", "this would be depth three which is banned xx",
            check=False)
    if r.returncode == 0:
        raise AssertionError(f"split at MAX_DEPTH=2 should fail; got rc=0\nstdout:{r.stdout}\nstderr:{r.stderr}")
    print("[ok] depth cap: split refused at MAX_DEPTH")


def test_cycle_guard(tmp: Path) -> None:
    env = {"LEDGER_DIR": str(tmp), "LEDGER_LLM": "stdout"}
    run(env, "add", "cycle guard parent task identity")
    run(env, "estimate", "T-0001", "--apply", "--points", "3", "--rationale", "x")
    r = run(env, "split", "T-0001", "--agent", "tester", "--apply",
            "--child", "cycle guard parent task identity",  # same as parent
            "--child", "another legitimate sub-task title",
            check=False)
    if r.returncode == 0:
        raise AssertionError("split with child title matching parent should fail")
    print("[ok] cycle guard: child title matching parent refused")


def test_stdout_fallback(tmp: Path) -> None:
    """With LEDGER_LLM=stdout and no --points, estimate exits 2 and prints prompt."""
    env = {"LEDGER_DIR": str(tmp), "LEDGER_LLM": "stdout", "OLLAMA_URL": "http://127.0.0.1:1"}
    run(env, "add", "task needing agent-driven estimation")
    r = run(env, "estimate", "T-0001", "--agent", "tester", "--apply", check=False)
    if r.returncode != 2:
        raise AssertionError(f"stdout-fallback estimate should return 2, got {r.returncode}")
    if "LEDGER_PROMPT" not in r.stdout or "LEDGER_FULFILL_COMMAND" not in r.stdout:
        raise AssertionError(f"stdout fallback missing parseable markers:\n{r.stdout}")
    print("[ok] stdout fallback: prompt emitted, exit code 2, markers present")


def test_min_title_len(tmp: Path) -> None:
    env = {"LEDGER_DIR": str(tmp), "LEDGER_LLM": "stdout"}
    run(env, "add", "parent task for min title length check")
    run(env, "estimate", "T-0001", "--apply", "--points", "3", "--rationale", "x")
    r = run(env, "split", "T-0001", "--agent", "tester", "--apply",
            "--child", "short",  # too short
            "--child", "also fine long enough",
            check=False)
    if r.returncode == 0:
        raise AssertionError("split with too-short child should fail")
    print("[ok] min title length enforced")


def test_thirteen_child_split(tmp: Path) -> None:
    """Default LEDGER_MAX_SPLIT_CHILDREN=21 must allow a 13p parent -> 13 leaves."""
    env = {"LEDGER_DIR": str(tmp), "LEDGER_LLM": "stdout"}
    run(env, "add", "thirteen child split parent task title here")
    run(env, "estimate", "T-0001", "--apply", "--points", "13", "--rationale", "epic")
    children = [f"child task number {i} with enough padding here" for i in range(13)]
    cmd = ["split", "T-0001", "--agent", "tester", "--apply", "--rationale", "13-way split"]
    for c in children:
        cmd.extend(["--child", c])
    run(env, *cmd)
    state = json.loads((tmp / "ledger-state.json").read_text())
    parent = find(state, "T-0001")
    assert_eq(len(parent["children"]), 13, "thirteen-way split child count")
    assert_eq(parent["leaf_points"], 13, "leaf_points rollup")
    print("[ok] 13-child split accepted (MAX_SPLIT_CHILDREN default 21)")


def main() -> int:
    with tempfile.TemporaryDirectory() as d1, \
         tempfile.TemporaryDirectory() as d2, \
         tempfile.TemporaryDirectory() as d3, \
         tempfile.TemporaryDirectory() as d4, \
         tempfile.TemporaryDirectory() as d5, \
         tempfile.TemporaryDirectory() as d6:
        test_happy_path(Path(d1))
        test_depth_cap(Path(d2))
        test_cycle_guard(Path(d3))
        test_stdout_fallback(Path(d4))
        test_min_title_len(Path(d5))
        test_thirteen_child_split(Path(d6))
    print("\nall tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
