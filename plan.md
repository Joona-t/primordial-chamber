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
