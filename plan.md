# Primordial audit implementation plan

## Scope
Implement the forge-lite primitives from the Primordial audit as deterministic Hermes support code, plus a delegation artifact verification seam.

## Tasks
- [x] Add `agent.primordial` package.
- [x] Implement typed absence states and transition validation.
- [x] Implement stable content/file references.
- [x] Implement reversible summaries with source refs and expansion helpers.
- [x] Implement chamber records for multi-voice synthesis.
- [x] Implement JSONL store under Hermes home by default.
- [x] Add delegation artifact verification helpers.
- [x] Return verified artifact metadata from child delegation results.
- [x] Add unit tests for all new primitives.
- [x] Add delegation artifact verification tests.
- [x] Run targeted tests.
- [x] Review diff.

## Non-goals
- No new LLM prompt requirements.
- No new provider or tool schema.
- No autonomous memory learning.
- No UI changes.

## Verification
Executed:

```bash
pytest tests/agent/primordial tests/tools/test_delegate_artifacts.py -o 'addopts=' -q
pytest tests/tools/test_delegate.py tests/tools/test_delegate_artifacts.py -o 'addopts=' -q
python3 -m compileall -q agent/primordial tools/delegate_tool.py tests/agent/primordial tests/tools/test_delegate_artifacts.py
```

---

# Codex `NoneType` iterable fix plan

## Scope
Fix the audited OpenAI Codex Responses paths that can surface raw
`TypeError("'NoneType' object is not iterable")` during main turns and
auxiliary title generation.

## Tasks
- [x] Normalize Codex stream backfill so `output is None` is handled like an empty output list.
- [x] Normalize Codex `create(stream=True)` fallback backfill for `output is None`.
- [x] Normalize auxiliary Codex response extraction so `final.output is None` never gets iterated.
- [x] Add regression tests for main Codex stream `output is None` with streamed items/deltas.
- [x] Add regression tests for fallback stream terminal `output is None`.
- [x] Add regression tests for auxiliary Codex adapter `output is None`.
- [x] Run targeted Codex runtime, transport, title, and auxiliary tests.
- [x] Run compile check on touched modules.

## Non-goals
- No provider routing changes.
- No retry-classifier policy changes beyond preventing the local TypeError.
- No Primordial-only agent harness in this pass; that requires its own research and plan because it is a new architecture surface.

## Follow-up: Primordial Harness
Research a dedicated Primordial agent harness as a separate feature. The likely shape is a narrow, deterministic harness that runs Primordial primitives and verification records without coupling them to the general Hermes conversation loop.

---

# Primordial Harness Plan

Date: 2026-06-01
Status: planned; do not implement yet

## Scope

Implement a passive `agent.primordial.harness` recorder and wire it only to delegation completion in v1.

The harness will persist auditable Primordial records for subagent results:

- status and lifecycle outcome;
- summary text or typed absence;
- verified/rejected child artifacts;
- model, token, cost, duration metadata;
- stable source refs where available.

This is a ledger layer, not a new model-facing tool.

## Non-Goals

- No prompt changes.
- No provider/schema changes.
- No autonomous memory learning.
- No compression behavior changes.
- No UI changes.
- No SQLite migration in this pass.
- No full transcript duplication into JSONL.

## Data Contract

Use `PrimordialStore` as the persistence layer.

Record type:

```text
delegation_result
```

Required payload fields:

- `parent_session_id`
- `task_index`
- `status`
- `summary` or `summary_state`
- `artifacts`
- `model`
- `tokens`
- `cost_usd`
- `duration_seconds`
- `source_refs`
- `metadata`

Typed absence rules:

- no summary + timeout/interrupted/error -> `summary_state: unresolved`
- no summary + completed/no output -> `summary_state: not_generated`
- withheld/redacted content -> `summary_state: redacted`
- unavailable source data -> typed absence object, not raw empty string

Artifact rules:

- every claimed artifact is either in `verified` or `rejected`;
- verified artifacts include path, byte count, SHA-256;
- rejected artifacts include path and reason;
- no artifact path disappears silently.

## Implementation Tasks

- [x] Add `agent/primordial/harness.py`.
- [x] Add `PrimordialHarness` with injectable `PrimordialStore`.
- [x] Add `record_delegation()` for normalized delegation result records.
- [x] Add helper for summary typed absence classification.
- [x] Add helper for compact delegation source refs.
- [x] Add unit tests for successful delegation with summary and artifacts.
- [x] Add unit tests for delegation with no summary -> typed absence.
- [x] Add unit tests for missing/rejected artifacts staying visible.
- [x] Add unit tests that records round-trip through `PrimordialStore`.
- [x] Wire `tools/delegate_tool.py` to call the harness after child result assembly.
- [x] Ensure harness failures are logged and do not break delegation.
- [x] Update `BUGS_AND_ITERATIONS.md`.
- [x] Run targeted Primordial and delegation tests.
- [x] Run compile check on touched modules.
- [x] Review diff.

## Expected Files

- Create: `agent/primordial/harness.py`
- Create: `tests/agent/primordial/test_harness.py`
- Modify: `agent/primordial/__init__.py`
- Modify: `tools/delegate_tool.py`
- Modify: `BUGS_AND_ITERATIONS.md`
- Modify: `plan.md`

## Verification Commands

```bash
pytest tests/agent/primordial tests/tools/test_delegate_artifacts.py -o 'addopts=' -q
pytest tests/tools/test_delegate.py tests/tools/test_delegate_artifacts.py -o 'addopts=' -q
python3 -m compileall -q agent/primordial tools/delegate_tool.py tests/agent/primordial tests/tools/test_delegate_artifacts.py
```

## Approval Gate

Implementation may begin only after Joona explicitly says:

```text
implement it all
```

Do not implement yet.
