"""Reversible summary records.

A reversible summary is a compact text plus source references and optional
fragments that allow humans or tools to expand back toward the underlying
material without trusting the compression blindly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from .absence import ForgeNullError, validate_record
from .refs import Ref


@dataclass(frozen=True)
class ReversibleSummary:
    summary: str
    source_refs: list[dict[str, Any]] = field(default_factory=list)
    fragments: list[dict[str, Any]] = field(default_factory=list)
    summary_state: str | None = None

    @classmethod
    def from_sources(
        cls,
        summary: str,
        sources: Iterable[Ref | Mapping[str, Any]],
        *,
        fragments: Iterable[Mapping[str, Any]] | None = None,
        summary_state: str | None = None,
    ) -> "ReversibleSummary":
        refs: list[dict[str, Any]] = []
        for source in sources:
            refs.append(source.to_dict() if isinstance(source, Ref) else dict(source))
        obj = cls(
            summary=summary,
            source_refs=refs,
            fragments=[dict(f) for f in fragments or []],
            summary_state=summary_state,
        )
        obj.validate()
        return obj

    def validate(self) -> None:
        validate_record(self.to_dict())
        if self.summary and not self.source_refs:
            raise ForgeNullError("Reversible summaries require at least one source_ref")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}

    def expand(self) -> dict[str, Any]:
        """Return the provenance payload needed to inspect the summary."""

        return {
            "summary": self.summary,
            "source_refs": list(self.source_refs),
            "fragments": list(self.fragments),
        }
