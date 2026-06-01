from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from agent.codex_runtime import (
    _sanitize_responses_sdk_kwargs,
    run_codex_create_stream_fallback,
    run_codex_stream,
)


def test_sanitize_responses_sdk_kwargs_omits_unset_iterables():
    kwargs = {
        "model": "gpt-5.5",
        "input": [{"role": "user", "content": "hello"}],
        "tools": [],
        "include": None,
        "context_management": None,
        "extra_headers": {"session_id": "s1", "x-empty": None},
        "extra_body": {"prompt_cache_key": "s1", "unused": None},
        "store": False,
    }

    sanitized = _sanitize_responses_sdk_kwargs(kwargs)

    assert "tools" not in sanitized
    assert "include" not in sanitized
    assert "context_management" not in sanitized
    assert sanitized["extra_headers"] == {"session_id": "s1"}
    assert sanitized["extra_body"] == {"prompt_cache_key": "s1"}
    assert sanitized["store"] is False


def test_codex_stream_logs_traceback_for_local_sdk_type_error(caplog):
    class Responses:
        def __init__(self):
            self.kwargs = None

        def stream(self, **kwargs):
            self.kwargs = kwargs
            raise TypeError("'NoneType' object is not iterable")

    responses = Responses()
    client = SimpleNamespace(responses=responses)
    agent = SimpleNamespace(
        _interrupt_requested=False,
        _codex_streamed_text_parts=[],
        _client_log_context=lambda: "provider=openai-codex model=gpt-5.5",
    )

    with caplog.at_level(logging.ERROR, logger="agent.codex_runtime"):
        with pytest.raises(TypeError, match="NoneType"):
            run_codex_stream(
                agent,
                {
                    "model": "gpt-5.5",
                    "input": "hello",
                    "tools": [],
                    "include": None,
                    "context_management": None,
                },
                client=client,
            )

    assert "tools" not in responses.kwargs
    assert "include" not in responses.kwargs
    assert "context_management" not in responses.kwargs
    assert "Local TypeError before/during Codex Responses SDK stream call" in caplog.text
    assert "Traceback" in caplog.text


def test_codex_stream_backfills_none_output_from_done_items():
    done_item = SimpleNamespace(
        type="message",
        content=[SimpleNamespace(type="output_text", text="Recovered")],
    )
    final_response = SimpleNamespace(output=None)

    class Stream:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def __iter__(self):
            return iter([SimpleNamespace(type="response.output_item.done", item=done_item)])

        def get_final_response(self):
            return final_response

    class Responses:
        def stream(self, **kwargs):
            return Stream()

    agent = SimpleNamespace(
        _interrupt_requested=False,
        _codex_streamed_text_parts=[],
        _client_log_context=lambda: "provider=openai-codex model=gpt-5.5",
        _touch_activity=lambda *_args, **_kwargs: None,
        _fire_stream_delta=lambda *_args, **_kwargs: None,
        _fire_reasoning_delta=lambda *_args, **_kwargs: None,
    )

    response = run_codex_stream(
        agent,
        {"model": "gpt-5.5", "input": "hello"},
        client=SimpleNamespace(responses=Responses()),
    )

    assert response.output == [done_item]


def test_codex_create_stream_fallback_sanitizes_kwargs_and_logs_type_error(caplog):
    class Transport:
        def preflight_kwargs(self, kwargs, *, allow_stream=False):
            assert allow_stream is True
            return dict(kwargs)

    class Responses:
        def __init__(self):
            self.kwargs = None

        def create(self, **kwargs):
            self.kwargs = kwargs
            raise TypeError("'NoneType' object is not iterable")

    responses = Responses()
    client = SimpleNamespace(responses=responses)
    agent = SimpleNamespace(
        _client_log_context=lambda: "provider=openai-codex model=gpt-5.5",
        _get_transport=lambda: Transport(),
    )

    with caplog.at_level(logging.ERROR, logger="agent.codex_runtime"):
        with pytest.raises(TypeError, match="NoneType"):
            run_codex_create_stream_fallback(
                agent,
                {
                    "model": "gpt-5.5",
                    "input": "hello",
                    "tools": [],
                    "include": None,
                    "context_management": None,
                },
                client=client,
            )

    assert responses.kwargs["stream"] is True
    assert "tools" not in responses.kwargs
    assert "include" not in responses.kwargs
    assert "context_management" not in responses.kwargs
    assert "Local TypeError before/during Codex Responses SDK create(stream=True) call" in caplog.text
    assert "Traceback" in caplog.text


def test_codex_create_stream_fallback_backfills_none_output_from_done_items():
    done_item = SimpleNamespace(
        type="message",
        content=[SimpleNamespace(type="output_text", text="Recovered")],
    )
    terminal = SimpleNamespace(output=None)

    class Transport:
        def preflight_kwargs(self, kwargs, *, allow_stream=False):
            assert allow_stream is True
            return dict(kwargs)

    class ResponseStream:
        def __iter__(self):
            return iter([
                SimpleNamespace(type="response.output_item.done", item=done_item),
                SimpleNamespace(type="response.completed", response=terminal),
            ])

        def close(self):
            pass

    class Responses:
        def create(self, **kwargs):
            return ResponseStream()

    agent = SimpleNamespace(
        _client_log_context=lambda: "provider=openai-codex model=gpt-5.5",
        _get_transport=lambda: Transport(),
        _touch_activity=lambda *_args, **_kwargs: None,
    )

    response = run_codex_create_stream_fallback(
        agent,
        {"model": "gpt-5.5", "input": "hello"},
        client=SimpleNamespace(responses=Responses()),
    )

    assert response.output == [done_item]
