"""Typed absence primitives.

Hermes data records often need to distinguish "not looked up" from "looked up
and unavailable".  Bare ``None`` and empty strings collapse those states, so
this module provides a small state lattice and validation helpers.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Mapping


class ForgeNullError(ValueError):
    """Raised when an ambiguous or invalid absence value is encountered."""


class AbsenceState(str, Enum):
    NOT_INVOKED = "not_invoked"
    UNRESOLVED = "unresolved"
    UNKNOWN = "unknown"
    NOT_GENERATED = "not_generated"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"
    REDACTED = "redacted"
    DELETED = "deleted"


ABSENCE_STATES = frozenset(state.value for state in AbsenceState)

# Conservative transition matrix.  It permits refinement from an initial
# not-invoked state into known absence states, permits stable self-transitions,
# and treats redacted/deleted as terminal.
_ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    AbsenceState.NOT_INVOKED.value: frozenset(
        {
            AbsenceState.NOT_INVOKED.value,
            AbsenceState.UNRESOLVED.value,
            AbsenceState.UNKNOWN.value,
            AbsenceState.NOT_GENERATED.value,
            AbsenceState.INVALID.value,
            AbsenceState.UNAVAILABLE.value,
            AbsenceState.REDACTED.value,
            AbsenceState.DELETED.value,
        }
    ),
    AbsenceState.UNRESOLVED.value: frozenset(
        {
            AbsenceState.UNRESOLVED.value,
            AbsenceState.UNKNOWN.value,
            AbsenceState.INVALID.value,
            AbsenceState.UNAVAILABLE.value,
            AbsenceState.REDACTED.value,
            AbsenceState.DELETED.value,
        }
    ),
    AbsenceState.UNKNOWN.value: frozenset(
        {
            AbsenceState.UNKNOWN.value,
            AbsenceState.INVALID.value,
            AbsenceState.UNAVAILABLE.value,
            AbsenceState.REDACTED.value,
            AbsenceState.DELETED.value,
        }
    ),
    AbsenceState.NOT_GENERATED.value: frozenset(
        {
            AbsenceState.NOT_GENERATED.value,
            AbsenceState.INVALID.value,
            AbsenceState.REDACTED.value,
            AbsenceState.DELETED.value,
        }
    ),
    AbsenceState.INVALID.value: frozenset(
        {
            AbsenceState.INVALID.value,
            AbsenceState.REDACTED.value,
            AbsenceState.DELETED.value,
        }
    ),
    AbsenceState.UNAVAILABLE.value: frozenset(
        {
            AbsenceState.UNAVAILABLE.value,
            AbsenceState.REDACTED.value,
            AbsenceState.DELETED.value,
        }
    ),
    AbsenceState.REDACTED.value: frozenset({AbsenceState.REDACTED.value}),
    AbsenceState.DELETED.value: frozenset({AbsenceState.DELETED.value}),
}

_SEMANTIC_EMPTY_FIELDS = frozenset(
    {
        "summary",
        "result",
        "content",
        "answer",
        "evidence",
        "decision",
        "synthesis",
    }
)


def normalize_absence_state(state: Any) -> str:
    """Return the canonical string value for a known absence state."""

    if isinstance(state, AbsenceState):
        return state.value
    if isinstance(state, str) and state in ABSENCE_STATES:
        return state
    raise ForgeNullError(f"Unknown absence state: {state!r}")


def absent(state: AbsenceState | str, *, reason: str | None = None) -> dict[str, Any]:
    """Create a canonical absent object: ``{"value": None, "state": ...}``."""

    obj: dict[str, Any] = {"value": None, "state": normalize_absence_state(state)}
    if reason:
        obj["reason"] = str(reason)
    return obj


def validate_absent_object(obj: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a mapping that represents typed absence."""

    if not isinstance(obj, Mapping):
        raise ForgeNullError("Absent object must be a mapping")
    if obj.get("value") is not None:
        raise ForgeNullError("Absent object must have value=None")
    state = normalize_absence_state(obj.get("state"))
    out: dict[str, Any] = {"value": None, "state": state}
    reason = obj.get("reason")
    if reason:
        out["reason"] = str(reason)
    return out


def validate_transition(previous: AbsenceState | str, current: AbsenceState | str) -> bool:
    """Return whether an absence state transition is allowed."""

    src = normalize_absence_state(previous)
    dst = normalize_absence_state(current)
    return dst in _ALLOWED_TRANSITIONS[src]


def validate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Reject ambiguous semantic empties in a record.

    Empty strings on semantic fields must be paired with ``<field>_state`` so
    consumers can tell whether the value was not generated, redacted, etc.
    Empty lists (for example ``source_refs=[]``) are allowed because an empty
    collection is often the precise observed value.
    """

    if not isinstance(record, Mapping):
        raise ForgeNullError("Record must be a mapping")
    out = dict(record)
    for key, value in out.items():
        if isinstance(value, Mapping) and set(value.keys()) >= {"value", "state"}:
            out[key] = validate_absent_object(value)
            continue
        if key.endswith("_state"):
            normalize_absence_state(value)
            continue
        if key in _SEMANTIC_EMPTY_FIELDS and value == "":
            state_key = f"{key}_state"
            if state_key not in out:
                raise ForgeNullError(
                    f"Ambiguous empty value for {key!r}; add {state_key!r}"
                )
            normalize_absence_state(out[state_key])
    return out
