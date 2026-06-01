# Bugs and Iterations

## 2026-06-01 - Chamber Production Audit

Problem: The chamber workflow had passing unit tests but no written production-readiness audit after applying it against a live OpenClaw path.

Root cause: Fake-runner tests covered the structural protocol, but live OpenClaw Gateway readiness and operator ergonomics were not yet evaluated.

Fix: Ran the live chamber path, confirmed failure is captured as typed absence, and documented missing production work plus optimization order in `docs/primordial/chamber-production-audit.md`.

## 2026-06-01 - Production Chamber Workflow

Problem: The chamber orchestrator could write records but lacked production operator basics: stable IDs, pending/finalized lifecycle, list/show inspection, and documentation.

Root cause: The first orchestrator pass focused on one-shot recording rather than the full operational loop needed when Codex text is only available after OpenClaw has already answered.

Fix: Added chamber IDs/status, JSONL record update by id, start/finalize/list/show commands, operator docs, and tests for pending-to-sealed finalization.

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
