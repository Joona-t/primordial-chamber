# Primordial Chamber Extraction Research

Date: 2026-06-02

## Finding

The chamber does not need the full Hermes source tree. The useful project
surface is the council protocol, seat adapters, typed absence primitives,
source refs, chamber records, JSONL persistence, and CLI.

## Source Modules

Extract from the Hermes prototype:

- `agent/primordial/*.py`
- `scripts/primordial_chamber.py`
- `tests/agent/primordial/test_*.py`
- `docs/primordial/*.md`

## Standalone Changes

- Rename package from `agent.primordial` to `primordial_chamber`.
- Replace `hermes_constants.get_hermes_home()` with
  `PRIMORDIAL_CHAMBER_HOME` / `~/.primordial-chamber`.
- Keep OpenClaw as an optional CLI seat.
- Keep Codex/Hermes as explicit text/static seat until a safe self-seat adapter
  exists.

## Verdict

The standalone repo should be the product. The Hermes fork should remain only
as a backup/source integration branch.
