import json
import subprocess

from agent.primordial.harness import PrimordialHarness
from agent.primordial.orchestrator import CodexChamberOrchestrator
from agent.primordial.store import PrimordialStore


def test_orchestrator_records_successful_two_seat_chamber(tmp_path):
    store = PrimordialStore(tmp_path / "records.jsonl")
    orchestrator = CodexChamberOrchestrator(PrimordialHarness(store))

    def fake_runner(command, **_kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"ok": True, "reply": "OpenClaw voice"}),
            stderr="",
        )

    result = orchestrator.run_two_seat_chamber(
        message="Decide",
        codex_text="Codex voice",
        hermes_session_id="h1",
        runner=fake_runner,
    )

    assert result.openclaw.ok is True
    assert result.codex_summary_state is None
    assert result.record_path == str(tmp_path / "records.jsonl")
    records = store.list_records(record_type="chamber_record")
    assert records[0]["payload"]["voices"][0]["summary"] == "Codex voice"
    assert records[0]["payload"]["voices"][1]["summary"] == "OpenClaw voice"


def test_orchestrator_marks_missing_codex_text(tmp_path):
    store = PrimordialStore(tmp_path / "records.jsonl")
    orchestrator = CodexChamberOrchestrator(PrimordialHarness(store))

    def fake_runner(command, **_kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"ok": True, "reply": "OpenClaw voice"}),
            stderr="",
        )

    result = orchestrator.run_two_seat_chamber(message="Decide", runner=fake_runner)

    assert result.codex_summary_state == "not_generated"
    payload = result.record["payload"]
    assert payload["metadata"]["codex_summary_state"] == "not_generated"


def test_orchestrator_records_openclaw_failure(tmp_path):
    store = PrimordialStore(tmp_path / "records.jsonl")
    orchestrator = CodexChamberOrchestrator(PrimordialHarness(store))

    def fake_runner(command, **_kwargs):
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="down")

    result = orchestrator.run_two_seat_chamber(
        message="Decide",
        codex_text="Codex voice",
        runner=fake_runner,
    )

    assert result.openclaw.ok is False
    payload = result.record["payload"]
    assert payload["metadata"]["openclaw_summary_state"] == "unresolved"
    assert store.list_records(record_type="chamber_record")
