"""Replica-safe admission control for password authentication attempts."""

from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from typing import Protocol, Sequence


class RedisEvalClient(Protocol):
    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object: ...


class LoginRateLimitUnavailable(RuntimeError):
    """Raised when a configured distributed limiter cannot make a decision."""


class LoginRateLimitExceeded(RuntimeError):
    def __init__(self, retry_after: int) -> None:
        super().__init__("login rate limit exceeded")
        self.retry_after = retry_after


class LoginRateLimiter(Protocol):
    def consume(self, scope: str, identity: str) -> None: ...

    def reset(self, scope: str, identity: str) -> None: ...


CONSUME_LUA = r"""
-- negin-login-rate-consume-v1
local current = redis.call("INCR", KEYS[1])
if current == 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[2])
end
local ttl = redis.call("TTL", KEYS[1])
if ttl < 1 then
  redis.call("EXPIRE", KEYS[1], ARGV[2])
  ttl = tonumber(ARGV[2])
end
if current > tonumber(ARGV[1]) then
  return {0, ttl}
end
return {1, ttl}
"""


RESET_LUA = r"""
-- negin-login-rate-reset-v1
return redis.call("DEL", KEYS[1])
"""


def _key_id(scope: str, identity: str) -> str:
    if not scope or not identity:
        raise ValueError("login rate-limit scope and identity are required")
    return hashlib.sha256(f"{scope}\x1f{identity}".encode("utf-8")).hexdigest()


class RedisLoginRateLimiter:
    """Fixed-window limiter whose increment and TTL are one Redis operation."""

    def __init__(
        self,
        client: RedisEvalClient,
        *,
        limit: int = 8,
        window_seconds: int = 300,
        key_prefix: str = "negin:login-rate",
    ) -> None:
        if limit <= 0 or window_seconds <= 0:
            raise ValueError("login rate-limit policy must be positive")
        prefix = key_prefix.strip().rstrip(":")
        if not prefix:
            raise ValueError("login rate-limit key prefix is required")
        self._client = client
        self._limit = int(limit)
        self._window_seconds = int(window_seconds)
        self._key_prefix = prefix

    def _key(self, scope: str, identity: str) -> str:
        return f"{self._key_prefix}:{{login}}:{_key_id(scope, identity)}"

    def consume(self, scope: str, identity: str) -> None:
        try:
            raw = self._client.eval(
                CONSUME_LUA,
                1,
                self._key(scope, identity),
                self._limit,
                self._window_seconds,
            )
        except Exception as exc:
            raise LoginRateLimitUnavailable("distributed login limiter unavailable") from exc
        if (
            not isinstance(raw, Sequence)
            or isinstance(raw, (str, bytes))
            or len(raw) != 2
        ):
            raise LoginRateLimitUnavailable("invalid distributed login limiter response")
        try:
            admitted = int(raw[0]) == 1
            retry_after = max(1, int(raw[1]))
        except (TypeError, ValueError) as exc:
            raise LoginRateLimitUnavailable(
                "invalid distributed login limiter response"
            ) from exc
        if not admitted:
            raise LoginRateLimitExceeded(retry_after=retry_after)

    def reset(self, scope: str, identity: str) -> None:
        try:
            raw = self._client.eval(
                RESET_LUA,
                1,
                self._key(scope, identity),
            )
        except Exception as exc:
            raise LoginRateLimitUnavailable("distributed login limiter unavailable") from exc
        if isinstance(raw, bool) or not isinstance(raw, int) or raw not in {0, 1}:
            raise LoginRateLimitUnavailable("invalid distributed login limiter response")


class LocalLoginRateLimiter:
    """Bounded development-only fallback with deterministic entry eviction."""

    def __init__(
        self,
        *,
        limit: int = 8,
        window_seconds: int = 300,
        max_identities: int = 10_000,
        clock=time.monotonic,
    ) -> None:
        if limit <= 0 or window_seconds <= 0 or max_identities <= 0:
            raise ValueError("login rate-limit policy must be positive")
        self._limit = int(limit)
        self._window_seconds = int(window_seconds)
        self._max_identities = int(max_identities)
        self._clock = clock
        self._entries: OrderedDict[str, tuple[int, float]] = OrderedDict()
        self._lock = threading.Lock()

    def _remove_expired(self, now: float) -> None:
        while self._entries:
            _, (_, expires_at) = next(iter(self._entries.items()))
            if expires_at > now:
                return
            self._entries.popitem(last=False)

    def consume(self, scope: str, identity: str) -> None:
        key = _key_id(scope, identity)
        now = self._clock()
        with self._lock:
            self._remove_expired(now)
            count, expires_at = self._entries.get(
                key, (0, now + self._window_seconds)
            )
            count += 1
            if key not in self._entries and len(self._entries) >= self._max_identities:
                self._entries.popitem(last=False)
            self._entries[key] = (count, expires_at)
            if count > self._limit:
                raise LoginRateLimitExceeded(
                    retry_after=max(1, int(expires_at - now + 0.999))
                )

    def reset(self, scope: str, identity: str) -> None:
        key = _key_id(scope, identity)
        with self._lock:
            self._entries.pop(key, None)
