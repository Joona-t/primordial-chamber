from agent.primordial.harness import (
    PrimordialHarness,
    classify_summary_absence,
    record_delegation_safely,
)
from agent.primordial.store import PrimordialStore


def test_record_delegation_with_summary_and_artifacts(tmp_path):
    store = PrimordialStore(tmp_path / "records.jsonl")
    harness = PrimordialHarness(store)

    record = harness.record_delegation(
        parent_session_id="session-1",
        child_result={
            "task_index": 2,
            "status": "completed",
            "summary": "Built the artifact.",
            "model": "test-model",
            "tokens": {"input": 10, "output": 5},
            "_child_cost_usd": 0.01,
            "duration_seconds": 1.5,
        },
        verified_artifacts={
            "verified": [{"path": "/tmp/out.txt", "bytes": 4, "sha256": "abcd"}],
            "rejected": [],
        },
        metadata={"role": "worker"},
    )

    payload = record["payload"]
    assert record["type"] == "delegation_result"
    assert payload["parent_session_id"] == "session-1"
    assert payload["summary"] == "Built the artifact."
    assert "summary_state" not in payload
    assert payload["artifacts"]["verified"][0]["sha256"] == "abcd"
    assert payload["source_refs"][0]["kind"] == "delegate_run"
    assert store.list_records()[0]["payload"]["metadata"]["role"] == "worker"


def test_record_delegation_without_summary_uses_typed_absence(tmp_path):
    harness = PrimordialHarness(PrimordialStore(tmp_path / "records.jsonl"))

    record = harness.record_delegation(
        parent_session_id="session-1",
        child_result={
            "task_index": 0,
            "status": "timeout",
            "summary": "",
            "duration_seconds": 30,
        },
    )

    payload = record["payload"]
    assert payload["summary"] == ""
    assert payload["summary_state"] == "unresolved"


def test_record_delegation_keeps_rejected_artifacts_visible(tmp_path):
    harness = PrimordialHarness(PrimordialStore(tmp_path / "records.jsonl"))

    record = harness.record_delegation(
        parent_session_id="session-1",
        child_result={"task_index": 1, "status": "completed", "summary": "done"},
        verified_artifacts={
            "verified": [],
            "rejected": [{"path": "/tmp/missing.txt", "reason": "missing"}],
        },
    )

    rejected = record["payload"]["artifacts"]["rejected"]
    assert rejected == [{"path": "/tmp/missing.txt", "reason": "missing"}]


def test_record_delegation_round_trips_through_store(tmp_path):
    store = PrimordialStore(tmp_path / "records.jsonl")
    harness = PrimordialHarness(store)

    harness.record_delegation(
        parent_session_id="session-1",
        child_result={"task_index": 0, "status": "completed", "summary": "done"},
    )

    records = store.list_records(record_type="delegation_result")
    assert len(records) == 1
    assert records[0]["payload"]["source_refs"]


def test_summary_absence_classification():
    assert classify_summary_absence("completed", "done") is None
    assert classify_summary_absence("completed", "") == "not_generated"
    assert classify_summary_absence("interrupted", "") == "unresolved"
    assert classify_summary_absence("failed", None) == "unresolved"


def test_record_delegation_safely_swallows_store_failure():
    class BrokenHarness:
        def record_delegation(self, **_kwargs):
            raise RuntimeError("boom")

    result = record_delegation_safely(
        parent_session_id="session-1",
        child_result={"task_index": 0, "status": "completed", "summary": "done"},
        harness=BrokenHarness(),
    )

    assert result is None
