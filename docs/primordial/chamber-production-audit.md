# Primordial Chamber Production Audit

Date: 2026-06-01
Status: current-state audit after live smoke test

## Current Production Surface

Implemented:

- Codex-owned chamber orchestrator.
- OpenClaw CLI adapter through `openclaw agent --json`.
- Two-seat chamber records with `codex` and `openclaw` voices.
- Stable chamber ids.
- `pending` and `sealed` lifecycle states.
- `start`, `finalize`, `list`, `show`, and one-shot `run` CLI commands.
- JSONL persistence at `$HERMES_HOME/primordial/records.jsonl`.
- Typed absence for missing Codex text and OpenClaw failures.
- Unit coverage with fake OpenClaw runners.
- Delegation regression tests after integration.

Live smoke result:

- Command path executed and wrote a chamber record.
- OpenClaw did not produce a valid seat response.
- Recorded OpenClaw state: `unresolved`.
- Root symptom: OpenClaw Gateway websocket closed with code `1006` on `ws://127.0.0.1:18789`.
- The chamber behaved correctly by preserving the failure instead of crashing.

## Missing For Production Readiness

1. OpenClaw health preflight.

The chamber should check OpenClaw Gateway readiness before running the seat. Current behavior records a failure only after attempting the turn.

Needed:

- `openclaw health --json` or equivalent preflight.
- Clear distinction between gateway unavailable, model failure, timeout, and invalid response.
- Operator-facing remediation in CLI output.

2. Live integration test mode.

Current tests use fake runners, which is correct for CI. Production also needs an opt-in live smoke test:

```bash
python3 scripts/primordial_chamber.py smoke --live
```

This should be skipped by default and only run when OpenClaw is configured.

3. Record schema version.

Chamber records need an explicit schema version so future changes can migrate safely.

Needed fields:

- `schema_version`
- `record_kind`
- `created_by`
- `orchestrator_version`

4. Redaction policy.

OpenClaw errors are currently truncated, but stderr/stdout policy is informal.

Needed:

- maximum captured error bytes;
- explicit redaction of paths/secrets/tokens where possible;
- tests for truncation and redaction.

5. Atomic concurrency guard.

`PrimordialStore.update_payload_by_id()` rewrites JSONL. This is acceptable for single-operator use but not multi-process production.

Needed:

- file lock around rewrite;
- or move chamber index/update records to append-only events:
  - `chamber_started`
  - `chamber_finalized`
  - `chamber_failed`

Recommendation: keep JSONL append-only long-term and model finalization as a new event rather than replacing records.

6. Chamber comparison.

The current chamber stores voices but does not compare them.

Needed:

- deterministic diff summary:
  - agreement points;
  - conflicts;
  - missing claims;
  - unverifiable claims;
  - recommended next check.

7. Claude orchestrator fork compatibility.

The Claude fork should emit the same chamber schema. Do not let it invent its own ledger format.

Needed:

- schema fixture JSON;
- compatibility tests that load both Codex and Claude records.

8. Source refs for real Hermes message ids.

Current Codex refs are content refs or session-level pseudo refs. Production should bind Codex voice to a concrete Hermes session/message id when possible.

Needed:

- CLI option or runtime integration to pass `message_id`;
- source ref kind `session_message`.

9. CI placement.

The Primordial tests should be included in CI for the fork.

Needed:

```bash
pytest tests/agent/primordial -o 'addopts=' -q
```

Optional broader gate:

```bash
pytest tests/agent/primordial tests/tools/test_delegate_artifacts.py -o 'addopts=' -q
```

## Optimization Opportunities

1. Lazy OpenClaw parsing.

Normalize OpenClaw JSON with a table of known response paths instead of repeated key scans.

2. Event-sourced chamber store.

Replace in-place JSONL rewrite with append-only lifecycle events. This preserves audit history and avoids race-prone updates.

3. Compact show output.

Add:

```bash
python3 scripts/primordial_chamber.py show --latest --compact
```

This should print id, status, question, voice summaries, and absence states without full refs.

4. Health-aware retries.

Retry OpenClaw only when failure class is transient:

- gateway not ready;
- websocket closed before response;
- timeout before model request.

Do not retry invalid JSON unless OpenClaw version changed or parser changed.

5. Chamber seat registry.

Move hard-coded `codex` and `openclaw` into a small registry:

- seat id;
- display name;
- invocation adapter;
- source-ref builder;
- absence mapping.

This prepares for Claude without changing the core chamber runner.

## Recommended Next Implementation Order

1. Add OpenClaw health preflight and clearer failure classes.
2. Change finalization to append-only event records instead of JSONL rewrite.
3. Add compact show output.
4. Add schema version and fixture tests.
5. Add seat registry for Claude compatibility.
6. Add chamber comparison command.

## Verdict

The chamber is operational as a v1 auditable workflow. It is not yet production-grade for unattended orchestration because OpenClaw readiness, append-only lifecycle events, schema versioning, and live smoke coverage are missing.

The highest-leverage next fix is OpenClaw health preflight plus clearer failure classes, because the first live application already exposed Gateway readiness as the weak link.
