# Primordial audit implementation research

## Source idea
Primordial's useful systems pattern for Hermes is not a large runtime transplant. The high-leverage transplant is a small, deterministic data layer:

1. typed absence states instead of ambiguous null/empty strings;
2. stable references for evidence and artifacts;
3. reversible summaries that preserve provenance and can be expanded;
4. chamber-style multi-voice synthesis records;
5. local JSONL storage for these records;
6. verification metadata for subagent artifacts before a parent trusts them.

---

# LLM Council Adaptation Research

Date: 2026-06-02
Status: research complete; planning complete; do not implement yet

## Source Architecture

Karpathy's `llm-council` demonstrates a three-stage deliberation architecture:

1. Stage 1: collect independent first opinions from multiple LLMs.
2. Stage 2: anonymize those responses and ask the same council to review/rank them.
3. Stage 3: ask a chairman model to synthesize a final answer from the original responses and reviews.

The implementation details in that repository are OpenRouter API calls, a FastAPI backend, JSON file storage, and a React frontend. The useful architecture for Hermes is not the API transport or UI. The useful architecture is the staged council protocol.

Primary source:

- `karpathy/llm-council`: https://github.com/karpathy/llm-council
- `backend/council.py`: https://github.com/karpathy/llm-council/blob/master/backend/council.py

## Mapping To Primordial Chamber

Current Primordial chamber:

```text
message -> Codex voice + OpenClaw voice -> chamber_record
```

Council-adapted Primordial chamber:

```text
message
  -> Stage 1: collect independent CLI seat answers
  -> Stage 2: ask seats to review anonymized answers
  -> Stage 3: Codex chairman synthesis
  -> Persist staged council_chamber_record
```

The chamber should preserve Karpathy's Stage 1 / Stage 2 / Stage 3 pattern, but replace OpenRouter model calls with local CLI-backed seats:

- Codex / Hermes
- OpenClaw
- Claude fork
- future local agents

Each seat should satisfy one narrow adapter contract:

```text
run_seat(prompt, session_key, timeout) -> SeatResult
```

The council runner should not care whether the seat is OpenClaw, Claude, Codex, or another local harness.

## Primordial Advantage

Karpathy's repository shows the working deliberation pattern. Primordial makes that pattern production-auditable:

- typed absence for missing, failed, timed-out, invalid, or unavailable seat output;
- source refs for every answer, review, and synthesis;
- sealed lifecycle status;
- stable hashes for evidence;
- append-only ledger compatibility;
- no silently dropped responses;
- cross-harness comparison without a shared API provider.

In short:

```text
LLM Council = deliberation pattern
Primordial = deliberation pattern + provenance + failure semantics + auditability
```

## Schema Implication

The current two-voice `chamber_record` should remain compatible, but staged council runs need a schema-versioned record:

```json
{
  "schema_version": 2,
  "id": "chamber:...",
  "status": "pending|reviewing|synthesizing|sealed|failed",
  "question": "...",
  "stages": {
    "stage1_first_opinions": [],
    "stage2_peer_reviews": [],
    "stage3_chairman_synthesis": {}
  },
  "seats": [],
  "source_refs": [],
  "metadata": {}
}
```

Stage outputs should carry seat ids, anonymized labels, summary text or typed absence, source refs, and review ranking metadata. Ranking parsing should preserve Karpathy's explicit final ranking convention while failing closed to typed absence when the ranking cannot be parsed.

## Research Verdict

Adapt the architecture, not the transport.

Keep:

- independent first opinions;
- anonymized peer review;
- chairman synthesis.

Replace:

- OpenRouter API calls;
- web-backend coupling;
- provider-specific model list.

Enhance:

- typed absence;
- source refs;
- staged chamber schema;
- CLI seat registry;
- persistent audit ledger.

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

---

# Primordial Harness Research

Date: 2026-06-01
Status: research only; do not implement yet

## Goal

