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
