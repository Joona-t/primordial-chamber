import hashlib
from unittest.mock import MagicMock

from tools.delegate_tool import _run_single_child, _verify_artifact_paths


def test_verify_artifact_paths_hashes_existing_files(tmp_path):
    artifact = tmp_path / "out.txt"
    artifact.write_text("deliverable", encoding="utf-8")

    result = _verify_artifact_paths([str(artifact)], allowed_paths=[str(artifact)])

    assert result["rejected"] == []
    assert result["verified"][0]["path"] == str(artifact.resolve())
    assert result["verified"][0]["bytes"] == len("deliverable")
    assert result["verified"][0]["sha256"] == hashlib.sha256(b"deliverable").hexdigest()


def test_verify_artifact_paths_rejects_missing_and_unclaimed(tmp_path):
    claimed = tmp_path / "claimed.txt"
    unclaimed = tmp_path / "unclaimed.txt"
    claimed.write_text("ok", encoding="utf-8")
    unclaimed.write_text("no", encoding="utf-8")

    result = _verify_artifact_paths(
        [str(claimed), str(unclaimed), str(tmp_path / "missing.txt")],
        allowed_paths=[str(claimed), str(tmp_path / "missing.txt")],
    )

    reasons = {item["reason"] for item in result["rejected"]}
    assert "not_child_written" in reasons
    assert "missing" in reasons
    assert len(result["verified"]) == 1


def test_run_single_child_returns_verified_written_artifacts(tmp_path, monkeypatch):
    artifact = tmp_path / "child.txt"
    artifact.write_text("child output", encoding="utf-8")

    child = MagicMock()
    child._subagent_id = "subagent-artifact-test"
    child._delegate_role = "leaf"
    child._delegate_depth = 1
    child._delegate_saved_tool_names = []
    child.model = "test-model"
    child.session_prompt_tokens = 0
    child.session_completion_tokens = 0
    child.session_estimated_cost_usd = 0.0
    child.run_conversation.return_value = {
        "final_response": "done",
        "completed": True,
        "interrupted": False,
        "api_calls": 1,
        "messages": [],
    }
    child.get_activity_summary.return_value = {
        "api_call_count": 1,
        "max_iterations": 1,
        "current_tool": None,
    }

    parent = MagicMock()
    parent._current_task_id = "parent-task"
    parent._active_children = [child]
    parent._active_children_lock = None

    monkeypatch.setattr("tools.delegate_tool.file_state.known_reads", lambda task_id: [])
    monkeypatch.setattr(
        "tools.delegate_tool.file_state.writes_since",
        lambda task_id, since, paths: {"subagent-artifact-test": [str(artifact)]},
    )

    result = _run_single_child(0, "make artifact", child, parent)

    assert result["status"] == "completed"
    assert result["artifacts"]["rejected"] == []
    assert result["artifacts"]["verified"][0]["path"] == str(artifact.resolve())
