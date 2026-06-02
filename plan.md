# Primordial audit implementation plan

## Scope
Implement the forge-lite primitives from the Primordial audit as deterministic Hermes support code, plus a delegation artifact verification seam.

---

# LLM Council Chamber Adaptation Plan

Date: 2026-06-02
Status: planned; do not implement yet

## Scope

Adapt Karpathy's `llm-council` architecture into the Primordial chamber by adding a staged council runner over local CLI-backed seats.

The implementation should preserve the useful council protocol:

```text
Stage 1: independent first opinions
Stage 2: anonymized peer review and ranking
Stage 3: chairman synthesis
```

It should replace API model calls with local seat adapters and persist the result as a schema-versioned Primordial council chamber record.

## Non-Goals

- No OpenRouter dependency.
- No FastAPI backend transplant.
- No React UI transplant.
- No remote API requirement.
- No provider-specific model registry.
- No replacement of existing two-seat `chamber_record` compatibility.

## Implementation Tasks

- [x] Add `agent/primordial/seats.py`.
- [x] Define `SeatSpec`.
- [x] Define `SeatResult`.
- [x] Move OpenClaw invocation behind the seat adapter interface.
- [x] Add Codex/Hermes and Claude placeholder seat adapters without hard dependencies.
- [x] Add `agent/primordial/council_runner.py`.
- [x] Implement Stage 1 first-opinion collection.
- [x] Implement deterministic anonymous labels: `Response A`, `Response B`, etc.
- [x] Implement Stage 2 review prompt builder.
- [x] Implement Stage 2 ranking parser using Karpathy's `FINAL RANKING:` convention.
- [x] Implement Stage 3 chairman synthesis prompt builder.
- [x] Add schema version `2` for staged council chamber records.
- [x] Store staged records as `council_chamber_record`.
- [x] Preserve typed absence for every failed seat, review, or synthesis.
- [x] Preserve source refs for every stage.
- [x] Keep old `chamber_record` compatibility.
- [x] Extend `scripts/primordial_chamber.py` with `council run`.
- [x] Extend `scripts/primordial_chamber.py` with `council show`.
- [x] Add fake two-seat Stage 1 success test.
- [x] Add one-seat-failure typed absence test.
- [x] Add review-label anonymization test.
- [x] Add valid `FINAL RANKING:` parser test.
- [x] Add chairman synthesis persistence/source-ref test.
- [x] Add no-response-disappears-silently test.
- [x] Update `BUGS_AND_ITERATIONS.md`.
- [x] Run targeted Primordial tests.
- [x] Run compile check.
- [x] Review diff.

## Expected Files

- Create: `agent/primordial/seats.py`
- Create: `agent/primordial/council_runner.py`
- Create: `tests/agent/primordial/test_seats.py`
- Create: `tests/agent/primordial/test_council_runner.py`
- Modify: `agent/primordial/openclaw_adapter.py`
- Modify: `agent/primordial/harness.py`
- Modify: `agent/primordial/__init__.py`
- Modify: `scripts/primordial_chamber.py`
- Modify: `BUGS_AND_ITERATIONS.md`
- Modify: `research.md`
- Modify: `plan.md`

## Verification Commands

```bash
pytest tests/agent/primordial -o 'addopts=' -q
python3 -m compileall -q agent/primordial scripts/primordial_chamber.py tests/agent/primordial
```

## Approval Gate

Implementation may begin only after Joona explicitly says:

```text
implement it all
```

Do not implement yet.

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

---

# Codex Chamber Orchestrator Plan

Date: 2026-06-01
Status: implementing after explicit approval

## Scope

Add a Codex-owned orchestration layer for the two-seat chamber.

The orchestrator should:

- accept one message;
- invoke OpenClaw via the existing adapter;
- accept optional Codex voice text;
- build a two-seat chamber;
- persist the chamber through `PrimordialHarness`;
- return a compact structured result.

## Non-Goals

- No Hermes slash command yet.
- No model tool schema yet.
- No direct OpenClaw queue-file writes.
- No automatic recursive call into this current assistant session.
- No UI.

## Implementation Tasks

- [x] Add `agent/primordial/orchestrator.py`.
- [x] Add `CodexChamberOrchestrator`.
- [x] Add `run_two_seat_chamber()` method.
- [x] Add `scripts/primordial_chamber.py` CLI.
- [x] Add tests for successful orchestration with fake OpenClaw runner.
- [x] Add tests for missing Codex text typed absence.
- [x] Add tests for OpenClaw failure still recording a chamber.
- [x] Export orchestrator helpers in `agent/primordial/__init__.py`.
- [x] Update `BUGS_AND_ITERATIONS.md`.
- [x] Run targeted Primordial tests.
- [x] Run compile check.
- [x] Review diff.

