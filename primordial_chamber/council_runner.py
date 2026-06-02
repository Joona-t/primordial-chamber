"""Karpathy-style council runner adapted to local Primordial seats."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from .absence import AbsenceState
from .refs import content_ref
from .seats import SeatResult, SeatSpec, run_seat


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def response_label(index: int) -> str:
    return f"Response {chr(ord('A') + index)}"


def parse_final_ranking(text: str, valid_labels: Iterable[str]) -> list[str]:
    """Parse Karpathy-style ``FINAL RANKING: Response B, Response A`` text."""

    valid = list(valid_labels)
    valid_set = set(valid)
    match = re.search(r"FINAL\s+RANKING\s*:\s*(.+)", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return []
    tail = match.group(1).splitlines()[0]
    found = re.findall(r"Response\s+[A-Z]", tail, flags=re.IGNORECASE)
    normalized: list[str] = []
    for item in found:
        label = " ".join(part.capitalize() for part in item.split())
        if label in valid_set and label not in normalized:
            normalized.append(label)
    return normalized


def build_review_prompt(question: str, opinions: Sequence[dict[str, Any]]) -> str:
    lines = [
        "You are reviewing anonymous council responses.",
        "Rank the responses by correctness, usefulness, and operational clarity.",
        "Do not infer author identity.",
        "",
        f"Question: {question}",
        "",
    ]
    for opinion in opinions:
        lines.append(f"{opinion['label']}:")
        lines.append(str(opinion.get("text") or opinion.get("summary") or ""))
        lines.append("")
    lines.extend(
        [
            "Write a concise review.",
            "End with one line in this exact format:",
            "FINAL RANKING: Response A, Response B",
        ]
    )
    return "\n".join(lines)


def build_synthesis_prompt(
    question: str,
    opinions: Sequence[dict[str, Any]],
    reviews: Sequence[dict[str, Any]],
) -> str:
    lines = [
        "You are the chairman of an LLM council.",
        "Synthesize the strongest final answer using the first opinions and peer reviews.",
        "Be explicit where the council disagrees or where a seat failed.",
        "",
        f"Question: {question}",
        "",
        "First opinions:",
    ]
    for opinion in opinions:
        lines.append(f"- {opinion['label']}: {opinion.get('text') or opinion.get('summary') or opinion.get('absence_state')}")
    lines.extend(["", "Peer reviews:"])
    for review in reviews:
        ranking = ", ".join(review.get("ranking") or []) or review.get("absence_state") or "unranked"
        lines.append(f"- {review['reviewer_seat_id']} ranking {ranking}: {review.get('review_text') or ''}")
    lines.extend(["", "Final synthesis:"])
    return "\n".join(lines)


@dataclass(frozen=True)
class CouncilRunResult:
    record: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.record)


class CouncilRunner:
    """Run Stage 1 / Stage 2 / Stage 3 council deliberation over local seats."""

    def __init__(
        self,
        seats: Sequence[SeatSpec],
        *,
        chairman_seat_id: str | None = None,
        chairman_seat: SeatSpec | None = None,
        schema_version: int = 2,
    ):
        if not seats:
            raise ValueError("CouncilRunner requires at least one seat")
        self.seats = list(seats)
        self.chairman_seat = chairman_seat
        self.chairman_seat_id = chairman_seat_id or (chairman_seat.seat_id if chairman_seat else self.seats[0].seat_id)
        self.schema_version = schema_version

    def run(self, question: str) -> CouncilRunResult:
        question = question.strip()
        if not question:
            raise ValueError("Council question is required")
        stage1 = self._stage1(question)
        stage2 = self._stage2(question, stage1)
        stage3 = self._stage3(question, stage1, stage2)
        status = "sealed" if stage3.get("summary") else "failed"
        record = {
            "schema_version": self.schema_version,
            "id": content_ref(f"council:{question}:{_utc_now()}", kind="council_chamber").id,
            "status": status,
            "question": question,
            "created_at": _utc_now(),
            "stages": {
                "stage1_first_opinions": stage1,
                "stage2_peer_reviews": stage2,
                "stage3_chairman_synthesis": stage3,
            },
            "seats": [seat.to_dict() for seat in self.seats],
            "source_refs": self._record_refs(question, stage1, stage2, stage3),
            "metadata": {
                "architecture": "karpathy/llm-council adapted to local CLI seats",
                "chairman_seat_id": self.chairman_seat_id,
            },
        }
        return CouncilRunResult(record)

    def _stage1(self, question: str) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for index, seat in enumerate(self.seats):
            result = run_seat(question, seat)
            results.append(self._opinion_dict(result, label=response_label(index)))
        return results

    def _stage2(self, question: str, opinions: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        prompt = build_review_prompt(question, opinions)
        valid_labels = [opinion["label"] for opinion in opinions]
        reviews: list[dict[str, Any]] = []
        for seat in self.seats:
            result = run_seat(prompt, seat)
            ranking = parse_final_ranking(result.text, valid_labels) if result.ok else []
            item = {
                "reviewer_seat_id": seat.seat_id,
                "review_text": result.text,
                "ranking": ranking,
                "source_refs": self._refs_for_text(result.text, f"stage2:{seat.seat_id}"),
                "metadata": dict(result.metadata),
            }
            if not result.ok:
                item["absence_state"] = result.absence_state or AbsenceState.UNRESOLVED.value
                item["error"] = result.error or ""
            elif not ranking:
                item["absence_state"] = AbsenceState.INVALID.value
                item["error"] = "review did not include a parseable FINAL RANKING"
            reviews.append(item)
        return reviews

    def _stage3(
        self,
        question: str,
        opinions: Sequence[dict[str, Any]],
        reviews: Sequence[dict[str, Any]],
    ) -> dict[str, Any]:
        chairman = self._chairman_seat()
        prompt = build_synthesis_prompt(question, opinions, reviews)
        result = run_seat(prompt, chairman)
        item = {
            "chairman_seat_id": chairman.seat_id,
            "summary": result.text,
            "source_refs": self._refs_for_text(result.text, f"stage3:{chairman.seat_id}"),
            "metadata": dict(result.metadata),
        }
        if not result.ok:
            item["summary_state"] = result.absence_state or AbsenceState.UNRESOLVED.value
            item["error"] = result.error or ""
        return item

    def _chairman_seat(self) -> SeatSpec:
        if self.chairman_seat is not None:
            return self.chairman_seat
        for seat in self.seats:
            if seat.seat_id == self.chairman_seat_id:
                return seat
        raise ValueError(f"chairman seat not found: {self.chairman_seat_id}")

    def _opinion_dict(self, result: SeatResult, *, label: str) -> dict[str, Any]:
        item = {
            "seat_id": result.seat_id,
            "label": label,
            "summary": result.text,
            "source_refs": self._refs_for_text(result.text, f"stage1:{result.seat_id}"),
            "metadata": dict(result.metadata),
        }
        if not result.ok:
            item["summary_state"] = result.absence_state or AbsenceState.UNRESOLVED.value
            item["error"] = result.error or ""
        return item

    def _refs_for_text(self, text: str, label: str) -> list[dict[str, Any]]:
        if not text.strip():
            return []
        return [content_ref(text, kind="council_stage", label=label).to_dict()]

    def _record_refs(
        self,
        question: str,
        stage1: Sequence[dict[str, Any]],
        stage2: Sequence[dict[str, Any]],
        stage3: dict[str, Any],
    ) -> list[dict[str, Any]]:
        refs = [content_ref(question, kind="council_question", label="question").to_dict()]
        for item in [*stage1, *stage2, stage3]:
            refs.extend(item.get("source_refs") or [])
        return refs
