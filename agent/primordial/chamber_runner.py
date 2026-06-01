"""Two-seat Primordial chamber construction helpers."""

from __future__ import annotations

from typing import Any, Mapping

from .absence import AbsenceState
from .chamber import ChamberRecord, ChamberVoice
from .openclaw_adapter import OpenClawAgentResult
from .refs import content_ref
from .summary import ReversibleSummary


def _voice_ref(name: str, text: str, *, uri: str | None = None) -> dict[str, Any]:
    ref = content_ref(text or f"{name}:absent", kind=f"{name}_voice", label=name).to_dict()
    if uri:
        ref["uri"] = uri
    return ref


def build_two_seat_chamber(
    *,
    message: str,
    codex_text: str | None,
    openclaw_result: OpenClawAgentResult,
    hermes_session_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> ChamberRecord:
    """Build a chamber record for one message answered by Codex and OpenClaw."""

    codex_summary = codex_text.strip() if isinstance(codex_text, str) else ""
    codex_ref = _voice_ref(
        "codex",
        codex_summary,
        uri=(
            f"hermes://session/{hermes_session_id}/voice/codex"
            if hermes_session_id
            else None
        ),
    )
    openclaw_summary = openclaw_result.summary.strip()
    openclaw_ref = _voice_ref(
        "openclaw",
        openclaw_summary,
        uri=f"openclaw://session/{openclaw_result.session_key}",
    )
    voices = [
        ChamberVoice(
            name="codex",
            stance="Hermes/Codex current-session voice",
            summary=codex_summary,
            source_refs=[codex_ref],
        ),
        ChamberVoice(
            name="openclaw",
            stance="OpenClaw Gateway agent voice",
            summary=openclaw_summary,
            source_refs=[openclaw_ref],
        ),
    ]
    synthesis_text = "Two-seat chamber captured for the prompt."
    synthesis = ReversibleSummary.from_sources(
        synthesis_text,
        [codex_ref, openclaw_ref],
        fragments=[
            {"source_ref": codex_ref["id"], "voice": "codex"},
            {"source_ref": openclaw_ref["id"], "voice": "openclaw"},
        ],
    )
    chamber_metadata = dict(metadata or {})
    chamber_metadata.update(
        {
            "hermes_session_id": hermes_session_id or "",
            "openclaw": openclaw_result.to_dict(),
        }
    )
    if not codex_summary:
        chamber_metadata["codex_summary_state"] = AbsenceState.NOT_GENERATED.value
    if openclaw_result.absence_state:
        chamber_metadata["openclaw_summary_state"] = openclaw_result.absence_state
    return ChamberRecord.create(
        question=message,
        voices=voices,
        synthesis=synthesis,
        metadata=chamber_metadata,
    )
