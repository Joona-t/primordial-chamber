from primordial_chamber.refs import content_ref, file_ref
from primordial_chamber.summary import ReversibleSummary
from primordial_chamber.chamber import ChamberRecord, ChamberVoice
from primordial_chamber.store import PrimordialStore


def test_content_ref_is_stable():
    a = content_ref("same text", label="note")
    b = content_ref("same text", label="note")

    assert a.id == b.id
    assert a.sha256 == b.sha256
    assert a.to_dict()["label"] == "note"


def test_file_ref_hashes_file(tmp_path):
    path = tmp_path / "artifact.txt"
    path.write_text("artifact", encoding="utf-8")

    ref = file_ref(path)

    assert ref.kind == "file"
    assert ref.uri == str(path.resolve())
    assert ref.bytes == len("artifact")


def test_reversible_summary_requires_provenance():
    ref = content_ref("source")
    summary = ReversibleSummary.from_sources(
        "short",
        [ref],
        fragments=[{"source_ref": ref.id, "quote": "source"}],
    )

    assert summary.expand()["source_refs"][0]["id"] == ref.id
    assert summary.to_dict()["fragments"][0]["quote"] == "source"


def test_chamber_record_normalizes_voice_dicts():
    ref = content_ref("source")
    synthesis = ReversibleSummary.from_sources("decision", [ref])

    record = ChamberRecord.create(
        question="What should we build?",
        voices=[{"name": "Carmack", "stance": "systems", "summary": "measure"}],
        synthesis=synthesis,
    )

    data = record.to_dict()
    assert data["voices"][0]["name"] == "Carmack"
    assert data["synthesis"]["summary"] == "decision"


def test_store_appends_and_filters(tmp_path):
    store = PrimordialStore(tmp_path / "records.jsonl")
    ref = content_ref("source")

    store.append("summary", ReversibleSummary.from_sources("short", [ref]).to_dict())
    store.append("note", {"source_refs": []})

    assert len(store.list_records()) == 2
    summaries = store.list_records(record_type="summary")
    assert len(summaries) == 1
    assert summaries[0]["payload"]["summary"] == "short"


def test_store_updates_payload_by_id(tmp_path):
    store = PrimordialStore(tmp_path / "records.jsonl")
    store.append("chamber_record", {"id": "chamber:1", "summary": "old"})

    updated = store.update_payload_by_id(
        "chamber_record",
        "chamber:1",
        {"id": "chamber:1", "summary": "new"},
    )

    assert updated["payload"]["summary"] == "new"
    assert store.find_by_id("chamber_record", "chamber:1")["payload"]["summary"] == "new"
    assert len(store.list_records(record_type="chamber_record")) == 1
