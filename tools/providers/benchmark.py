"""Dry-run-first benchmark for OpenAI-compatible intent providers.

Only synthetic Persian intent-extraction fixtures are accepted. The tool never
records prompts, model output, authorization headers, or API-key values.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from app.ai_gateway import IntentEnvelope
from tools.providers.catalog import DOCUMENTED_CANDIDATES


DEFAULT_FIXTURES = Path(__file__).with_name("fixtures.json")
_ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{2,100}$")
_REDACTED = "[REDACTED]"


class ProviderBenchmarkSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    base_url: str = Field(min_length=8, max_length=500)
    model: str = Field(min_length=1, max_length=200)
    api_key_env: str = Field(min_length=3, max_length=100)
    supports_structured_json: bool = True
    input_cost_per_million: float | None = Field(default=None, ge=0)
    output_cost_per_million: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=1, max_length=20)
    timeout_seconds: float = Field(default=20.0, gt=0, le=120)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized.startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ValueError("base_url must use HTTPS (localhost is allowed for tests)")
        return normalized

    @field_validator("api_key_env")
    @classmethod
    def validate_api_key_env(cls, value: str) -> str:
        normalized = value.strip()
        if not _ENV_NAME.fullmatch(normalized):
            raise ValueError("api_key_env must be an uppercase environment variable name")
        return normalized

    @field_validator("input_cost_per_million", "output_cost_per_million")
    @classmethod
    def validate_finite_price(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("token prices must be finite")
        return value


@dataclass(frozen=True)
class SyntheticFixture:
    fixture_id: str
    message: str


@dataclass(frozen=True)
class BenchmarkObservation:
    fixture_id: str
    schema_valid: bool
    latency_ms: float
    error: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: float | None
    currency: str | None


class FixturePolicyError(ValueError):
    """Fixture data does not carry the mandatory synthetic-data declaration."""


def load_provider_specs(path: Path) -> tuple[ProviderBenchmarkSpec, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_providers = payload.get("providers") if isinstance(payload, dict) else None
    if not isinstance(raw_providers, list):
        raise ValueError("provider config must contain a providers array")
    providers = tuple(ProviderBenchmarkSpec.model_validate(item) for item in raw_providers)
    names = [provider.name.casefold() for provider in providers]
    if len(names) != len(set(names)):
        raise ValueError("provider names must be unique")
    return providers


def load_synthetic_fixtures(path: Path) -> tuple[SyntheticFixture, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("synthetic_only") is not True:
        raise FixturePolicyError("fixture file must declare synthetic_only=true")
    raw_fixtures = payload.get("fixtures")
    if not isinstance(raw_fixtures, list) or not raw_fixtures:
        raise FixturePolicyError("fixture file must contain at least one synthetic fixture")
    fixtures: list[SyntheticFixture] = []
    seen: set[str] = set()
    for item in raw_fixtures:
        if not isinstance(item, dict):
            raise FixturePolicyError("each fixture must be an object")
        fixture_id = str(item.get("id", "")).strip()
        message = " ".join(str(item.get("message", "")).split())
        if not fixture_id or fixture_id in seen or not message or len(message) > 4_000:
            raise FixturePolicyError("fixture ids must be unique and messages must be bounded")
        seen.add(fixture_id)
        fixtures.append(SyntheticFixture(fixture_id=fixture_id, message=message))
    return tuple(fixtures)


class OpenAICompatibleBenchmarkClient:
    def __init__(
        self,
        spec: ProviderBenchmarkSpec,
        *,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        if not api_key.strip():
            raise ValueError("provider API key is empty")
        self.spec = spec
        self._clock = clock
        self._client = httpx.Client(
            base_url=spec.base_url,
            headers={"Authorization": f"Bearer {api_key.strip()}"},
            timeout=spec.timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def run_fixture(self, fixture: SyntheticFixture) -> BenchmarkObservation:
        started = self._clock()
        try:
            response = self._client.post(
                "/chat/completions",
                json={
                    "model": self.spec.model,
                    "temperature": 0,
                    "max_tokens": 500,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Convert the synthetic Persian request to the strict JSON schema. "
                                "Do not answer, calculate, write SQL, choose tools, permissions, or commands."
                            ),
                        },
                        {"role": "user", "content": fixture.message},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "neginai_intent_envelope",
                            "strict": True,
                            "schema": IntentEnvelope.model_json_schema(),
                        },
                    },
                },
            )
            latency_ms = max(0.0, (self._clock() - started) * 1_000)
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            raw_envelope = json.loads(content) if isinstance(content, str) else content
            IntentEnvelope.model_validate(raw_envelope)
            usage = payload.get("usage") if isinstance(payload, dict) else None
            input_tokens, output_tokens, total_tokens = _usage_fields(usage)
            return BenchmarkObservation(
                fixture_id=fixture.fixture_id,
                schema_valid=True,
                latency_ms=latency_ms,
                error=None,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=_estimate_cost(self.spec, input_tokens, output_tokens),
                currency=self.spec.currency,
            )
        except httpx.TimeoutException:
            error = "timeout"
        except httpx.HTTPStatusError as exc:
            error = f"http_status_{exc.response.status_code}"
        except (json.JSONDecodeError, KeyError, IndexError, TypeError):
            error = "invalid_json_response"
        except ValidationError:
            error = "schema_invalid"
        except httpx.HTTPError:
            error = "network_error"
        latency_ms = max(0.0, (self._clock() - started) * 1_000)
        return BenchmarkObservation(
            fixture_id=fixture.fixture_id,
            schema_valid=False,
            latency_ms=latency_ms,
            error=error,
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            estimated_cost=None,
            currency=self.spec.currency,
        )


def _usage_fields(usage: Any) -> tuple[int | None, int | None, int | None]:
    if not isinstance(usage, dict):
        return None, None, None
    input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
    output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
    total_tokens = usage.get("total_tokens")

    def valid(value: Any) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None

    return valid(input_tokens), valid(output_tokens), valid(total_tokens)


def _estimate_cost(
    spec: ProviderBenchmarkSpec,
    input_tokens: int | None,
    output_tokens: int | None,
) -> float | None:
    if (
        input_tokens is None
        or output_tokens is None
        or spec.input_cost_per_million is None
        or spec.output_cost_per_million is None
    ):
        return None
    return (
        input_tokens * spec.input_cost_per_million
        + output_tokens * spec.output_cost_per_million
    ) / 1_000_000


def _percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize_provider(
    spec: ProviderBenchmarkSpec,
    observations: Sequence[BenchmarkObservation],
) -> dict[str, Any]:
    latencies = [observation.latency_ms for observation in observations]
    valid_count = sum(observation.schema_valid for observation in observations)
    costs = [
        observation.estimated_cost
        for observation in observations
        if observation.estimated_cost is not None
    ]
    return {
        "provider": spec.name,
        "model": spec.model,
        "supports_structured_json_configured": spec.supports_structured_json,
        "request_count": len(observations),
        "schema_valid_count": valid_count,
        "schema_valid_rate": valid_count / len(observations) if observations else 0.0,
        "latency_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "p99": _percentile(latencies, 0.99),
        },
        "errors": dict(sorted(Counter(o.error for o in observations if o.error).items())),
        "usage": {
            "input_tokens": sum(o.input_tokens or 0 for o in observations),
            "output_tokens": sum(o.output_tokens or 0 for o in observations),
            "total_tokens": sum(o.total_tokens or 0 for o in observations),
        },
        "estimated_cost": (
            sum(costs) if observations and len(costs) == len(observations) else None
        ),
        "currency": spec.currency,
        "observations": [asdict(observation) for observation in observations],
    }


def redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (_REDACTED if any(token in key.casefold() for token in ("api_key", "authorization", "secret", "token_value")) else redact_secrets(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item) for item in value]
    return value


def run_benchmark(
    providers: Sequence[ProviderBenchmarkSpec],
    fixtures: Sequence[SyntheticFixture],
    *,
    execute: bool,
    transport_factory: Callable[[ProviderBenchmarkSpec], httpx.BaseTransport | None] | None = None,
) -> dict[str, Any]:
    if not execute:
        return redact_secrets(
            {
                "mode": "dry_run",
                "network_calls_made": 0,
                "fixture_count": len(fixtures),
                "configured_providers": [
                    {
                        "name": spec.name,
                        "model": spec.model,
                        "api_key_env": spec.api_key_env,
                        "supports_structured_json": spec.supports_structured_json,
                        "price_configured": (
                            spec.input_cost_per_million is not None
                            and spec.output_cost_per_million is not None
                        ),
                    }
                    for spec in providers
                ],
                "documented_candidates": DOCUMENTED_CANDIDATES,
                "live_benchmark_status": "pending_explicit_execute_and_credentials",
            }
        )

    reports: list[dict[str, Any]] = []
    for spec in providers:
        api_key = os.environ.get(spec.api_key_env, "")
        if not api_key.strip():
            reports.append(
                {
                    "provider": spec.name,
                    "model": spec.model,
                    "status": "not_executed_missing_api_key_environment",
                    "api_key_env": spec.api_key_env,
                }
            )
            continue
        transport = transport_factory(spec) if transport_factory else None
        client = OpenAICompatibleBenchmarkClient(spec, api_key=api_key, transport=transport)
        try:
            observations = [client.run_fixture(fixture) for fixture in fixtures]
        finally:
            client.close()
        reports.append({"status": "executed", **summarize_provider(spec, observations)})
    return redact_secrets(
        {
            "mode": "execute",
            "dataset_policy": "synthetic_only",
            "providers": reports,
        }
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Benchmark OpenAI-compatible providers for strict intent JSON."
    )
    parser.add_argument("--config", type=Path, help="Local JSON provider configuration")
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--execute", action="store_true", help="Allow real, potentially paid API calls")
    parser.add_argument("--output", type=Path, help="Optional JSON result path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.execute and args.config is None:
        print("--execute requires --config", file=sys.stderr)
        return 2
    try:
        fixtures = load_synthetic_fixtures(args.fixtures)
        providers = load_provider_specs(args.config) if args.config else ()
        result = run_benchmark(providers, fixtures, execute=args.execute)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"configuration_error: {type(exc).__name__}", file=sys.stderr)
        return 2
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
