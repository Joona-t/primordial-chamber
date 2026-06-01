"""Chamber records: multi-voice synthesis without hidden provenance."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from .summary import ReversibleSummary


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class ChamberVoice:
    name: str
    stance: str
    summary: str
    source_refs: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChamberRecord:
    question: str
    voices: list[ChamberVoice]
    synthesis: ReversibleSummary
    created_at: str = field(default_factory=_utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        question: str,
        voices: list[ChamberVoice | Mapping[str, Any]],
        synthesis: ReversibleSummary,
        metadata: Mapping[str, Any] | None = None,
    ) -> "ChamberRecord":
        normalized: list[ChamberVoice] = []
        for voice in voices:
            if isinstance(voice, ChamberVoice):
                normalized.append(voice)
            else:
                normalized.append(
                    ChamberVoice(
                        name=str(voice.get("name", "voice")),
                        stance=str(voice.get("stance", "")),
                        summary=str(voice.get("summary", "")),
                        source_refs=[dict(r) for r in voice.get("source_refs", []) or []],
                    )
                )
        record = cls(
            question=question,
            voices=normalized,
            synthesis=synthesis,
            metadata=dict(metadata or {}),
        )
        record.validate()
        return record

    def validate(self) -> None:
        if not self.question.strip():
            raise ValueError("Chamber question is required")
        if not self.voices:
            raise ValueError("Chamber requires at least one voice")
        for voice in self.voices:
            if not voice.name.strip():
                raise ValueError("Chamber voice name is required")
        self.synthesis.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "voices": [v.to_dict() for v in self.voices],
            "synthesis": self.synthesis.to_dict(),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }
