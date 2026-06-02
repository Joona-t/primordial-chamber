from agent.primordial.council_runner import CouncilRunner, build_review_prompt, parse_final_ranking
from agent.primordial.harness import PrimordialHarness
from agent.primordial.seats import SeatResult, SeatSpec
from agent.primordial.store import PrimordialStore


def _fake_seat(seat_id: str, first_text: str) -> SeatSpec:
    def runner(prompt: str, spec: SeatSpec) -> SeatResult:
        if "Final synthesis:" in prompt:
            return SeatResult(seat_id=spec.seat_id, ok=True, text="Chairman synthesis")
        if "FINAL RANKING" in prompt:
            return SeatResult(
                seat_id=spec.seat_id,
                ok=True,
                text="Review looks sound.\nFINAL RANKING: Response B, Response A",
            )
        return SeatResult(seat_id=spec.seat_id, ok=True, text=first_text)

    return SeatSpec(seat_id=seat_id, kind="fake", runner=runner)


def test_parse_final_ranking_handles_valid_line():
    ranking = parse_final_ranking(
        "Notes.\nFINAL RANKING: Response B, Response A",
        ["Response A", "Response B"],
    )

    assert ranking == ["Response B", "Response A"]


def test_review_prompt_anonymizes_labels():
    prompt = build_review_prompt(
        "Question",
        [
            {"seat_id": "codex", "label": "Response A", "summary": "A"},
            {"seat_id": "openclaw", "label": "Response B", "summary": "B"},
        ],
    )

    assert "Response A:" in prompt
    assert "Response B:" in prompt
    assert "codex" not in prompt
    assert "openclaw" not in prompt


def test_council_runner_records_two_successful_seats():
    runner = CouncilRunner(
        [_fake_seat("codex", "Codex first"), _fake_seat("openclaw", "OpenClaw first")],
        chairman_seat_id="codex",
    )

    result = runner.run("Decide")
    payload = result.record

    assert payload["schema_version"] == 2
    assert payload["status"] == "sealed"
    assert payload["stages"]["stage1_first_opinions"][0]["label"] == "Response A"
    assert payload["stages"]["stage1_first_opinions"][1]["label"] == "Response B"
    assert payload["stages"]["stage2_peer_reviews"][0]["ranking"] == ["Response B", "Response A"]
    assert payload["stages"]["stage3_chairman_synthesis"]["summary"] == "Chairman synthesis"
    assert payload["source_refs"]


def test_council_runner_preserves_failed_seat_absence():
    def broken_runner(_prompt: str, spec: SeatSpec) -> SeatResult:
        return SeatResult(
            seat_id=spec.seat_id,
            ok=False,
            error="down",
            absence_state="unresolved",
        )

    runner = CouncilRunner(
        [_fake_seat("codex", "Codex first"), SeatSpec(seat_id="openclaw", kind="fake", runner=broken_runner)],
        chairman_seat_id="codex",
    )

    result = runner.run("Decide")
    failed = result.record["stages"]["stage1_first_opinions"][1]

    assert failed["summary"] == ""
    assert failed["summary_state"] == "unresolved"
    assert failed["error"] == "down"


def test_record_council_chamber_round_trips(tmp_path):
    store = PrimordialStore(tmp_path / "records.jsonl")
    harness = PrimordialHarness(store)
    runner = CouncilRunner([_fake_seat("codex", "Codex first")], chairman_seat_id="codex")

    record = harness.record_council_chamber(runner.run("Decide").record)

    assert record["type"] == "council_chamber_record"
    assert store.list_records(record_type="council_chamber_record")[0]["payload"]["question"] == "Decide"


def test_chairman_override_does_not_join_stage1():
    runner = CouncilRunner(
        [_fake_seat("codex", "Codex first")],
        chairman_seat_id="chairman",
        chairman_seat=_fake_seat("chairman", "Chairman first"),
    )

    payload = runner.run("Decide").record

    assert len(payload["stages"]["stage1_first_opinions"]) == 1
    assert payload["stages"]["stage1_first_opinions"][0]["seat_id"] == "codex"
    assert payload["stages"]["stage3_chairman_synthesis"]["chairman_seat_id"] == "chairman"
