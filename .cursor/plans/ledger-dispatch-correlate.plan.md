# Ledger + Crew integration + correlate (plan)

## Goals (latest)

1. **Connect** [`task-ledger.jsonl`](task-ledger.jsonl) (T-*) and [`diagnostics/crew_events.jsonl`](diagnostics/crew_events.jsonl) (C-*) so work is not siloed.
2. Make **CrewAI** the **default executor for small tasks**—anything that is quick, bounded, and either handled by [`task_dispatch.try_dispatch`](lds_pipeline/task_dispatch.py) or explicitly classified as “small.”
3. Keep **long / heavy** jobs (full [`correlate_embeddings.py`](lds_pipeline/correlate_embeddings.py), bulk syncs) as **direct scripts or nohup**, not inside a tight Crew loop.
4. **Donaldson gaps:** treat missing commentary as partly a **similarity problem**: neighboring verses/chapters with rich Donaldson or graph edges should **inform** what to fill (notes, scaffolding, or ranked “see also” hints)—not hand-waved.

## Current architecture (facts)

- **Ledger:** [`task_ledger.py`](lds_pipeline/task_ledger.py) `next` picks lowest `task_id` pending; blocks on huge **Donaldson — …** backlog for dispatch-only workers.
- **Crew:** [`crew_swarm/runner.py`](lds_pipeline/crew_swarm/runner.py) drains **only** `crew_events.jsonl`; [`swarm.py`](lds_pipeline/crew_swarm/swarm.py) runs a 3-agent crew whose worker tool is [`run_wescripture_dispatch`](lds_pipeline/crew_swarm/tools.py) → same `try_dispatch` as [`task_worker`](lds_pipeline/task_worker.py).
- **Implication:** Donaldson titles today get `handled: false` from dispatch; Crew **alone** does not write `library/donaldson/*.json` unless we add tools (e.g. scaffold file, Claude, or hybrid).

## Phase A — Unblock + policy (still required)

1. **`next --exclude-title-prefix`** on ledger (e.g. `"Donaldson —"`) so dispatch/`task_worker` can reach Corpus tasks.
2. **`task_worker`:** pass that flag when `--backend dispatch`.

## Phase B — Connect ledger ↔ Crew (bridge)

**Intent:** One clear path: *small tasks* land in the ledger (or are mirrored there), and **Crew drains them** instead of duplicating two mental models.

**Recommended design (minimal coupling):**

- **`ledger_pull_feeder` (new script):**  
  - Read projected pending tasks from ledger (reuse [`task_ledger._project`](lds_pipeline/task_ledger.py) / `list --format json`).  
  - Filter: titles that match **Crew-eligible** rules (see below).  
  - For each, **enqueue** into [`crew_swarm.events.enqueue_task`](lds_pipeline/crew_swarm/events.py) with **notes** containing `ledger_task_id: T-xxxx` so completion can be mirrored.  
  - Dedupe: skip if a crew task with same title or same `ledger_task_id` already pending.

- **`crew completion → ledger:****  
  - After `run_swarm_on_task` succeeds, append **`task_completed`** to ledger for the linked `T-xxxx` (reuse `task_ledger.py complete` logic or shared helper).  
  - On failure, **`task_reopened`** or notes on ledger with error summary.

- **`runner.py` extension:** optional `--after-run complete-ledger` or keep feeder + runner separate so runner stays dumb.

**Crew-eligible (small) task policy (initial):**

- Prefixes handled by dispatch: `Corpus maintenance:`, `Corpus audit:`, `Ch …: add entity span annotations`, registry Wikipedia, Christ —, etc.  
- **Exclude:** `Corpus pipeline: run correlate_embeddings` (full), anything estimated **>15–30 min** CPU, or env `CREW_BLOCK_TITLE_REGEX`.  
- **Donaldson:** include only after Phase C (scaffold/hybrid); until then either remain **excluded** from automatic Crew or use **hybrid** worker.

## Phase C — Donaldson + “similar verses” hints

**Not** asking Crew to hallucinate whole commentary blindly.

1. **Pipeline helper (deterministic):** e.g. `lds_pipeline/donaldson_hint_from_graph.py`  
   - Input: chapter id (e.g. `1_chronicles_10`).  
   - Use existing artifacts: [`build_graph`](lds_pipeline/build_graph.py) / [`verse_discovery`](library/verse_discovery.json) / neighbor chapters in same book with non-empty Donaldson.  
   - Output: short **notes block** appended to ledger/Crew task: “Similar filled chapters: …”, “Top semantic neighbors: …”.

2. **Dispatch or tool:** optional `StructuredTool` that runs the hint script and returns text for the LLM to **structure** into schema-compliant JSON (still subject to human review if quality low).

3. **Crew role:** **editor/assembler** for small Donaldson files when hints + schema are present—not sole author for 50+ chapter batches without review.

## Phase D — Correlate

- **Smoke:** `--books Genesis` once cache + catalog exist.  
- **Full:** nohup / CI; document in [`corpus_missing_list.txt`](lds_pipeline/reports/corpus_missing_list.txt).

## Phase E — Operator UX

- Document: **“Small tasks → Crew loop”** = run `ledger_pull_feeder` on a timer + `crew_swarm/runner.py --loop` OR extend [`run_crew_swarm_forever.sh`](lds_pipeline/run_crew_swarm_forever.sh).  
- [`agent_ui_server`](lds_pipeline/agent_ui_server.py): optional “pull from ledger” button → calls feeder (future).

## Execution order when implementing

1. Phase A (ledger exclude-prefix + task_worker). **Done**
2. Phase B (feeder + ledger completion mirror) with strict Crew-eligible list. **Done** — `lds_pipeline/ledger_to_crew_feeder.py`; `lds_pipeline/crew_swarm/swarm.py` mirrors ledger complete/reopen when `ledger_task_id:T-*` appears in crew notes.
3. Phase D smoke correlate. **Done** — `correlate_embeddings.py --books Genesis` (1533 verse JSON under cache, gitignored).
4. Phase C Donaldson hints + optional Crew tool. **Not started**
5. Phase E docs / shell glue. **Partial** — run `python3 lds_pipeline/ledger_to_crew_feeder.py` before `crew_swarm/runner.py --loop` as needed.

---

**Execution:** implemented 2026-04-11 (Phases A, B, D partial).
