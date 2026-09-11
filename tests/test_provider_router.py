from __future__ import annotations

import pytest

from app.provider_router import (
    DeterministicProviderRouter,
    NoEligibleProvider,
    ProviderRouteSpec,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance_ms(self, milliseconds: float) -> None:
        self.value += milliseconds / 1_000


def test_router_requires_structured_json_latency_budget_and_uses_lowest_known_price():
    router = DeterministicProviderRouter(
        [
            ProviderRouteSpec(
                name="unsupported-cheap",
                supports_structured_json=False,
                input_cost_per_million=0,
                output_cost_per_million=0,
            ),
            ProviderRouteSpec(
                name="too-slow",
                supports_structured_json=True,
                observed_p95_latency_ms=2_001,
                input_cost_per_million=0.1,
                output_cost_per_million=0.1,
            ),
            ProviderRouteSpec(
                name="priced-high",
                supports_structured_json=True,
                observed_p95_latency_ms=800,
                input_cost_per_million=4,
                output_cost_per_million=8,
            ),
            ProviderRouteSpec(
                name="priced-low",
                supports_structured_json=True,
                observed_p95_latency_ms=900,
                input_cost_per_million=1,
                output_cost_per_million=2,
            ),
        ],
        max_latency_ms=2_000,
    )

    candidates = router.ordered_candidates(input_tokens=300, output_tokens=100)

    assert [candidate.name for candidate in candidates] == ["priced-low", "priced-high"]


def test_router_falls_back_on_invalid_schema_without_returning_bad_value():
    clock = FakeClock()
    router = DeterministicProviderRouter(
        [
            ProviderRouteSpec("first", True, input_cost_per_million=1, output_cost_per_million=1),
            ProviderRouteSpec("second", True, input_cost_per_million=2, output_cost_per_million=2),
        ],
        max_latency_ms=500,
        clock=clock,
    )

    def execute(provider: ProviderRouteSpec) -> dict[str, str]:
        clock.advance_ms(10)
        return {"intent": "valid"} if provider.name == "second" else {"bad": "shape"}

    result = router.route(
        execute,
        schema_validator=lambda value: set(value) == {"intent"},
        input_tokens=100,
        output_tokens=20,
    )

    assert result.provider == "second"
    assert result.value == {"intent": "valid"}
    assert result.attempted_providers == ("first", "second")


def test_router_opens_circuit_then_allows_probe_after_cooldown():
    clock = FakeClock()
    router = DeterministicProviderRouter(
        [ProviderRouteSpec("only", True, input_cost_per_million=1, output_cost_per_million=1)],
        max_latency_ms=100,
        failure_threshold=1,
        cooldown_seconds=5,
        clock=clock,
    )

    with pytest.raises(NoEligibleProvider):
        router.route(
            lambda _provider: (_ for _ in ()).throw(RuntimeError("safe test failure")),
            schema_validator=lambda _value: True,
            input_tokens=10,
            output_tokens=10,
        )

    assert router.ordered_candidates(input_tokens=10, output_tokens=10) == ()
    clock.value = 5.1
    assert [item.name for item in router.ordered_candidates(input_tokens=10, output_tokens=10)] == [
        "only"
    ]


def test_router_rejects_runtime_latency_over_budget_and_falls_back():
    clock = FakeClock()
    router = DeterministicProviderRouter(
        [
            ProviderRouteSpec("cheap", True, input_cost_per_million=1, output_cost_per_million=1),
            ProviderRouteSpec("fallback", True, input_cost_per_million=2, output_cost_per_million=2),
        ],
        max_latency_ms=100,
        clock=clock,
    )

    def execute(provider: ProviderRouteSpec) -> str:
        clock.advance_ms(101 if provider.name == "cheap" else 5)
        return provider.name

    result = router.route(
        execute,
        schema_validator=lambda _value: True,
        input_tokens=1,
        output_tokens=1,
    )

    assert result.provider == "fallback"
    assert result.attempted_providers == ("cheap", "fallback")


def test_router_rejects_duplicate_names_and_invalid_prices():
    with pytest.raises(ValueError, match="unique"):
        DeterministicProviderRouter(
            [ProviderRouteSpec("same", True), ProviderRouteSpec("SAME", True)],
            max_latency_ms=100,
        )
    with pytest.raises(ValueError, match="prices"):
        ProviderRouteSpec("bad", True, input_cost_per_million=-1)

