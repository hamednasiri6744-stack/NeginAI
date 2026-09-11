from __future__ import annotations

import math
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.redis_resource_backend import (
    ACQUIRE_LUA,
    RELEASE_LUA,
    RENEW_LUA,
    RedisModelResourceBackend,
)
from app.routes.chat import ModelResourceLimitExceeded, ModelResourcePolicy


def _policy(**overrides: int) -> ModelResourcePolicy:
    values = {
        "global_concurrency": 3,
        "user_concurrency": 2,
        "user_requests_per_minute": 4,
        "user_daily_budget_units": 5_000,
        "global_daily_budget_units": 10_000,
        "max_request_budget_units": 2_000,
    }
    values.update(overrides)
    return ModelResourcePolicy(**values)


class DeterministicScriptRedis:
    """Small atomic script harness; no live Redis server is involved."""

    def __init__(self, *, now_ms: int = 1_800_000_000_000) -> None:
        self.now_ms = now_ms
        self._lock = threading.Lock()
        self.leases: dict[str, dict[str, int]] = defaultdict(dict)
        self.rpm: dict[str, dict[str, int]] = defaultdict(dict)
        self.budgets: dict[str, tuple[int, int]] = {}
        self.calls: list[tuple[str, tuple[object, ...]]] = []
        self.failure: Exception | None = None

    def advance(self, milliseconds: int) -> None:
        self.now_ms += milliseconds

    def eval(self, script: str, numkeys: int, *items: object) -> object:
        if self.failure is not None:
            raise self.failure
        with self._lock:
            self.calls.append((script, items))
            keys = tuple(str(item) for item in items[:numkeys])
            args = items[numkeys:]
            if script == ACQUIRE_LUA:
                return self._acquire(keys, args)
            if script == RELEASE_LUA:
                return self._release(keys, args)
            if script == RENEW_LUA:
                return self._renew(keys, args)
            raise AssertionError("unexpected script")

    def _acquire(self, keys: tuple[str, ...], args: tuple[object, ...]) -> list[object]:
        assert len(keys) == 5
        (
            ttl_ms,
            global_limit,
            user_limit,
            rpm_limit,
            request_units,
            max_request,
            user_daily,
            global_daily,
            token,
        ) = args
        values = [int(value) for value in args[:8]]
        ttl_ms, global_limit, user_limit, rpm_limit, request_units, max_request, user_daily, global_daily = values
        if (
            min(ttl_ms, global_limit, user_limit, rpm_limit, max_request, user_daily, global_daily) <= 0
            or user_limit > global_limit
            or user_daily > global_daily
        ):
            return [0, b"invalid_policy", 60]
        if request_units <= 0 or request_units > max_request:
            return [0, b"request_budget", 60]

        global_leases, user_leases, user_rpm, user_budget, global_budget = keys
        for lease_key in (global_leases, user_leases):
            self.leases[lease_key] = {
                member: expiry
                for member, expiry in self.leases[lease_key].items()
                if expiry > self.now_ms
            }
        if len(self.leases[global_leases]) >= global_limit:
            return [0, b"global_concurrency", 1]
        if len(self.leases[user_leases]) >= user_limit:
            return [0, b"user_concurrency", 1]

        minute_start = self.now_ms - 60_000
        self.rpm[user_rpm] = {
            member: timestamp
            for member, timestamp in self.rpm[user_rpm].items()
            if timestamp > minute_start
        }
        if len(self.rpm[user_rpm]) >= rpm_limit:
            oldest = min(self.rpm[user_rpm].values())
            return [0, b"rpm", max(1, math.ceil((oldest + 60_000 - self.now_ms) / 1000))]

        day = self.now_ms // 86_400_000
        user_used = self.budgets.get(user_budget, (day, 0))[1] if self.budgets.get(user_budget, (day, 0))[0] == day else 0
        global_used = self.budgets.get(global_budget, (day, 0))[1] if self.budgets.get(global_budget, (day, 0))[0] == day else 0
        day_retry = max(1, math.ceil(((day + 1) * 86_400_000 - self.now_ms) / 1000))
        if user_used + request_units > user_daily:
            return [0, b"user_daily_budget", day_retry]
        if global_used + request_units > global_daily:
            return [0, b"global_daily_budget", day_retry]

        token = str(token)
        expiry = self.now_ms + ttl_ms
        self.leases[global_leases][token] = expiry
        self.leases[user_leases][token] = expiry
        self.rpm[user_rpm][token] = self.now_ms
        self.budgets[user_budget] = (day, user_used + request_units)
        self.budgets[global_budget] = (day, global_used + request_units)
        return [1, token.encode(), expiry]

    def _release(self, keys: tuple[str, ...], args: tuple[object, ...]) -> int:
        assert len(keys) == 2
        token = str(args[0])
        removed = 0
        for key in keys:
            removed += int(self.leases[key].pop(token, None) is not None)
        return removed

    def _renew(self, keys: tuple[str, ...], args: tuple[object, ...]) -> list[object]:
        assert len(keys) == 2
        token = str(args[0])
        ttl_ms = int(args[1])
        if ttl_ms <= 0:
            return [0, b"invalid_ttl"]
        if any(token not in self.leases[key] for key in keys):
            return [0, b"lease_lost"]
        expiry = self.now_ms + ttl_ms
        for key in keys:
            self.leases[key][token] = expiry
        return [1, expiry]


