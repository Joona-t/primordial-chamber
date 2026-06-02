import pytest

from primordial_chamber.absence import (
    ABSENCE_STATES,
    AbsenceState,
    ForgeNullError,
    absent,
    normalize_absence_state,
    validate_absent_object,
    validate_record,
    validate_transition,
)


def test_absent_creates_canonical_state_object():
    obj = absent(AbsenceState.NOT_INVOKED, reason="tool gated")

    assert obj == {"value": None, "state": "not_invoked", "reason": "tool gated"}
    assert validate_absent_object(obj) == obj


def test_normalize_rejects_unknown_state():
    with pytest.raises(ForgeNullError):
        normalize_absence_state("timed_out")


def test_transition_matrix_initial_terminal_rules():
    assert validate_transition("not_invoked", "unresolved") is True
    assert validate_transition("unknown", "not_invoked") is False
    assert validate_transition("unresolved", "not_generated") is False
    assert validate_transition("deleted", "unknown") is False
    assert validate_transition("deleted", "deleted") is True


def test_transition_matrix_covers_all_states():
    for src in ABSENCE_STATES:
        for target in ABSENCE_STATES:
            result = validate_transition(src, target)
            assert isinstance(result, bool)


def test_validate_record_rejects_ambiguous_empty_semantic_field():
    with pytest.raises(ForgeNullError, match="Ambiguous empty value"):
        validate_record({"summary": ""})


def test_validate_record_accepts_sibling_state_for_empty_semantic_field():
    assert validate_record({"summary": "", "summary_state": "not_generated"}) == {
        "summary": "",
        "summary_state": "not_generated",
    }


def test_validate_record_allows_empty_source_refs_by_default():
    assert validate_record({"source_refs": []}) == {"source_refs": []}
