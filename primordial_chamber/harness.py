"""Passive Primordial record harness for Hermes runtime boundaries."""

from __future__ import annotations

import logging
from typing import Any, Mapping

from .absence import AbsenceState
from .chamber import ChamberRecord
from .refs import content_ref
from .store import PrimordialStore

logger = logging.getLogger(__name__)


def _numeric(value: Any, default: float = 0.0) -> float:
    return float(value) if isinstance(value, (int, float)) else default


def classify_summary_absence(status: str, summary: Any) -> str | None:
    """Return the summary absence state, or None when summary text exists."""

    if isinstance(summary, str) and summary.strip():
        return None
    normalized = str(status or "").strip().lower()
    if normalized in {"timeout", "interrupted", "error", "failed"}:
        return AbsenceState.UNRESOLVED.value
    return AbsenceState.NOT_GENERATED.value


def delegation_source_refs(
    *,
    parent_session_id: str | None,
    task_index: int,
    summary: str,
) -> list[dict[str, Any]]:
    """Build compact source refs for a delegation result."""

    label = f"delegation:{parent_session_id or 'unknown'}:{task_index}"
    source_text = summary if summary.strip() else label
    ref = content_ref(source_text, kind="delegate_run", label=label).to_dict()
    ref["uri"] = f"hermes://delegate/{parent_session_id or 'unknown'}/{task_index}"
    return [ref]


class PrimordialHarness:
    """Append-only recorder for Primordial-compatible Hermes events."""

    def __init__(self, store: PrimordialStore | None = None):
        self.store = store or PrimordialStore()

    def record_delegation(
        self,
        *,
        parent_session_id: str | None,
        child_result: Mapping[str, Any],
        verified_artifacts: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist one normalized delegation result record."""

        task_index = int(child_result.get("task_index") or 0)
        status = str(child_result.get("status") or "unknown")
        summary = child_result.get("summary")
        summary_text = summary.strip() if isinstance(summary, str) else ""
        artifacts = dict(verified_artifacts or child_result.get("artifacts") or {})
        artifacts.setdefault("verified", [])
        artifacts.setdefault("rejected", [])

        payload: dict[str, Any] = {
            "parent_session_id": parent_session_id or "",
            "task_index": task_index,
            "status": status,
            "summary": summary_text,
            "artifacts": artifacts,
            "model": child_result.get("model"),
            "tokens": dict(child_result.get("tokens") or {}),
            "cost_usd": _numeric(child_result.get("_child_cost_usd", 0.0)),
            "duration_seconds": _numeric(child_result.get("duration_seconds", 0.0)),
            "source_refs": delegation_source_refs(
                parent_session_id=parent_session_id,
                task_index=task_index,
                summary=summary_text,
            ),
            "metadata": dict(metadata or {}),
        }
        absence_state = classify_summary_absence(status, summary_text)
        if absence_state:
            payload["summary_state"] = absence_state
        return self.store.append("delegation_result", payload)

    def record_chamber(self, chamber: ChamberRecord) -> dict[str, Any]:
        """Persist one normalized chamber record."""

        payload = chamber.to_dict()
        metadata = payload.get("metadata", {})
        if isinstance(metadata, dict) and metadata.get("id"):
            payload["id"] = metadata["id"]
            payload["status"] = metadata.get("status", "")
        return self.store.append("chamber_record", payload)

    def update_chamber(self, chamber: ChamberRecord) -> dict[str, Any]:
        """Replace an existing chamber record by chamber id."""

        payload = chamber.to_dict()
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict) or not metadata.get("id"):
            raise ValueError("Chamber metadata.id is required for update")
        payload["id"] = metadata["id"]
        payload["status"] = metadata.get("status", "")
        return self.store.update_payload_by_id("chamber_record", metadata["id"], payload)

    def record_council_chamber(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Persist one staged council chamber record."""

        return self.store.append("council_chamber_record", dict(payload))


def record_delegation_safely(
    *,
    parent_session_id: str | None,
    child_result: Mapping[str, Any],
    verified_artifacts: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    harness: PrimordialHarness | None = None,
) -> dict[str, Any] | None:
    """Record delegation metadata without allowing recorder failures to leak."""

    try:
        return (harness or PrimordialHarness()).record_delegation(
            parent_session_id=parent_session_id,
            child_result=child_result,
            verified_artifacts=verified_artifacts,
            metadata=metadata,
        )
    except Exception:
        logger.debug("Primordial delegation record failed", exc_info=True)
        return None