Research a dedicated Primordial harness for Hermes that can turn the newly added `agent.primordial` primitives into an auditable run ledger without coupling them directly to the general conversation loop, provider schemas, or memory-learning behavior.

The target is a deterministic harness that records what happened, what was absent, what was summarized, and what can be recovered.

## Current Hermes Facts

Hermes now has a small committed `agent.primordial` package:

- `absence.py`: typed absence states, transition validation, semantic-empty validation.
- `refs.py`: stable content and file references with SHA-256.
- `summary.py`: reversible summaries that require source refs when summary text exists.
- `chamber.py`: simple chamber records with voices, synthesis, and metadata.
- `store.py`: append-only JSONL records under `$HERMES_HOME/primordial/records.jsonl` by default.

The only active integration seam today is delegation artifact metadata:

- `tools/delegate_tool.py::_run_single_child()` already collects child-written paths from `tools.file_state`.
- `_verify_artifact_paths()` now hashes child-written files and returns verified/rejected artifact records.
- This gives the parent structural evidence about child output, but it does not yet write a persistent chamber/run record.

## Relevant Hermes Surfaces

### Session Database

`hermes_state.py` stores durable session and message history in SQLite:

- `sessions`: session metadata, parent session lineage, compression chains, model/config/cost fields.
- `messages`: role, content, tool call ids, names, arguments, timestamps, platform ids.
- FTS indexes support search.

Research implication:

The harness should not duplicate the full transcript into JSONL. It should store compact refs to session ids, message ids, tool ids, and hashes where possible. Full session text remains owned by `state.db`.

### Context Compression

`agent/context_compressor.py` already has a strong safety framing:

- compressed summaries are reference-only;
- latest user message wins;
- old summaries must not become active instructions;
- fallback summaries preserve continuity anchors when LLM compression fails.

Research implication:

Primordial should not replace the compressor in v1. The harness should observe compression boundaries and record reversible summary metadata:

- source session id / message window;
- summary hash;
- model/provider used;
- failure typed as `not_generated`, `unresolved`, or `redacted` instead of raw empty output.

### File-State and Delegation

`tools/file_state.py` maintains process-local read/write coordination:

- per-agent reads;
- last writer per path;
- `writes_since(exclude_task_id, since_ts, paths)` for child write detection.

Research implication:

This is the best existing signal for artifact provenance during a live run. The harness can consume verified child artifacts after delegation and store file refs. The registry is process-local, so it is not enough for historical reconstruction after restart; persistence must happen at subagent completion time.

### Trajectory Logging

`agent/trajectory.py` writes ShareGPT-style JSONL trajectories but is not the session source of truth.

Research implication:

Trajectory export can be a later sink for Primordial records, not the first storage layer. The harness should target `PrimordialStore` and session refs first.

### Hooks

`tools/delegate_tool.py` fires `subagent_stop` hooks on the parent thread after child results are collected.

Research implication:

Hooks are a clean optional observation point, but the first harness should be direct library code called by delegation/compression/session boundaries. Plugin hooks can mirror records later.

## Harness Shape

The smallest useful harness is an internal recorder, not a new model-facing tool.

Proposed module:

- `agent/primordial/harness.py`

Core object:

- `PrimordialHarness(store=None, session_db=None)`

Core methods:

- `record_session_turn(session_id, message_refs, status, metadata)`
- `record_tool_call(session_id, tool_call_ref, result_ref_or_absence, metadata)`
- `record_delegation(parent_session_id, child_result, verified_artifacts, metadata)`
- `record_compression(parent_session_id, child_session_id, source_message_refs, summary, status, metadata)`
- `record_chamber(question, voices, synthesis, metadata)`

Each method should produce:

- a `record_type`;
- a normalized payload validated by `validate_record()`;
- source refs using `content_ref()` / `file_ref()` or explicit session refs;
- typed absence for missing summaries, skipped tools, interrupted children, withheld content, failed compression, or deleted artifacts.

## Data Model Needed Before Implementation

The current primitives are enough for simple records, but the harness needs a few conventions before code:

