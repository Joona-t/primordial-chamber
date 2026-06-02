# LLM Council Adaptation For Primordial Chamber

Date: 2026-06-02
Status: implemented

## Source Architecture

Karpathy's `llm-council` uses a three-stage council:

1. **First opinions**: send the user query to multiple LLMs independently.
2. **Review**: anonymize the responses and ask each model to evaluate/rank the others.
3. **Final response**: a designated chairman model synthesizes the responses and rankings.

The repo implements this with OpenRouter API calls, FastAPI, JSON file storage, and a React UI.

Primary source:

- `karpathy/llm-council` README: https://github.com/karpathy/llm-council
- `backend/council.py`: https://github.com/karpathy/llm-council/blob/master/backend/council.py

## Key Architecture To Preserve

The important part is not OpenRouter or the web UI. The durable architecture is:

```text
Stage 1: independent answers
Stage 2: anonymized peer review
Stage 3: chairman synthesis
```

This maps directly onto Primordial chambers.

## Difference From Current Chamber

Current Primordial chamber:

```text
message -> Codex voice + OpenClaw voice -> chamber_record
```

Council-adapted chamber:

```text
message
  -> Stage 1: collect independent CLI seat answers
  -> Stage 2: ask each seat to review anonymized answers
  -> Stage 3: Codex chairman synthesizes
  -> Persist complete chamber record with stages, refs, rankings, absence states
```

## Why CLI Seats Are Better For Our System

We do not need the OpenRouter API layer. Our seats are already local/CLI-backed:

- Codex / Hermes
- OpenClaw
- Claude fork
- future local agents

Each seat should implement one interface:

```text
run_seat(prompt, session_key, timeout) -> SeatResult
```

The chamber orchestrator should not care whether the seat is OpenClaw, Claude, Codex, or another CLI.

## Primordial Improvements Over LLM Council

Karpathy's repo demonstrates the working social architecture, but Primordial adds reliability:

- typed absence when a seat fails;
- source refs for every answer and review;
- sealed chamber lifecycle;
- hashable evidence;
- append-only audit trail;
- ability to compare agent harnesses;
- no silent dropped responses.

In council terms:

```text
LLM Council = deliberation pattern
Primordial = deliberation pattern + provenance + failure semantics + auditability
```

## Proposed Chamber Schema Extension

Current `chamber_record` should grow from two voices into staged council data.

Recommended fields:

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

Stage 1 seat result:

```json
{
  "seat_id": "openclaw",
  "label": "Response A",
  "summary": "...",
  "summary_state": null,
  "source_refs": []
}
```

Stage 2 review result:

```json
{
  "reviewer_seat_id": "codex",
  "ranking": ["Response B", "Response A"],
  "review_text": "...",
  "source_refs": []
}
```

Stage 3 synthesis:

```json
{
  "chairman_seat_id": "codex",
  "summary": "...",
  "source_refs": []
}
```

## Implementation Plan

### Phase 1: Seat Registry

- [x] Add `primordial_chamber/seats.py`.
- [ ] Define `SeatSpec`.
- [ ] Define `SeatResult`.
- [ ] Move OpenClaw invocation behind seat adapter interface.
- [ ] Add Codex/Claude placeholders as CLI adapters, not hard dependencies.

### Phase 2: Council Runner

- [x] Add `primordial_chamber/council_runner.py`.
- [ ] Implement Stage 1 first-opinion collection.
- [ ] Implement anonymous labels: `Response A`, `Response B`, ...
- [ ] Implement Stage 2 review prompt builder.
- [ ] Implement Stage 2 ranking parser based on Karpathy's `FINAL RANKING:` pattern.
- [ ] Implement Stage 3 chairman synthesis prompt builder.

### Phase 3: Primordial Persistence

- [ ] Add schema version `2`.
- [ ] Store staged council records as `council_chamber_record`.
- [ ] Preserve typed absence for every failed seat/review/synthesis.
- [ ] Preserve source refs for every stage.
- [ ] Keep old `chamber_record` compatibility.

### Phase 4: CLI

Extend:

```bash
python3 scripts/primordial_chamber.py council run --message "..."
python3 scripts/primordial_chamber.py council show --latest --compact
```

### Phase 5: Tests

- [ ] Fake two-seat Stage 1 success.
- [ ] One seat failure produces typed absence.
- [ ] Review labels are anonymized.
- [ ] Ranking parser handles valid `FINAL RANKING:`.
- [ ] Chairman synthesis persists refs to Stage 1 and Stage 2.
- [ ] No response disappears silently.

## Design Decision

Use Karpathy's architecture, not his transport.

```text
Keep: Stage 1 / Stage 2 / Stage 3 council pattern.
Replace: OpenRouter API calls with local CLI seat adapters.
Enhance: Primordial provenance, typed absence, sealed records.
```

## Implemented Surface

- `primordial_chamber/seats.py`: local static, CLI, OpenClaw, and placeholder seats.
- `primordial_chamber/council_runner.py`: Stage 1 first opinions, Stage 2 anonymized review/ranking, Stage 3 chairman synthesis.
- `PrimordialHarness.record_council_chamber()`: persists `council_chamber_record`.
- `scripts/primordial_chamber.py council run/show`: operator CLI.
- `tests/test_seats.py`
- `tests/test_council_runner.py`

## Next Optimization

Add a real Codex/Hermes self-seat adapter once the host runtime exposes a safe way to invoke the current harness as a subprocess or queued session. Until then, Codex/Hermes text is supplied explicitly with `--codex-text`, and live OpenClaw can be included with `--include-openclaw`.
