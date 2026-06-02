# Primordial Chamber

Primordial Chamber is a local CLI council orchestrator. It adapts Karpathy's
`llm-council` pattern to local agent seats instead of API-only model calls.

The chamber runs:

```text
Stage 1: independent first opinions
Stage 2: anonymized peer review and ranking
Stage 3: chairman synthesis
```

It persists typed absence, source refs, hashes, and staged records so failed
seats do not disappear silently.

## Install

```bash
pip install -e .
```

## Run

```bash
python3 scripts/primordial_chamber.py council run \
  --message "What should we build next?" \
  --codex-text "Codex first opinion" \
  --chairman-text "Chairman synthesis"
```

Show the latest staged council:

```bash
python3 scripts/primordial_chamber.py council show --latest --compact
```

Records are written to `~/.primordial-chamber/records.jsonl` by default. Set
`PRIMORDIAL_CHAMBER_HOME` to override the data directory.

## Seats

Current seat adapters:

- static text seats for Codex/Hermes handoff;
- OpenClaw via `openclaw agent --json`;
- generic CLI seats;
- placeholders for future adapters.

The chamber can still run the original two-seat Codex/OpenClaw workflow, but
the staged council mode is the primary project direction.