1. Session refs:
   - kind: `session_message`
   - uri: `hermes://session/{session_id}/message/{message_id}`
   - metadata: role, timestamp, optional content hash

2. Tool refs:
   - kind: `tool_call`
   - uri: `hermes://session/{session_id}/tool/{tool_call_id}`
   - metadata: tool name, args hash, result hash if available

3. Delegation refs:
   - kind: `delegate_run`
   - uri: `hermes://delegate/{subagent_id}`
   - metadata: parent session, child task id, role, status, duration

4. Compression refs:
   - kind: `compression_window`
   - uri: `hermes://session/{old_session_id}/compression/{new_session_id}`
   - metadata: source message range, token estimate, summary hash

The existing `Ref` dataclass only supports `id`, `kind`, `uri`, `sha256`, `bytes`, `mime`, and `label`. It does not yet carry arbitrary metadata. Either add a metadata field in a planned pass, or encode metadata in record payloads rather than refs for v1.

## Architecture Recommendation

Implement the harness as a passive recorder with explicit call sites.

Recommended v1 integration order:

1. Delegation completion:
   - Record one delegation result per child.
   - Include status, summary or typed absence, verified/rejected artifacts, model, token counts, cost, duration, and source refs.
   - This is the highest value because subagents are the frontier surface where outputs can vanish or become ungrounded.

2. Manual chamber creation API:
   - Add deterministic helper to create a `ChamberRecord` from named voices and a synthesis.
   - Keep it internal first; no user-facing tool until the data contract is stable.

3. Compression boundary:
   - Record compaction source window and produced summary hash.
   - Use typed absence on summarizer failure.
   - Do not alter prompt summary text in this pass.

4. Session/tool refs:
   - Add ref factories for Hermes session messages and tool calls.
   - Avoid schema migration unless JSONL records prove insufficient.

Do not implement all integration points at once. Delegation gives immediate signal with limited blast radius.

## Risks

1. False confidence:
   - Structural provenance says where a result came from; it does not prove semantic truth.
   - Records must avoid language like "verified answer" unless only hash/path verification is meant.

2. Store growth:
   - JSONL can grow quickly if full text is stored.
   - v1 should store hashes and refs, not transcript copies.

3. Privacy:
   - Hermes may run with sensitive files, credentials, or private chats.
   - Raw payloads should be withheld/redacted by default when refs/hashes are enough.

4. Coupling:
   - If harness calls are scattered through hot conversation logic too early, future provider changes get harder.
   - Start at stable boundaries: delegation completion and compression completion.

5. Ref stability:
   - Local file paths can move.
   - File refs should include hash and byte size so moved files can still be recognized if content is available.

## Test Strategy

Required tests before any implementation:

- Harness writes append-only records to a temp `PrimordialStore`.
- Delegation result with summary and artifacts creates a grounded record.
- Delegation result with no summary creates typed absence, not empty string.
- Missing artifact path is rejected with reason, not dropped.
- Compression success creates summary with source refs.
- Compression failure creates typed absence.
- No full sensitive payload is persisted when a hash/ref is enough.
- Store records are valid JSONL and round-trip through `list_records()`.

Good property-style tests later:

- Absence transitions never move out of terminal states.
- Every record with summary text has at least one source ref.
- Every claimed artifact is either verified or rejected; none disappear silently.

## Research Verdict

The Primordial harness is worth doing, but the first implementation should be narrow:

Build a passive `agent.primordial.harness` recorder and wire it only to delegation completion first. That gives Hermes a real frontier ledger for subagent output without changing provider behavior, prompts, memory learning, or compression semantics.

After that is stable, extend the same harness to compression boundaries and manual chamber records.

---

# Two-Seat Chamber Research

Date: 2026-06-01
Status: research only; do not implement yet

## User Goal

Get the chamber up and running with one user message sent to two chat sessions:

- the current Hermes/Codex session;
- an OpenClaw session.