def test_atomic_concurrency_limits_are_shared_across_backend_instances() -> None:
    redis = DeterministicScriptRedis()
    backends = [RedisModelResourceBackend(redis) for _ in range(12)]
    barrier = threading.Barrier(len(backends))

    def attempt(index: int):
        barrier.wait()
        try:
            return backends[index].acquire(f"seller-{index}", _policy(), 100)
        except ModelResourceLimitExceeded:
            return None

    with ThreadPoolExecutor(max_workers=len(backends)) as pool:
        leases = list(pool.map(attempt, range(len(backends))))

    admitted = [lease for lease in leases if lease is not None]
    assert len(admitted) == 3
    for lease in admitted:
        backends[0].release(lease)


def test_user_concurrency_release_and_expired_lease_recovery() -> None:
    redis = DeterministicScriptRedis()
    first = RedisModelResourceBackend(redis, lease_ttl_seconds=5)
    second = RedisModelResourceBackend(redis, lease_ttl_seconds=5)
    policy = _policy(user_concurrency=1)
    lease = first.acquire("same-seller", policy, 100)
    with pytest.raises(ModelResourceLimitExceeded, match="user model concurrency"):
        second.acquire("same-seller", policy, 100)
    first.release(lease)
    released_capacity = second.acquire("same-seller", policy, 100)
    second.release(released_capacity)

    first.acquire("crashed-worker", policy, 100)
    redis.advance(5_001)
    recovered = second.acquire("crashed-worker", policy, 100)
    assert recovered.identity == "crashed-worker"


def test_rpm_is_shared_and_reports_precise_retry_after() -> None:
    redis = DeterministicScriptRedis(now_ms=1_800_000_012_500)
    one = RedisModelResourceBackend(redis)
    two = RedisModelResourceBackend(redis)
    policy = _policy(user_requests_per_minute=2)
    for backend in (one, two):
        lease = backend.acquire("seller", policy, 100)
        backend.release(lease)
    redis.advance(10_100)
    with pytest.raises(ModelResourceLimitExceeded, match="quota") as rejected:
        one.acquire("seller", policy, 100)
    assert rejected.value.retry_after == 50
    redis.advance(49_900)
    lease = two.acquire("seller", policy, 100)
    assert lease.identity == "seller"


def test_daily_budgets_are_utc_day_scoped_and_atomic() -> None:
    redis = DeterministicScriptRedis(now_ms=20 * 86_400_000 + 86_399_000)
    first = RedisModelResourceBackend(redis)
    second = RedisModelResourceBackend(redis)
    policy = _policy(
        user_daily_budget_units=300,
        global_daily_budget_units=500,
        max_request_budget_units=300,
    )
    lease = first.acquire("seller-a", policy, 300)
    first.release(lease)
    with pytest.raises(ModelResourceLimitExceeded, match="user model daily budget") as user_limit:
        second.acquire("seller-a", policy, 1)
    assert user_limit.value.retry_after == 1
    lease = second.acquire("seller-b", policy, 200)
    second.release(lease)
    with pytest.raises(ModelResourceLimitExceeded, match="global model daily budget"):
        first.acquire("seller-c", policy, 1)

    redis.advance(1_001)
    next_day = first.acquire("seller-a", policy, 300)
    assert next_day.identity == "seller-a"


def test_request_budget_and_redis_failures_fail_closed_without_mutation() -> None:
    redis = DeterministicScriptRedis()
    backend = RedisModelResourceBackend(redis)
    with pytest.raises(ModelResourceLimitExceeded, match="outside the allowed range"):
        backend.acquire("seller", _policy(), 2_001)
    assert not redis.leases and not redis.rpm and not redis.budgets

    redis.failure = ConnectionError("redis unavailable")
    with pytest.raises(ConnectionError, match="unavailable"):
        backend.acquire("seller", _policy(), 100)


def test_unknown_script_response_fails_closed() -> None:
    class BadRedis:
        def eval(self, *_args: object) -> object:
            return [0, b"unrecognized-decision", 1]

    backend = RedisModelResourceBackend(BadRedis())
    with pytest.raises(RuntimeError, match="rejection response"):
        backend.acquire("seller", _policy(), 100)


def test_keys_hide_identity_and_share_one_cluster_hash_slot() -> None:
    redis = DeterministicScriptRedis()
    backend = RedisModelResourceBackend(redis, key_prefix="negin:test")
    lease = backend.acquire("seller@example.test", _policy(), 100)
    _, items = redis.calls[0]
    keys = [str(item) for item in items[:5]]
    assert all("seller@example.test" not in key for key in keys)
    assert all("{model-resource}" in key for key in keys)
    backend.release(lease)


def test_release_is_atomic_idempotent_and_propagates_redis_errors() -> None:
    redis = DeterministicScriptRedis()
    backend = RedisModelResourceBackend(redis)
    lease = backend.acquire("seller", _policy(), 100)
    backend.release(lease)
    backend.release(lease)
    assert [call[0] for call in redis.calls[-2:]] == [RELEASE_LUA, RELEASE_LUA]

    redis.failure = TimeoutError("release uncertain")
    with pytest.raises(TimeoutError, match="uncertain"):
        backend.release(lease)


def test_renewal_keeps_active_lease_counted_and_lost_lease_fails_closed() -> None:
    redis = DeterministicScriptRedis()
    backend = RedisModelResourceBackend(redis, lease_ttl_seconds=5)
    policy = _policy(user_concurrency=1)
    lease = backend.acquire("seller", policy, 100)

    redis.advance(4_000)
    backend.renew(lease)
    redis.advance(4_000)
    with pytest.raises(ModelResourceLimitExceeded, match="user model concurrency"):
        backend.acquire("seller", policy, 100)

    backend.release(lease)
    with pytest.raises(RuntimeError, match="lease renewal failed"):
        backend.renew(lease)
