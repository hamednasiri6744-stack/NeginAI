from __future__ import annotations

from dataclasses import replace

import pytest

from app.login_rate_limit import (
    LocalLoginRateLimiter,
    LoginRateLimitExceeded,
    LoginRateLimitUnavailable,
    RedisLoginRateLimiter,
)


class _RedisStub:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def eval(self, script, numkeys, *args):
        self.calls.append((script, numkeys, args))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_local_limiter_expires_and_caps_identity_storage():
    now = [100.0]
    limiter = LocalLoginRateLimiter(
        limit=1,
        window_seconds=5,
        max_identities=2,
        clock=lambda: now[0],
    )
    limiter.consume("login", "first")
    limiter.consume("login", "second")
    limiter.consume("login", "third")
    # The oldest identity was evicted instead of allowing unbounded growth.
    limiter.consume("login", "first")
    with pytest.raises(LoginRateLimitExceeded):
        limiter.consume("login", "first")

    now[0] += 6
    limiter.consume("login", "first")


def test_redis_limiter_uses_atomic_ttl_script_and_fails_closed():
    redis = _RedisStub([[1, 300], [0, 17], OSError("redis down")])
    limiter = RedisLoginRateLimiter(redis)

    limiter.consume("auth-login", "127.0.0.1")
    script, numkeys, args = redis.calls[0]
    assert "INCR" in script and "EXPIRE" in script
    assert numkeys == 1
    assert "127.0.0.1" not in args[0]

    with pytest.raises(LoginRateLimitExceeded) as limited:
        limiter.consume("auth-login", "127.0.0.1")
    assert limited.value.retry_after == 17
    with pytest.raises(LoginRateLimitUnavailable):
        limiter.consume("auth-login", "127.0.0.1")


def test_auth_login_returns_429_after_bounded_attempts(client, settings):
    client.app.state.settings = replace(
        settings,
        login_username="sample-user",
        login_password_hash=(
            "pbkdf2_sha256$10000$Zml4ZWQtc2FsdA==$"
            "L2H4PRgErM96wdH-vqSB1dY3wrN9v9pV6Uq9Wz5z0yA="
        ),
    )
    client.app.state.login_rate_limiter = LocalLoginRateLimiter(limit=2)

    assert client.post(
        "/auth/login", json={"username": "sample-user", "password": "wrong"}
    ).status_code == 401
    assert client.post(
        "/auth/login", json={"username": "sample-user", "password": "wrong"}
    ).status_code == 401
    blocked = client.post(
        "/auth/login", json={"username": "sample-user", "password": "wrong"}
    )
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
