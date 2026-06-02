from primordial_chamber.seats import SeatResult, SeatSpec, placeholder_seat, run_seat, static_seat


def test_static_seat_returns_text():
    result = run_seat("question", static_seat("codex", "answer"))

    assert result.ok is True
    assert result.seat_id == "codex"
    assert result.text == "answer"


def test_static_seat_without_text_is_typed_absence():
    result = run_seat("question", static_seat("codex", ""))

    assert result.ok is False
    assert result.absence_state == "not_generated"


def test_placeholder_seat_is_unavailable():
    result = run_seat("question", placeholder_seat("claude"))

    assert result.ok is False
    assert result.absence_state == "unavailable"


def test_custom_runner_receives_prompt_and_spec():
    def fake_runner(prompt: str, spec: SeatSpec) -> SeatResult:
        return SeatResult(seat_id=spec.seat_id, ok=True, text=f"{spec.seat_id}:{prompt}")

    result = run_seat("hello", SeatSpec(seat_id="seat-a", kind="fake", runner=fake_runner))

    assert result.text == "seat-a:hello"
