"""Redis-backed, replica-safe admission control for external model work.

All admission decisions are made by one Lua invocation.  Concurrency is stored
as expiring sorted-set leases instead of counters so a terminated worker cannot
hold capacity forever.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Protocol, Sequence

from app.routes.chat import (
    ModelResourceLease,
    ModelResourceLimitExceeded,
    ModelResourcePolicy,
)


class RedisEvalClient(Protocol):
    """The narrow redis-py synchronous interface used by the backend."""

    def eval(self, script: str, numkeys: int, *keys_and_args: object) -> object: ...


ACQUIRE_LUA = r"""
-- negin-model-resource-acquire-v1
local global_leases = KEYS[1]
local user_leases = KEYS[2]
local user_rpm = KEYS[3]
local user_budget = KEYS[4]
local global_budget = KEYS[5]

local lease_ttl_ms = tonumber(ARGV[1])
local global_limit = tonumber(ARGV[2])
local user_limit = tonumber(ARGV[3])
local rpm_limit = tonumber(ARGV[4])
local request_units = tonumber(ARGV[5])
local max_request_units = tonumber(ARGV[6])
local user_daily_limit = tonumber(ARGV[7])
local global_daily_limit = tonumber(ARGV[8])
local token = ARGV[9]

if not lease_ttl_ms or not global_limit or not user_limit or not rpm_limit or
   not request_units or not max_request_units or not user_daily_limit or
   not global_daily_limit or lease_ttl_ms <= 0 or global_limit <= 0 or
   user_limit <= 0 or rpm_limit <= 0 or max_request_units <= 0 or
   user_daily_limit <= 0 or global_daily_limit <= 0 or
   user_limit > global_limit or user_daily_limit > global_daily_limit then
  return {0, "invalid_policy", 60}
end
if request_units <= 0 or request_units > max_request_units then
  return {0, "request_budget", 60}
end

local redis_time = redis.call("TIME")
local now_seconds = tonumber(redis_time[1])
local now_ms = now_seconds * 1000 + math.floor(tonumber(redis_time[2]) / 1000)
local current_day = tostring(math.floor(now_seconds / 86400))
local day_retry = 86400 - (now_seconds % 86400)
if day_retry < 1 then day_retry = 1 end

-- Expired leases are removed before either concurrency count is inspected.
redis.call("ZREMRANGEBYSCORE", global_leases, "-inf", now_ms)
redis.call("ZREMRANGEBYSCORE", user_leases, "-inf", now_ms)
if redis.call("ZCARD", global_leases) >= global_limit then
  return {0, "global_concurrency", 1}
end
if redis.call("ZCARD", user_leases) >= user_limit then
  return {0, "user_concurrency", 1}
end

local minute_start = now_ms - 60000
redis.call("ZREMRANGEBYSCORE", user_rpm, "-inf", minute_start)
if redis.call("ZCARD", user_rpm) >= rpm_limit then
  local oldest = redis.call("ZRANGE", user_rpm, 0, 0, "WITHSCORES")
  local retry_ms = 1000
  if oldest[2] then retry_ms = tonumber(oldest[2]) + 60000 - now_ms end
  local retry_seconds = math.ceil(retry_ms / 1000)
  if retry_seconds < 1 then retry_seconds = 1 end
  return {0, "rpm", retry_seconds}
end

local function used_today(key)
  if redis.call("HGET", key, "day") ~= current_day then return 0 end
  return tonumber(redis.call("HGET", key, "used") or "0")
end

local user_used = used_today(user_budget)
local global_used = used_today(global_budget)
if user_used + request_units > user_daily_limit then
  return {0, "user_daily_budget", day_retry}
end
if global_used + request_units > global_daily_limit then
  return {0, "global_daily_budget", day_retry}
end

