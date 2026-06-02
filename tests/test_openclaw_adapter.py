import json
import subprocess

from primordial_chamber.openclaw_adapter import (
    DEFAULT_OPENCLAW_SESSION_KEY,
    normalize_openclaw_json,
    run_openclaw_agent,
)


def test_normalize_openclaw_json_extracts_reply():
    result = normalize_openclaw_json(
        {"ok": True, "reply": "OpenClaw answer", "sessionId": "abc"},
        session_key="agent:main:test",
    )

    assert result.ok is True
    assert result.summary == "OpenClaw answer"
    assert result.session_id == "abc"
    assert result.session_key == "agent:main:test"


def test_run_openclaw_agent_uses_json_and_session_key():
    calls = []

    def fake_runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"ok": True, "reply": "done"}),
            stderr="",
        )

    result = run_openclaw_agent("hello", runner=fake_runner, timeout_seconds=12)

    command, kwargs = calls[0]
    assert command[:3] == ["openclaw", "agent", "--json"]
    assert DEFAULT_OPENCLAW_SESSION_KEY in command
    assert "--message" in command
    assert kwargs["timeout"] == 17
    assert result.ok is True
    assert result.summary == "done"


def test_run_openclaw_agent_nonzero_exit_becomes_unresolved():
    def fake_runner(command, **_kwargs):
        return subprocess.CompletedProcess(command, 2, stdout="", stderr="gateway down")

    result = run_openclaw_agent("hello", runner=fake_runner)

    assert result.ok is False
    assert result.summary == ""
    assert result.absence_state == "unresolved"
    assert "gateway down" in result.error


def test_run_openclaw_agent_invalid_json_becomes_invalid():
    def fake_runner(command, **_kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="not json", stderr="")

    result = run_openclaw_agent("hello", runner=fake_runner)

    assert result.ok is False
    assert result.absence_state == "invalid"


def test_run_openclaw_agent_timeout_becomes_unresolved():
    def fake_runner(_command, **_kwargs):
        raise subprocess.TimeoutExpired(cmd="openclaw", timeout=1)

    result = run_openclaw_agent("hello", runner=fake_runner, timeout_seconds=1)

    assert result.ok is False
    assert result.absence_state == "unresolved"
