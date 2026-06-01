"""Codex-owned orchestration for two-seat Primordial chambers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .chamber_runner import build_two_seat_chamber
from .harness import PrimordialHarness
from .openclaw_adapter import (
    DEFAULT_OPENCLAW_SESSION_KEY,
    CommandRunner,
    OpenClawAgentResult,
    run_openclaw_agent,
)


@dataclass(frozen=True)
class ChamberOrchestrationResult:
    """Compact result returned by the Codex chamber orchestrator."""

    record: dict[str, Any]
    openclaw: OpenClawAgentResult
    codex_summary_state: str | None = None
    record_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["openclaw"] = self.openclaw.to_dict()
        return {k: v for k, v in data.items() if v is not None}


class CodexChamberOrchestrator:
    """Owns the v1 chamber protocol: Codex as orchestrator, OpenClaw as seat."""

    def __init__(self, harness: PrimordialHarness | None = None):
        self.harness = harness or PrimordialHarness()

    def run_two_seat_chamber(
        self,
        *,
        message: str,
        codex_text: str | None = None,
        hermes_session_id: str | None = None,
        openclaw_session_key: str = DEFAULT_OPENCLAW_SESSION_KEY,
        timeout_seconds: int = 600,
        runner: CommandRunner | None = None,
        openclaw_bin: str = "openclaw",
    ) -> ChamberOrchestrationResult:
        """Run OpenClaw, build the chamber, persist it, and return metadata."""

        openclaw = run_openclaw_agent(
            message,
            session_key=openclaw_session_key,
            timeout_seconds=timeout_seconds,
            openclaw_bin=openclaw_bin,
            runner=runner,
        )
        chamber = build_two_seat_chamber(
            message=message,
            codex_text=codex_text,
            openclaw_result=openclaw,
            hermes_session_id=hermes_session_id,
            metadata={"orchestrator": "codex"},
        )
        record = self.harness.record_chamber(chamber)
        payload = record.get("payload", {}) if isinstance(record, dict) else {}
        metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
        record_path = str(getattr(self.harness.store, "path", "")) or None
        return ChamberOrchestrationResult(
            record=record,
            openclaw=openclaw,
            codex_summary_state=metadata.get("codex_summary_state"),
            record_path=record_path,
        )

    def start_chamber(
        self,
        *,
        message: str,
        hermes_session_id: str | None = None,
        openclaw_session_key: str = DEFAULT_OPENCLAW_SESSION_KEY,
        timeout_seconds: int = 600,
        runner: CommandRunner | None = None,
        openclaw_bin: str = "openclaw",
    ) -> ChamberOrchestrationResult:
        """Start a chamber by running OpenClaw and leaving Codex pending."""

        return self.run_two_seat_chamber(
            message=message,
            codex_text=None,
            hermes_session_id=hermes_session_id,
            openclaw_session_key=openclaw_session_key,
            timeout_seconds=timeout_seconds,
            runner=runner,
            openclaw_bin=openclaw_bin,
        )

    def finalize_chamber(
        self,
        *,
        chamber_id: str,
        codex_text: str,
    ) -> ChamberOrchestrationResult:
        """Attach Codex text to an existing pending chamber record."""

        existing = self.harness.store.find_by_id("chamber_record", chamber_id)
        if existing is None:
            raise KeyError(f"chamber not found: {chamber_id}")
        payload = existing.get("payload", {})
        if not isinstance(payload, dict):
            raise ValueError(f"invalid chamber payload for {chamber_id}")
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        openclaw_data = metadata.get("openclaw", {})
        if not isinstance(openclaw_data, dict):
            openclaw_data = {}
        openclaw = OpenClawAgentResult(
            ok=bool(openclaw_data.get("ok")),
            summary=str(openclaw_data.get("summary") or ""),
            session_key=str(openclaw_data.get("session_key") or DEFAULT_OPENCLAW_SESSION_KEY),
            session_id=(
                str(openclaw_data.get("session_id"))
                if openclaw_data.get("session_id") is not None
                else None
            ),
            raw=dict(openclaw_data.get("raw") or {}),
            error=(
                str(openclaw_data.get("error"))
                if openclaw_data.get("error") is not None
                else None
            ),
            absence_state=(
                str(openclaw_data.get("absence_state"))
                if openclaw_data.get("absence_state") is not None
                else None
            ),
        )
        chamber = build_two_seat_chamber(
            message=str(payload.get("question") or ""),
            codex_text=codex_text,
            openclaw_result=openclaw,
            hermes_session_id=str(metadata.get("hermes_session_id") or "") or None,
            metadata={"orchestrator": metadata.get("orchestrator", "codex")},
            chamber_id=chamber_id,
            status="sealed",
        )
        record = self.harness.update_chamber(chamber)
        record_path = str(getattr(self.harness.store, "path", "")) or None
        return ChamberOrchestrationResult(
            record=record,
            openclaw=openclaw,
            codex_summary_state=None,
            record_path=record_path,
        )

    def list_chambers(self, *, limit: int = 20) -> list[dict[str, Any]]:
        records = self.harness.store.list_records(record_type="chamber_record")
        out = []
        for record in records[-max(0, int(limit)):]:
            payload = record.get("payload", {})
            if not isinstance(payload, dict):
                continue
            metadata = payload.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}
            out.append(
                {
                    "id": payload.get("id") or metadata.get("id"),
                    "status": payload.get("status") or metadata.get("status"),
                    "question": payload.get("question"),
                    "created_at": payload.get("created_at"),
                    "voices": [v.get("name") for v in payload.get("voices", []) if isinstance(v, dict)],
                }
            )
        return out

    def show_chamber(self, *, chamber_id: str | None = None, latest: bool = False) -> dict[str, Any] | None:
        if latest:
            records = self.harness.store.list_records(record_type="chamber_record")
            return records[-1] if records else None
        if not chamber_id:
            raise ValueError("chamber_id is required unless latest=True")
        return self.harness.store.find_by_id("chamber_record", chamber_id)