local expires_ms = now_ms + lease_ttl_ms
redis.call("ZADD", global_leases, expires_ms, token)
redis.call("ZADD", user_leases, expires_ms, token)
redis.call("PEXPIRE", global_leases, lease_ttl_ms)
redis.call("PEXPIRE", user_leases, lease_ttl_ms)
redis.call("ZADD", user_rpm, now_ms, token)
redis.call("PEXPIRE", user_rpm, 61000)
redis.call("HSET", user_budget, "day", current_day, "used", user_used + request_units)
redis.call("HSET", global_budget, "day", current_day, "used", global_used + request_units)
redis.call("EXPIRE", user_budget, day_retry + 60)
redis.call("EXPIRE", global_budget, day_retry + 60)
return {1, token, expires_ms}
"""


RELEASE_LUA = r"""
-- negin-model-resource-release-v1
local removed_global = redis.call("ZREM", KEYS[1], ARGV[1])
local removed_user = redis.call("ZREM", KEYS[2], ARGV[1])
return removed_global + removed_user
"""


RENEW_LUA = r"""
-- negin-model-resource-renew-v1
local global_leases = KEYS[1]
local user_leases = KEYS[2]
local token = ARGV[1]
local lease_ttl_ms = tonumber(ARGV[2])
if not lease_ttl_ms or lease_ttl_ms <= 0 then return {0, "invalid_ttl"} end

-- A lease is valid only while the same opaque token exists in both indexes.
-- Never recreate a partially lost/expired lease because that could admit work
-- without preserving the original atomic admission decision.
if not redis.call("ZSCORE", global_leases, token) or
   not redis.call("ZSCORE", user_leases, token) then
  return {0, "lease_lost"}
end
local redis_time = redis.call("TIME")
local now_ms = tonumber(redis_time[1]) * 1000 +
  math.floor(tonumber(redis_time[2]) / 1000)
