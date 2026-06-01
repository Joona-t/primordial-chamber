# Bugs and Iterations

## 2026-06-01 - Codex Chamber Orchestrator Tool

Problem: The two-seat chamber existed as library pieces but did not have a Codex-owned orchestration entrypoint an operator could run.

Root cause: OpenClaw invocation, chamber construction, and persistence were separate primitives without a command-level workflow.

Fix: Added `CodexChamberOrchestrator`, a `scripts/primordial_chamber.py run` CLI, and fake-runner tests for success, missing Codex text, and OpenClaw failure.

## 2026-06-01 - Two-Seat Primordial Chamber

Problem: Hermes had chamber record primitives but no practical way to capture one message across both Codex and OpenClaw seats.

Root cause: The chamber type existed as storage-only structure; OpenClaw CLI normalization and chamber persistence helpers were missing.

Fix: Added an OpenClaw `agent --json` adapter, two-seat chamber builder, chamber persistence in `PrimordialHarness`, and fake-runner tests for success/error paths.

## 2026-06-01 - Primordial Delegation Harness

Problem: Subagent artifact verification existed only in the immediate delegation result, so Hermes had no persistent Primordial ledger for child outcomes.

Root cause: The initial forge-lite integration added primitives and artifact hashes but did not yet wire them to an append-only runtime recorder.

Fix: Added a passive `PrimordialHarness`, unit tests, and failure-safe delegation completion recording to `$HERMES_HOME/primordial/records.jsonl`.

## 2026-06-01 - Primordial Forge-Lite Integration

Problem: Hermes needed a deterministic way to preserve typed absence, source references, reversible summaries, chamber records, and verified subagent artifact metadata without importing the full Primordial research repo.

Root cause: The Primordial repo is a research blueprint, not a production dependency; Hermes needed the protocol kernel extracted at stable support-code boundaries.

Fix: Added `agent.primordial` primitives, append-only JSONL storage, focused tests, and a delegation artifact verification seam that records hashes for child-written files.

## 2026-05-27 - Codex Responses `NoneType` Iterable Crash

Problem: Hermes could surface `TypeError("'NoneType' object is not iterable")` during OpenAI Codex main turns and auxiliary title generation.

Root cause: Codex Responses streams can return `response.output = None`; main/fallback backfill only handled `[]`, and the auxiliary Codex adapter iterated `final.output` without first normalizing non-list values.

Fix: Treat `None` output as backfillable in main Codex stream paths, normalize auxiliary output before iteration, and add regression tests for `output is None`.
