import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, Request

from app.routes.audio import read_bounded_request_body
from app.routes.chat import (
    InMemoryModelResourceBackend,
    ModelResourceLimitExceeded,
    ModelResourcePolicy,
    ModelResourceLease,
    model_resource_lease,
    model_resource_policy,
)


def _policy(**overrides):
    values = {
        "global_concurrency": 2,
        "user_concurrency": 1,
        "user_requests_per_minute": 2,
        "user_daily_budget_units": 10_000,
        "global_daily_budget_units": 20_000,
        "max_request_budget_units": 5_000,
    }
    values.update(overrides)
    return ModelResourcePolicy(**values)


def test_in_memory_backend_enforces_concurrency_quota_and_budget():
    backend = InMemoryModelResourceBackend()
    lease = backend.acquire("seller-a", _policy(global_concurrency=1), 1_000)
    with pytest.raises(ModelResourceLimitExceeded, match="concurrency"):
        backend.acquire("seller-b", _policy(global_concurrency=1), 1_000)
    backend.release(lease)

    quota_policy = _policy(user_requests_per_minute=1)
    lease = backend.acquire("seller-b", quota_policy, 1_000)
    backend.release(lease)
    with pytest.raises(ModelResourceLimitExceeded, match="quota"):
        backend.acquire("seller-b", quota_policy, 1_000)

    with pytest.raises(ModelResourceLimitExceeded, match="daily budget"):
        backend.acquire("seller-c", _policy(user_daily_budget_units=500), 1_000)


def test_invalid_resource_configuration_fails_closed(monkeypatch):
    monkeypatch.setenv("NEGIN_MODEL_GLOBAL_CONCURRENCY", "not-a-number")
    with pytest.raises(RuntimeError, match="NEGIN_MODEL_GLOBAL_CONCURRENCY"):
        model_resource_policy()


def test_release_failure_latches_the_backend_closed():
    class LostLeaseBackend:
        def acquire(self, identity, _policy, _budget_units):
            return ModelResourceLease(identity)

        def release(self, _lease):
            raise ConnectionError("lease state unknown")

    state = SimpleNamespace(settings=object(), model_resource_backend=LostLeaseBackend())
    app = SimpleNamespace(state=state)
    request = Request(
        {"type": "http", "method": "POST", "headers": [], "app": app, "state": {"username": "seller"}}
    )

    async def consume_once():
        async with model_resource_lease(request, 1_000):
            pass

    asyncio.run(consume_once())
    assert state._model_resource_backend_failed is True
    with pytest.raises(HTTPException) as rejected:
        asyncio.run(consume_once())
    assert rejected.value.status_code == 503


def test_all_model_routes_fail_closed_when_the_backend_is_unavailable(
    client, auth, settings, monkeypatch
):
    class UnavailableBackend:
        def acquire(self, *_args, **_kwargs):
            raise ConnectionError("redis unavailable")

        def release(self, _lease):
            raise AssertionError("a rejected lease cannot be released")

    client.app.state.settings = replace(settings, openai_api_key="test-openai-key")
    client.app.state.model_resource_backend = UnavailableBackend()
    monkeypatch.setattr(
        "app.routes.chat.chat",
        lambda *_args, **_kwargs: pytest.fail("chat provider must not run"),
    )
    monkeypatch.setattr(
        "app.routes.attachments.analyze_attachment",
        lambda *_args, **_kwargs: pytest.fail("attachment provider must not run"),
    )
    monkeypatch.setattr(
        "app.routes.audio.transcribe_audio",
        lambda *_args, **_kwargs: pytest.fail("transcription provider must not run"),
    )
    monkeypatch.setattr(
        "app.routes.audio.synthesize_navigation_speech",
        lambda *_args, **_kwargs: pytest.fail("speech provider must not run"),
    )
    try:
        responses = [
            client.post("/chat", headers=auth, json={"message": "hello"}),
            client.post(
                "/attachments/analyze",
                headers=auth,
                files={"file": ("invoice.jpg", b"image", "image/jpeg")},
            ),
            client.post(
                "/audio/transcriptions",
                headers={**auth, "Content-Type": "audio/webm"},
                content=b"audio",
            ),
            client.post(
                "/audio/navigation-speech",
                headers=auth,
                json={"text": "start"},
            ),
        ]
    finally:
        del client.app.state.model_resource_backend
    assert [response.status_code for response in responses] == [503, 503, 503, 503]
    assert all(
        response.json()["detail"] == "model resource controls are unavailable"
        for response in responses
    )


def test_audio_stream_stops_before_buffering_an_oversized_body():
    chunks = iter(
        [
            {"type": "http.request", "body": b"123456", "more_body": True},
            {"type": "http.request", "body": b"789012", "more_body": False},
        ]
    )

    async def receive():
        return next(chunks)

    request = Request({"type": "http", "method": "POST", "headers": []}, receive)
    with pytest.raises(HTTPException) as rejected:
        asyncio.run(read_bounded_request_body(request, 10))
    assert rejected.value.status_code == 413
