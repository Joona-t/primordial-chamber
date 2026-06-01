from agent.primordial.chamber_runner import build_two_seat_chamber
from agent.primordial.harness import PrimordialHarness
from agent.primordial.openclaw_adapter import OpenClawAgentResult
from agent.primordial.store import PrimordialStore


def test_build_two_seat_chamber_creates_codex_and_openclaw_voices():
    chamber = build_two_seat_chamber(
        message="What should we build?",
        codex_text="Codex says measure first.",
        openclaw_result=OpenClawAgentResult(
            ok=True,
            summary="OpenClaw says ship a small runner.",
            session_key="agent:main:test",
            session_id="oc-1",
            raw={"reply": "OpenClaw says ship a small runner."},
        ),
        hermes_session_id="hermes-1",
    )

    data = chamber.to_dict()
    assert data["question"] == "What should we build?"
    assert [v["name"] for v in data["voices"]] == ["codex", "openclaw"]
    assert data["voices"][0]["source_refs"][0]["uri"] == "hermes://session/hermes-1/voice/codex"
    assert data["voices"][1]["source_refs"][0]["uri"] == "openclaw://session/agent:main:test"
    assert data["synthesis"]["source_refs"]


def test_build_two_seat_chamber_marks_absent_outputs():
    chamber = build_two_seat_chamber(
        message="Ping",
        codex_text=None,
        openclaw_result=OpenClawAgentResult(
            ok=False,
            summary="",
            session_key="agent:main:test",
            error="gateway down",
            absence_state="unresolved",
        ),
    )

    metadata = chamber.to_dict()["metadata"]
    assert metadata["codex_summary_state"] == "not_generated"
    assert metadata["openclaw_summary_state"] == "unresolved"


def test_chamber_record_round_trips_through_store(tmp_path):
    store = PrimordialStore(tmp_path / "records.jsonl")
    harness = PrimordialHarness(store)
    chamber = build_two_seat_chamber(
        message="Ping",
        codex_text="Codex",
        openclaw_result=OpenClawAgentResult(
            ok=True,
            summary="OpenClaw",
            session_key="agent:main:test",
        ),
    )

    record = harness.record_chamber(chamber)

    assert record["type"] == "chamber_record"
    records = store.list_records(record_type="chamber_record")
    assert len(records) == 1
    assert records[0]["payload"]["voices"][1]["name"] == "openclaw"