local expires_ms = now_ms + lease_ttl_ms
redis.call("ZADD", global_leases, "XX", expires_ms, token)
redis.call("ZADD", user_leases, "XX", expires_ms, token)
redis.call("PEXPIRE", global_leases, lease_ttl_ms)
redis.call("PEXPIRE", user_leases, lease_ttl_ms)
return {1, expires_ms}
"""


@dataclass(frozen=True)
class RedisModelResourceLease(ModelResourceLease):
    token: str
    user_key_id: str


_LIMIT_ERRORS: dict[str, tuple[str, int]] = {
    "request_budget": ("model request budget is outside the allowed range", 60),
    "global_concurrency": ("model service concurrency limit reached", 1),
    "user_concurrency": ("user model concurrency limit reached", 1),
    "rpm": ("user model request quota exceeded", 60),
    "user_daily_budget": ("user model daily budget exceeded", 3600),
    "global_daily_budget": ("global model daily budget exceeded", 3600),
}


def _text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="strict")
    return str(value)


class RedisModelResourceBackend:
    """Atomic distributed implementation of ``ModelResourceBackend``.

    The client is intentionally typed to redis-py's small synchronous ``eval``
    seam, keeping the module importable before the optional Redis dependency is
    installed and making failure behavior straightforward: Redis errors escape
    and are converted to a fail-closed 503 by the route boundary.
    """

    def __init__(
        self,
        client: RedisEvalClient,
        *,
        key_prefix: str = "negin:model-resource",
        lease_ttl_seconds: int = 120,
    ) -> None:
        prefix = key_prefix.strip().rstrip(":")
        if not prefix or "{" in prefix or "}" in prefix:
            raise ValueError("Redis model resource key prefix is invalid")
        if isinstance(lease_ttl_seconds, bool) or lease_ttl_seconds <= 0:
            raise ValueError("Redis model resource lease TTL must be positive")
        self._client = client
        # The hash tag keeps all script keys in one Redis Cluster slot.
        self._key_base = f"{prefix}:{{model-resource}}"
        self._lease_ttl_ms = int(lease_ttl_seconds) * 1000

    @property
    def renewal_interval_seconds(self) -> float:
        """Renew well before expiry while avoiding an aggressive Redis loop."""
        return max(1.0, self._lease_ttl_ms / 3000.0)

    def _user_key_id(self, identity: str) -> str:
        if not isinstance(identity, str) or not identity:
            raise ValueError("model resource identity must be non-empty")
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    def _keys(self, user_key_id: str) -> tuple[str, str, str, str, str]:
        return (
            f"{self._key_base}:leases:global",
            f"{self._key_base}:leases:user:{user_key_id}",
            f"{self._key_base}:rpm:user:{user_key_id}",
            f"{self._key_base}:budget:user:{user_key_id}",
            f"{self._key_base}:budget:global",
        )

    @staticmethod
    def _validate_policy(policy: ModelResourcePolicy, budget_units: int) -> None:
        values = (
            policy.global_concurrency,
            policy.user_concurrency,
            policy.user_requests_per_minute,
            policy.user_daily_budget_units,
            policy.global_daily_budget_units,
            policy.max_request_budget_units,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in values):
            raise RuntimeError("invalid model resource policy")
        if policy.user_concurrency > policy.global_concurrency:
            raise RuntimeError("invalid model resource policy")
        if policy.user_daily_budget_units > policy.global_daily_budget_units:
            raise RuntimeError("invalid model resource policy")
        if isinstance(budget_units, bool) or not isinstance(budget_units, int):
            raise ModelResourceLimitExceeded(
                "model request budget is outside the allowed range"
            )

    def acquire(
        self,
        identity: str,
        policy: ModelResourcePolicy,
        budget_units: int,
    ) -> ModelResourceLease:
        self._validate_policy(policy, budget_units)
        user_key_id = self._user_key_id(identity)
        token = secrets.token_urlsafe(24)
        keys = self._keys(user_key_id)
        raw = self._client.eval(
            ACQUIRE_LUA,
            len(keys),
            *keys,
            self._lease_ttl_ms,
            policy.global_concurrency,
            policy.user_concurrency,
            policy.user_requests_per_minute,
            budget_units,
            policy.max_request_budget_units,
            policy.user_daily_budget_units,
            policy.global_daily_budget_units,
            token,
        )
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < 2:
            raise RuntimeError("invalid Redis model resource response")
        try:
            admitted = int(raw[0]) == 1
        except (TypeError, ValueError) as exc:
            raise RuntimeError("invalid Redis model resource response") from exc
        if admitted:
            if not secrets.compare_digest(_text(raw[1]), token):
                raise RuntimeError("Redis model resource lease token mismatch")
            return RedisModelResourceLease(
                identity=identity,
                token=token,
                user_key_id=user_key_id,
            )

        code = _text(raw[1])
        if code == "invalid_policy":
            raise RuntimeError("invalid model resource policy")
        if code not in _LIMIT_ERRORS:
            raise RuntimeError("invalid Redis model resource rejection response")
        detail, fallback_retry = _LIMIT_ERRORS[code]
        try:
            retry_after = max(1, int(raw[2])) if len(raw) > 2 else fallback_retry
        except (TypeError, ValueError):
            retry_after = fallback_retry
        raise ModelResourceLimitExceeded(detail, retry_after=retry_after)

    def release(self, lease: ModelResourceLease) -> None:
        if not isinstance(lease, RedisModelResourceLease):
            raise TypeError("lease was not issued by the Redis model resource backend")
        global_key, user_key, _, _, _ = self._keys(lease.user_key_id)
        raw = self._client.eval(
            RELEASE_LUA,
            2,
            global_key,
            user_key,
            lease.token,
        )
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0 or raw > 2:
            raise RuntimeError("invalid Redis model resource release response")

    def renew(self, lease: ModelResourceLease) -> None:
        if not isinstance(lease, RedisModelResourceLease):
            raise TypeError("lease was not issued by the Redis model resource backend")
        global_key, user_key, _, _, _ = self._keys(lease.user_key_id)
        raw = self._client.eval(
            RENEW_LUA,
            2,
            global_key,
            user_key,
            lease.token,
            self._lease_ttl_ms,
        )
        if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < 2:
            raise RuntimeError("invalid Redis model resource renewal response")
        try:
            renewed = int(raw[0]) == 1
        except (TypeError, ValueError) as exc:
            raise RuntimeError("invalid Redis model resource renewal response") from exc
        if not renewed:
            raise RuntimeError(f"Redis model resource lease renewal failed: {_text(raw[1])}")
