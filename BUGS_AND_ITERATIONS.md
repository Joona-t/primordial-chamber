# Bugs and Iterations

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
