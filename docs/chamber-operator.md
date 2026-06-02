# Primordial Chamber Operator Guide

## Purpose

The Primordial chamber records one prompt across independent seats and stores the result in an append-only ledger.

Current production path:

- Codex is the orchestrator.
- OpenClaw is invoked through `openclaw agent --json`.
- Codex voice text is either provided immediately or finalized later.
- Records are stored in `$PRIMORDIAL_CHAMBER_HOME/records.jsonl` or
  `~/.primordial-chamber/records.jsonl`.

## Commands

Run and seal in one command:

```bash
python3 scripts/primordial_chamber.py run \
  --message "Question or task" \
  --codex-text "Codex voice"
```

Start a chamber with Codex pending:

```bash
python3 scripts/primordial_chamber.py start \
  --message "Question or task"
```

Finalize a pending chamber:

```bash
python3 scripts/primordial_chamber.py finalize \
  --id "chamber:..." \
  --codex-text "Codex final voice"
```

List chambers:

```bash
python3 scripts/primordial_chamber.py list --limit 20
```

Show a chamber:

```bash
python3 scripts/primordial_chamber.py show --latest
python3 scripts/primordial_chamber.py show --id "chamber:..."
```

## OpenClaw Target

Default session key:

```text
agent:main:primordial-chamber
```

Override it with:

```bash
--openclaw-session-key agent:main:other-key
```

## Absence States

- `not_generated`: Codex voice has not been attached yet.
- `not_invoked`: OpenClaw command was unavailable.
- `unresolved`: OpenClaw timed out or returned a nonzero exit.
- `invalid`: OpenClaw returned invalid JSON or no reply text.

## Production Notes

The chamber verifies structure and provenance, not semantic truth. Treat hashes, refs, and absence states as audit evidence. Use tests, diffs, and external checks for correctness.