## Verification Commands

```bash
pytest tests/agent/primordial -o 'addopts=' -q
python3 -m compileall -q agent/primordial scripts/primordial_chamber.py tests/agent/primordial
```

---

# Production Chamber Workflow Plan

Date: 2026-06-01
Status: implemented

## Scope

Harden the Codex chamber orchestrator into a production-usable operator workflow.

## Completed Tasks

- [x] Add stable chamber ids.
- [x] Add chamber status metadata.
- [x] Add append-store record replacement by id.
- [x] Add pending `start` command.
- [x] Add `finalize` command to seal Codex text later.
- [x] Add `list` command for inspection.
- [x] Add `show` command for inspection.
- [x] Add operator documentation.
- [x] Add tests for stable ids.
- [x] Add tests for pending-to-sealed finalization.
- [x] Add tests for list/show.
- [x] Run Primordial tests.
- [x] Run compile check.
- [x] Run delegation regression tests.
- [x] Run local CLI dry run for OpenClaw unavailable path.

---

# Two-Seat Chamber Plan

Date: 2026-06-01
Status: planned; do not implement yet

## Scope

Bring up a v1 Primordial chamber that can represent one user message answered by two seats:

- `codex`: the current Hermes/Codex-side voice;
- `openclaw`: an OpenClaw `agent` CLI turn.

The v1 implementation should persist chamber records and provide a deterministic OpenClaw adapter. It should not directly mutate OpenClaw queue files.

## Non-Goals

- No UI.
- No direct OpenClaw queue-file writes.
- No new provider schema.
- No automatic recursive call to the current assistant from inside the same turn.
- No SQLite migration.
- No full transcript duplication.

## Design

Add a chamber runner layer under `agent/primordial/`:

- `openclaw_adapter.py`: run and normalize `openclaw agent --json`.
- `chamber_runner.py`: build and store `ChamberRecord` values.

The runner accepts:

- the original message;
- Codex voice text if available;
- OpenClaw voice text or adapter result;
- metadata such as Hermes session id and OpenClaw session key.

It then:

1. creates source refs;
2. creates `ChamberVoice` records;
3. creates a `ReversibleSummary` from both voice refs;
4. creates a `ChamberRecord`;
5. appends it to `PrimordialStore` as `chamber_record`.

## Implementation Tasks

- [x] Add `agent/primordial/openclaw_adapter.py`.
- [x] Add `OpenClawAgentResult` normalization for successful JSON output.
- [x] Add timeout/error normalization using typed absence metadata.
- [x] Add `agent/primordial/chamber_runner.py`.
- [x] Add `record_chamber()` to `PrimordialHarness`.
- [x] Add two-seat chamber builder for `codex` + `openclaw`.
- [x] Add tests with a fake OpenClaw command runner.
- [x] Test successful OpenClaw JSON -> chamber voice.
- [x] Test OpenClaw error/timeout -> typed absence metadata.
- [x] Test chamber record round-trip through `PrimordialStore`.
- [x] Export new helpers in `agent/primordial/__init__.py`.
- [x] Update `BUGS_AND_ITERATIONS.md`.
- [x] Run targeted Primordial tests.
- [x] Run compile check on touched modules.
- [x] Review diff.

## Expected Files

- Create: `agent/primordial/openclaw_adapter.py`
- Create: `agent/primordial/chamber_runner.py`
- Create: `tests/agent/primordial/test_openclaw_adapter.py`
- Create: `tests/agent/primordial/test_chamber_runner.py`
- Modify: `agent/primordial/harness.py`
- Modify: `agent/primordial/__init__.py`
- Modify: `BUGS_AND_ITERATIONS.md`
- Modify: `plan.md`

## Verification Commands

```bash
pytest tests/agent/primordial -o 'addopts=' -q
python3 -m compileall -q agent/primordial tests/agent/primordial
```

## Open Question For Implementation

Default OpenClaw target:

```text
agent:main:primordial-chamber
```

This keeps chamber runs separate from the normal `agent:main:main` session unless Joona asks to target main directly.

## Approval Gate

Implementation may begin only after Joona explicitly says:

```text
implement it all
```

Do not implement yet.