The result should become a Primordial chamber record with both voices preserved.

## Current Capabilities

Hermes now has:

- `agent.primordial.ChamberRecord`
- `ChamberVoice`
- `ReversibleSummary`
- `PrimordialStore`
- `PrimordialHarness` for delegation records

This is enough to persist a chamber record once two outputs exist.

OpenClaw is installed locally:

```text
/opt/homebrew/bin/openclaw
```

Relevant command:

```text
openclaw agent --message <text> --json --session-key <key> --timeout <seconds>
```

OpenClaw help confirms:

- `openclaw agent` runs one agent turn via the Gateway;
- `--message` provides the prompt;
- `--json` returns machine-readable output;
- `--session-id` or `--session-key` targets an explicit session;
- `--agent <id>` can select an agent;
- `--local` exists but requires provider keys in the shell.

OpenClaw also has:

- `openclaw sessions --json`
- `openclaw transcripts list/show/path`

The local OpenClaw state includes `~/.openclaw/tui/last-session.json`, with active session keys such as `agent:main:main` and `agent:crestodian:main`.

## Old OpenClaw Queue Research

The older Primordial research identified Zarathustra as OpenClaw and described a queue-based runtime:

- queue file: `~/.openclaw/workspace/out/console_queue.jsonl`
- state file: `~/.openclaw/workspace/out/console_queue_state.json`
- ledger file: `~/.openclaw/workspace/out/queue_ledger.jsonl`

That remains useful as historical provenance research, but the current local OpenClaw CLI exposes a higher-level `agent` command. For a practical v1 chamber, use the CLI agent turn instead of writing queue files directly.

## Architecture Options

### Option A: Tool-Like Chamber Command In Hermes

Add a deterministic Python module that:

1. accepts a message;
2. calls a local Hermes/Codex responder interface or records the current assistant response;
3. invokes `openclaw agent --json --session-key agent:main:primordial-chamber --message <message>`;
4. normalizes both outputs into `ChamberVoice`;
5. creates a `ChamberRecord`;
6. stores it through `PrimordialStore`.

Pros:

- direct, testable, simple;
- keeps the chamber record in Hermes;
- no UI needed;
- no OpenClaw internal imports.

Cons:

- needs a clear boundary for "Codex voice" because the current assistant turn is already happening outside a reusable `call_llm()` wrapper.

### Option B: Delegate-Based Chamber

Use Hermes delegation for one seat and OpenClaw CLI for the other.

Pros:

- reuses existing subagent machinery and ledger.

Cons:

- user asked specifically for "you & OpenClaw"; spawning a Hermes child agent is not exactly this current session;
- more moving parts than v1 requires.

### Option C: OpenClaw Queue Adapter

Write directly to OpenClaw queue/ledger files.

Pros:

- close to original Primordial OpenClaw integration.

Cons:

- bypasses the current supported CLI surface;
- higher risk of corrupting state;
- old queue paths may not match the current OpenClaw Gateway/session model.

## Recommended v1

Build a local `primordial_chamber` runner in Hermes, but keep it non-model-facing at first.

Practical first milestone:

- add chamber record helpers to `PrimordialHarness`;
- add an OpenClaw CLI adapter that can run one OpenClaw turn and normalize JSON output;
- add a "two-seat chamber" function that takes:
  - message;
  - Hermes/Codex voice text;
  - OpenClaw voice text or OpenClaw command output;
  - session metadata;
- persist the `ChamberRecord`.

This avoids trying to recursively call the current assistant from inside itself. The current Hermes/Codex voice can be passed in after the assistant produces it, or collected by a CLI command in a later pass.

Second milestone:

- expose a command that sends the message to OpenClaw immediately and emits a chamber prompt for the current Hermes/Codex session to answer;
- after the current answer exists, seal/store the full chamber.

## Data Contract

Record type:

```text
chamber_record
```

Voice names:

- `codex`
- `openclaw`

Each voice should include:

- `name`
- `stance`
- `summary`
- `source_refs`

