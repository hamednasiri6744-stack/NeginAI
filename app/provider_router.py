"""Deterministic, provider-neutral routing for structured intent extraction.

Remote models are candidates only when they support the application's strict
JSON contract.  They never receive authority to answer, calculate, query data,
or select tools.  The router applies latency, price, and circuit-breaker policy
before returning a model-produced intent envelope to the application.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from threading import Lock
from typing import Callable, Generic, Sequence, TypeVar


T = TypeVar("T")


class NoEligibleProvider(RuntimeError):
    """No provider can currently satisfy the routing policy."""


@dataclass(frozen=True)
class ProviderRouteSpec:
    name: str
    supports_structured_json: bool
    observed_p95_latency_ms: float | None = None
    input_cost_per_million: float | None = None
    output_cost_per_million: float | None = None
    priority: int = 100

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("provider name is required")
        if self.observed_p95_latency_ms is not None and (
            not math.isfinite(self.observed_p95_latency_ms)
            or self.observed_p95_latency_ms < 0
        ):
            raise ValueError("observed p95 latency must be finite and non-negative")
        for value in (self.input_cost_per_million, self.output_cost_per_million):
            if value is not None and (not math.isfinite(value) or value < 0):
                raise ValueError("provider token prices must be finite and non-negative")

    def estimated_cost(self, *, input_tokens: int, output_tokens: int) -> float:
        if self.input_cost_per_million is None or self.output_cost_per_million is None:
            return math.inf
        return (
            input_tokens * self.input_cost_per_million
            + output_tokens * self.output_cost_per_million
        ) / 1_000_000


@dataclass(frozen=True)
class ProviderRouteResult(Generic[T]):
    value: T
    provider: str
    latency_ms: float
    attempted_providers: tuple[str, ...]


@dataclass
class _CircuitState:
    consecutive_failures: int = 0
    open_until: float = 0.0
    last_latency_ms: float | None = None


class DeterministicProviderRouter:
    """Select and fail over among strict-JSON intent providers.

    Candidate ordering is stable: structured-JSON capability is mandatory,
    circuits and previously observed latency are eligibility gates, then known
    estimated price, configured priority, and name determine order.
    """

    def __init__(
        self,
        providers: Sequence[ProviderRouteSpec],
        *,
        max_latency_ms: float,
        failure_threshold: int = 2,
        cooldown_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not math.isfinite(max_latency_ms) or max_latency_ms <= 0:
            raise ValueError("max_latency_ms must be positive and finite")
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least one")
        if not math.isfinite(cooldown_seconds) or cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be finite and non-negative")

        normalized = tuple(providers)
        names = [provider.name.casefold() for provider in normalized]
        if len(names) != len(set(names)):
            raise ValueError("provider names must be unique")
        self._providers = normalized
        self.max_latency_ms = max_latency_ms
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._clock = clock
        self._states = {provider.name: _CircuitState() for provider in normalized}
        self._lock = Lock()

    def ordered_candidates(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
    ) -> tuple[ProviderRouteSpec, ...]:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token estimates must be non-negative")
        now = self._clock()
        with self._lock:
            eligible = [
                provider
                for provider in self._providers
                if provider.supports_structured_json
                and self._states[provider.name].open_until <= now
                and (
                    provider.observed_p95_latency_ms is None
                    or provider.observed_p95_latency_ms <= self.max_latency_ms
                )
            ]
        return tuple(
            sorted(
                eligible,
                key=lambda provider: (
                    provider.estimated_cost(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                    ),
                    provider.priority,
                    provider.name.casefold(),
                ),
            )
        )

    def route(
        self,
        executor: Callable[[ProviderRouteSpec], T],
        *,
        schema_validator: Callable[[T], bool],
        input_tokens: int,
        output_tokens: int,
    ) -> ProviderRouteResult[T]:
        candidates = self.ordered_candidates(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        if not candidates:
            raise NoEligibleProvider("no structured-JSON provider is currently eligible")

        attempted: list[str] = []
        for provider in candidates:
            attempted.append(provider.name)
            started = self._clock()
            try:
                value = executor(provider)
                latency_ms = max(0.0, (self._clock() - started) * 1_000)
                if latency_ms > self.max_latency_ms:
                    self._record_failure(provider.name, latency_ms=latency_ms)
                    continue
                if not schema_validator(value):
                    self._record_failure(provider.name, latency_ms=latency_ms)
                    continue
            except Exception:
                latency_ms = max(0.0, (self._clock() - started) * 1_000)
                self._record_failure(provider.name, latency_ms=latency_ms)
                continue

            self._record_success(provider.name, latency_ms=latency_ms)
            return ProviderRouteResult(
                value=value,
                provider=provider.name,
                latency_ms=latency_ms,
                attempted_providers=tuple(attempted),
            )

        raise NoEligibleProvider(
            "all eligible structured-JSON providers failed policy validation"
        )

    def _record_failure(self, provider_name: str, *, latency_ms: float) -> None:
        now = self._clock()
        with self._lock:
            state = self._states[provider_name]
            state.last_latency_ms = latency_ms
            state.consecutive_failures += 1
            if state.consecutive_failures >= self.failure_threshold:
                state.open_until = now + self.cooldown_seconds

    def _record_success(self, provider_name: str, *, latency_ms: float) -> None:
        with self._lock:
            state = self._states[provider_name]
            state.last_latency_ms = latency_ms
            state.consecutive_failures = 0
            state.open_until = 0.0
