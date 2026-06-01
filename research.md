# Primordial audit implementation research

## Source idea
Primordial's useful systems pattern for Hermes is not a large runtime transplant. The high-leverage transplant is a small, deterministic data layer:

1. typed absence states instead of ambiguous null/empty strings;
2. stable references for evidence and artifacts;
3. reversible summaries that preserve provenance and can be expanded;
4. chamber-style multi-voice synthesis records;
5. local JSONL storage for these records;
6. verification metadata for subagent artifacts before a parent trusts them.

## Hermes integration surface
Hermes already has durable memory, session DB, delegation, kanban artifacts, and context compression. The safest implementation path is a `agent.primordial` support package, not a new toolset or prompt mutation. This keeps prompt caching stable and makes the primitives testable in isolation.

Delegation is the only active integration point for this pass. `_run_single_child()` already gathers `files_written` for progress payloads but does not return artifact verification to the parent. We can add a deterministic verification seam: inspect child-written paths, reject paths that do not exist / are not files / are outside the child write set, and return compact metadata in each delegation result. No LLM judgment, no side effects beyond filesystem stat+hash reads.

## Constraints
- No prompt/schema churn unless necessary.
- No persistent memory writes for task progress.
- Keep primitives provider-agnostic and dependency-free.
- Use `get_hermes_home()` for default stores.
- Tests must not touch real `~/.hermes`; pytest already redirects home in most cases, but explicit temp paths are used for new store tests.

## Target files
- `agent/primordial/absence.py`
- `agent/primordial/refs.py`
- `agent/primordial/summary.py`
- `agent/primordial/chamber.py`
- `agent/primordial/store.py`
- delegation artifact verification helpers in `tools/delegate_tool.py`
- tests under `tests/agent/primordial/` and `tests/tools/test_delegate.py`

---

# Codex `NoneType` iterable failure audit

## User-reported failures
Two observed failures share the same exception text:

1. Main Hermes turn on `provider=openai-codex`, `model=gpt-5.5`, endpoint `https://chatgpt.com/backend-api/codex`:
   - `API call failed (attempt 1/3): TypeError`
   - `Error: 'NoneType' object is not iterable`
   - classified as non-retryable because local `TypeError` is treated as a programming bug.
2. Background auxiliary title generation:
   - `Auxiliary title generation failed: 'NoneType' object is not iterable`

## Current repo state relevant to this audit
- `agent/codex_runtime.py` is already modified and contains a partial fix:
  - `_sanitize_responses_sdk_kwargs()` removes `None` and empty optional iterable kwargs for `context_management`, `include`, and `tools`.
  - `run_codex_stream()` and `run_codex_create_stream_fallback()` now pass sanitized kwargs into the OpenAI Responses SDK.
  - TypeErrors around `responses.stream()` / `responses.create(stream=True)` are logged with key diagnostics.
- `tests/agent/test_codex_runtime.py` is untracked and verifies the partial fix for request kwargs.
- `agent/auxiliary_client.py` is not modified for this issue.

## Main-turn failure path
- `agent/chat_completion_helpers.py::interruptible_api_call()` calls `agent._run_codex_stream()` for `api_mode == "codex_responses"`.
- `agent/codex_runtime.py::run_codex_stream()` previously passed raw `api_kwargs` directly into `active_client.responses.stream(**api_kwargs)`.
- If the SDK locally iterates a kwarg whose value is `None`, it raises `TypeError("'NoneType' object is not iterable")` before an HTTP status exists.
- `agent/conversation_loop.py` then treats local `TypeError` as `is_local_validation_error`, emits `Non-retryable error (HTTP None)`, tries fallback once, and aborts if no fallback activates.
- The current modified `agent/codex_runtime.py` addresses this specific request-kwarg vector by omitting unset iterable kwargs before the SDK call.

## Response-output failure path
- `agent/codex_runtime.py::run_codex_stream()` backfills output only when `final_response.output` is an empty list:
  - `if isinstance(_out, list) and not _out: ...`
- `agent/codex_runtime.py::run_codex_create_stream_fallback()` has the same empty-list-only backfill check for `terminal_response.output`.
- If `output is None`, the main path does not iterate it, but it also does not synthesize from collected stream items or deltas. The response later fails strict validation in `agent/transports/codex.py::validate_response()`.
- `agent/codex_responses_adapter.py::_normalize_codex_response()` handles `output is None` safely by raising `RuntimeError("Responses API returned no output items")` or using `output_text`, but the main conversation validation layer normally rejects invalid output before normalization unless `output_text` exists.

## Auxiliary title-generation failure path
- `agent/title_generator.py::generate_title()` calls `agent.auxiliary_client.call_llm(task="title_generation", ...)`.
- With `openai-codex`, `agent/auxiliary_client.py::_CodexCompletionsAdapter.create()` streams Responses output and then extracts text.
- It backfills only when `final.output` is an empty list:
  - `if isinstance(_output, list) and not _output: ...`
- It then iterates:
  - `for item in getattr(final, "output", []):`
- If the SDK response has an `output` attribute set to `None`, `getattr(final, "output", [])` returns `None`, so the loop raises the exact reported `TypeError("'NoneType' object is not iterable")`.
- This is the clearest live bug for the auxiliary title warning.

## Test coverage gaps
- Existing targeted tests pass:
  - `pytest tests/agent/test_codex_runtime.py tests/agent/test_title_generator.py tests/agent/transports/test_codex_transport.py -q -o 'addopts='` -> 68 passed.
  - `pytest tests/agent/test_auxiliary_client.py::TestCodexAdapterReasoningTranslation tests/agent/test_auxiliary_client.py::TestCodexAuxiliaryAdapterTimeout -q -o 'addopts='` -> 14 passed.
- Missing tests:
  - Main Codex stream where `get_final_response().output is None` but `response.output_item.done` or text deltas were collected.
  - `create(stream=True)` fallback where terminal response has `output is None` but collected items/deltas exist.
  - Auxiliary Codex adapter where `final.output is None`; it should not raise `TypeError`.
  - Auxiliary title generation should receive a clean `None` result or synthesized title text instead of surfacing raw local TypeError.

## Audit verdict
The current partial fix likely covers the main-turn request-kwarg source of the historical `NoneType` iterable crash. It does not cover the auxiliary Codex response-output source, and it incompletely handles `output is None` in main Codex response backfill. A complete fix should normalize `None` output to an empty sequence in all Codex stream/backfill paths, synthesize from collected items/deltas when possible regardless of `[]` vs `None`, and add regression tests for both main and auxiliary paths.