Source refs:

- Codex voice: `hermes://session/{session_id}/message/{message_id}` when available; otherwise content hash ref.
- OpenClaw voice: `openclaw://session/{session_key}` plus content hash ref.

Typed absence:

- OpenClaw timeout -> voice summary `""`, summary state `unresolved` in metadata.
- OpenClaw missing JSON output -> `invalid`.
- OpenClaw command unavailable -> `not_invoked`.
- Codex voice not provided yet -> `not_generated`.

## Verification Needs

Tests should use a fake command runner, not call real OpenClaw.

Required tests:

- OpenClaw JSON output is parsed into a voice.
- OpenClaw command timeout/error becomes typed absence.
- Two voices create a valid `ChamberRecord`.
- Chamber record round-trips through `PrimordialStore`.
- No raw command stderr is persisted unless explicitly included as redacted metadata.

## Research Verdict

The chamber can be brought up in two careful steps:

1. Implement chamber persistence and an OpenClaw CLI adapter with fake-runner tests.
2. Add the interactive "one message, two sessions" workflow that sends the prompt to OpenClaw and stores the current Hermes/Codex voice once it exists.

Do not write directly to OpenClaw queue files in v1. Use `openclaw agent --json --session-key ... --message ...`.

---

# Codex Chamber Orchestrator Research

Date: 2026-06-01
Status: research for implementation

## Goal

Make Codex the primary chamber orchestrator for Hermes/Primordial:

- Codex owns the protocol and persistent chamber state.
- OpenClaw is a chamber seat invoked through the CLI adapter.
- Codex output can be provided explicitly by the current session or left as typed absence until finalized.
- Records use the existing `chamber_record` schema and `PrimordialStore`.

## Current Gap

The previous implementation added:

- OpenClaw CLI result normalization;
- `build_two_seat_chamber()`;
- `PrimordialHarness.record_chamber()`.

But there is not yet a single tool/entrypoint that an operator can run to:

1. send the message to OpenClaw;
2. assemble the two-seat chamber;
3. persist the record;
4. print the stored chamber path/JSON for inspection.

Without this orchestrator layer, the architecture exists as library pieces but is awkward to operate.

## Recommended Tool Shape

Add a small stdlib-only CLI:

```text
python3 scripts/primordial_chamber.py run --message "..." [--codex-text "..."]
```

Default behavior:

- calls `openclaw agent --json --session-key agent:main:primordial-chamber`;
- builds a chamber with:
  - `codex` voice = provided `--codex-text`, or typed `not_generated`;
  - `openclaw` voice = OpenClaw result, or typed failure;
- stores the chamber through `PrimordialHarness`;
- prints compact JSON with `record_type`, `record_path`, `openclaw.ok`, and voice states.

Why a script first:

- no plugin registration risk;
- no prompt/tool schema churn;
- easy to test with fake runner at module level;
- useful immediately from Codex terminal execution.

Later:

- expose as a Hermes slash command or built-in model tool after the protocol stabilizes.

## Data Flow

```text
user message
  -> Codex orchestrator
     -> OpenClaw CLI adapter
     -> Codex voice text/typed absence
     -> build_two_seat_chamber()
     -> PrimordialHarness.record_chamber()
     -> $HERMES_HOME/primordial/records.jsonl
```

## Failure Handling

- OpenClaw command missing -> `not_invoked`
- OpenClaw timeout/nonzero exit -> `unresolved`
- invalid OpenClaw JSON -> `invalid`
- missing Codex text -> `not_generated`

All failure states are part of the chamber metadata. The command should still emit a chamber record unless the local store itself fails.

## Verification

Tests should avoid live OpenClaw:

- fake OpenClaw runner returns successful JSON;
- orchestrator persists chamber record;
- missing Codex text is recorded as typed absence;
- OpenClaw failure still persists a chamber record;
- CLI argument parsing can run with fake orchestration only if needed; unit tests on the orchestrator are higher value than subprocessing the script.
