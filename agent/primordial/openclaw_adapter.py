"""OpenClaw CLI adapter for Primordial chamber runs."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Sequence

from .absence import AbsenceState

DEFAULT_OPENCLAW_SESSION_KEY = "agent:main:primordial-chamber"

CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class OpenClawAgentResult:
    """Normalized result from one ``openclaw agent`` turn."""

    ok: bool
    summary: str
    session_key: str
    session_id: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    absence_state: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def _first_text_value(data: dict[str, Any], keys: Sequence[str]) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def normalize_openclaw_json(
    data: dict[str, Any],
    *,
    session_key: str = DEFAULT_OPENCLAW_SESSION_KEY,
) -> OpenClawAgentResult:
    """Normalize known OpenClaw JSON output shapes into a chamber voice result."""

    summary = _first_text_value(
        data,
        (
            "reply",
            "response",
            "message",
            "content",
            "text",
            "final_response",
            "summary",
        ),
    )
    result = data.get("result")
    if not summary and isinstance(result, dict):
        summary = _first_text_value(
            result,
            (
                "reply",
                "response",
                "message",
                "content",
                "text",
                "final_response",
                "summary",
            ),
        )
    session_id = data.get("session_id") or data.get("sessionId")
    if not isinstance(session_id, str) and isinstance(result, dict):
        session_id = result.get("session_id") or result.get("sessionId")
    ok_value = data.get("ok", data.get("success", bool(summary)))
    ok = bool(ok_value) and bool(summary)
    return OpenClawAgentResult(
        ok=ok,
        summary=summary,
        session_key=session_key,
        session_id=session_id if isinstance(session_id, str) else None,
        raw=data,
        error=None if ok else "OpenClaw JSON output did not include reply text",
        absence_state=None if ok else AbsenceState.INVALID.value,
    )


def run_openclaw_agent(
    message: str,
    *,
    session_key: str = DEFAULT_OPENCLAW_SESSION_KEY,
    timeout_seconds: int = 600,
    openclaw_bin: str = "openclaw",
    runner: CommandRunner | None = None,
) -> OpenClawAgentResult:
    """Run one OpenClaw agent turn and normalize its JSON output."""

    command = [
        openclaw_bin,
        "agent",
        "--json",
        "--session-key",
        session_key,
        "--timeout",
        str(int(timeout_seconds)),
        "--message",
        message,
    ]
    run = runner or subprocess.run
    try:
        completed = run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds + 5,
            check=False,
        )
    except FileNotFoundError as exc:
        return OpenClawAgentResult(
            ok=False,
            summary="",
            session_key=session_key,
            error=str(exc),
            absence_state=AbsenceState.NOT_INVOKED.value,
        )
    except subprocess.TimeoutExpired as exc:
        return OpenClawAgentResult(
            ok=False,
            summary="",
            session_key=session_key,
            error=str(exc),
            absence_state=AbsenceState.UNRESOLVED.value,
        )

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if completed.returncode != 0:
        return OpenClawAgentResult(
            ok=False,
            summary="",
            session_key=session_key,
            error=(stderr.strip() or stdout.strip() or f"openclaw exited {completed.returncode}")[:500],
            absence_state=AbsenceState.UNRESOLVED.value,
        )

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        return OpenClawAgentResult(
            ok=False,
            summary="",
            session_key=session_key,
            error=f"invalid JSON: {exc}",
            absence_state=AbsenceState.INVALID.value,
        )
    if not isinstance(data, dict):
        return OpenClawAgentResult(
            ok=False,
            summary="",
            session_key=session_key,
            raw={"value": data},
            error="OpenClaw JSON output was not an object",
            absence_state=AbsenceState.INVALID.value,
        )
    return normalize_openclaw_json(data, session_key=session_key)
