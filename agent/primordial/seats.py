"""Seat adapters for local Primordial council runs."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Mapping, Sequence

from .absence import AbsenceState
from .openclaw_adapter import DEFAULT_OPENCLAW_SESSION_KEY, run_openclaw_agent

SeatRunner = Callable[[str, "SeatSpec"], "SeatResult"]


@dataclass(frozen=True)
class SeatResult:
    """Normalized output from one council seat prompt."""

    seat_id: str
    ok: bool
    text: str = ""
    error: str | None = None
    absence_state: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass(frozen=True)
class SeatSpec:
    """Definition for a council seat.

    ``runner`` is intentionally process-local and omitted from serialization.
    """

    seat_id: str
    kind: str
    label: str | None = None
    command: tuple[str, ...] = ()
    session_key: str | None = None
    timeout_seconds: int = 600
    static_text: str | None = None
    runner: SeatRunner | None = field(default=None, repr=False, compare=False)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("runner", None)
        return {k: v for k, v in data.items() if v not in (None, (), {})}


def static_seat(seat_id: str, text: str, *, label: str | None = None) -> SeatSpec:
    """Create a seat that returns supplied text for every prompt."""

    return SeatSpec(seat_id=seat_id, kind="static", label=label, static_text=text)


def openclaw_seat(
    *,
    seat_id: str = "openclaw",
    session_key: str = DEFAULT_OPENCLAW_SESSION_KEY,
    timeout_seconds: int = 600,
    openclaw_bin: str = "openclaw",
) -> SeatSpec:
    """Create an OpenClaw CLI-backed council seat."""

    return SeatSpec(
        seat_id=seat_id,
        kind="openclaw",
        label="OpenClaw",
        command=(openclaw_bin,),
        session_key=session_key,
        timeout_seconds=timeout_seconds,
    )


def cli_seat(
    seat_id: str,
    command: Sequence[str],
    *,
    label: str | None = None,
    timeout_seconds: int = 600,
) -> SeatSpec:
    """Create a generic CLI seat whose command receives the prompt as argv."""

    return SeatSpec(
        seat_id=seat_id,
        kind="cli",
        label=label,
        command=tuple(command),
        timeout_seconds=timeout_seconds,
    )


def placeholder_seat(seat_id: str, *, label: str | None = None) -> SeatSpec:
    """Create a declared but unavailable seat for future harnesses."""

    return SeatSpec(seat_id=seat_id, kind="placeholder", label=label)


def run_seat(prompt: str, spec: SeatSpec) -> SeatResult:
    """Run one prompt through a seat spec."""

    if spec.runner is not None:
        return spec.runner(prompt, spec)

    if spec.kind == "static":
        text = (spec.static_text or "").strip()
        return SeatResult(
            seat_id=spec.seat_id,
            ok=bool(text),
            text=text,
            absence_state=None if text else AbsenceState.NOT_GENERATED.value,
            error=None if text else "static seat has no text",
            metadata={"kind": spec.kind},
        )

    if spec.kind == "openclaw":
        openclaw_bin = spec.command[0] if spec.command else "openclaw"
        result = run_openclaw_agent(
            prompt,
            session_key=spec.session_key or DEFAULT_OPENCLAW_SESSION_KEY,
            timeout_seconds=spec.timeout_seconds,
            openclaw_bin=openclaw_bin,
        )
        return SeatResult(
            seat_id=spec.seat_id,
            ok=result.ok,
            text=result.summary,
            error=result.error,
            absence_state=result.absence_state,
            raw=result.raw,
            metadata={
                "kind": spec.kind,
                "session_key": result.session_key,
                "session_id": result.session_id,
            },
        )

    if spec.kind == "cli":
        if not spec.command:
            return SeatResult(
                seat_id=spec.seat_id,
                ok=False,
                error="cli seat has no command",
                absence_state=AbsenceState.NOT_INVOKED.value,
                metadata={"kind": spec.kind},
            )
        try:
            completed = subprocess.run(
                [*spec.command, prompt],
                capture_output=True,
                text=True,
                timeout=spec.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            return SeatResult(
                seat_id=spec.seat_id,
                ok=False,
                error=str(exc),
                absence_state=AbsenceState.NOT_INVOKED.value,
                metadata={"kind": spec.kind},
            )
        except subprocess.TimeoutExpired as exc:
            return SeatResult(
                seat_id=spec.seat_id,
                ok=False,
                error=str(exc),
                absence_state=AbsenceState.UNRESOLVED.value,
                metadata={"kind": spec.kind},
            )
        text = (completed.stdout or "").strip()
        ok = completed.returncode == 0 and bool(text)
        return SeatResult(
            seat_id=spec.seat_id,
            ok=ok,
            text=text,
            error=None if ok else ((completed.stderr or "").strip() or f"cli exited {completed.returncode}"),
            absence_state=None if ok else AbsenceState.UNRESOLVED.value,
            metadata={"kind": spec.kind, "returncode": completed.returncode},
        )

    return SeatResult(
        seat_id=spec.seat_id,
        ok=False,
        error=f"seat kind unavailable: {spec.kind}",
        absence_state=AbsenceState.UNAVAILABLE.value,
        metadata={"kind": spec.kind},
    )


def seat_result_from_mapping(seat_id: str, data: Mapping[str, Any]) -> SeatResult:
    """Build a seat result from tests or external adapters."""

    text = data.get("text") or data.get("summary") or data.get("response") or ""
    ok = bool(data.get("ok", bool(text))) and bool(str(text).strip())
    return SeatResult(
        seat_id=seat_id,
        ok=ok,
        text=str(text).strip(),
        error=data.get("error") if isinstance(data.get("error"), str) else None,
        absence_state=(
            data.get("absence_state")
            if isinstance(data.get("absence_state"), str)
            else (None if ok else AbsenceState.UNRESOLVED.value)
        ),
        raw=dict(data.get("raw") or {}),
        metadata=dict(data.get("metadata") or {}),
    )
