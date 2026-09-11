from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from tools.providers.benchmark import (
    FixturePolicyError,
    OpenAICompatibleBenchmarkClient,
    ProviderBenchmarkSpec,
    SyntheticFixture,
    load_synthetic_fixtures,
    redact_secrets,
    run_benchmark,
    summarize_provider,
)


VALID_ENVELOPE = {
    "intent": "sales_summary",
    "entities": {},
    "time_range": {"kind": "today", "start": None, "end": None},
    "requested_metrics": ["net_sales"],
    "confidence": 0.98,
    "needs_clarification": False,
    "clarification_question": None,
}


def provider_spec(**overrides) -> ProviderBenchmarkSpec:
    values = {
        "name": "test-provider",
        "base_url": "https://provider.invalid/v1",
        "model": "configured-model",
        "api_key_env": "TEST_PROVIDER_KEY",
        "supports_structured_json": True,
        "input_cost_per_million": 1.0,
        "output_cost_per_million": 2.0,
        "currency": "configured-unit",
    }
    values.update(overrides)
    return ProviderBenchmarkSpec.model_validate(values)


def test_mock_transport_measures_valid_schema_usage_and_configured_cost():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer unit-test-secret"
        body = json.loads(request.content)
        assert body["response_format"]["type"] == "json_schema"
        assert "Do not answer" in body["messages"][0]["content"]
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": json.dumps(VALID_ENVELOPE)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
            },
        )

    client = OpenAICompatibleBenchmarkClient(
        provider_spec(),
        api_key="unit-test-secret",
        transport=httpx.MockTransport(handler),
    )
    try:
        observation = client.run_fixture(SyntheticFixture("synthetic-1", "فروش امروز"))
    finally:
        client.close()

    assert observation.schema_valid is True
    assert observation.error is None
    assert observation.input_tokens == 100
    assert observation.output_tokens == 20
    assert observation.estimated_cost == pytest.approx(0.00014)


def test_mock_transport_classifies_schema_failure_without_raw_response():
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"answer":"forbidden"}'}}]},
        )
    )
    client = OpenAICompatibleBenchmarkClient(
        provider_spec(), api_key="secret", transport=transport
    )
    try:
        observation = client.run_fixture(SyntheticFixture("synthetic-2", "یک درخواست ساختگی"))
    finally:
        client.close()

    assert observation.schema_valid is False
    assert observation.error == "schema_invalid"
    assert "answer" not in json.dumps(observation.__dict__)


def test_dry_run_never_reads_key_or_constructs_transport(monkeypatch):
    monkeypatch.setenv("TEST_PROVIDER_KEY", "must-not-appear")
    called = False

    def forbidden_transport(_spec):
        nonlocal called
        called = True
        raise AssertionError("dry-run attempted network setup")

    result = run_benchmark(
        [provider_spec()],
        [SyntheticFixture("synthetic", "داده ساختگی")],
        execute=False,
        transport_factory=forbidden_transport,
    )

    assert called is False
    assert result["network_calls_made"] == 0
    assert "must-not-appear" not in json.dumps(result)
    assert result["live_benchmark_status"] == "pending_explicit_execute_and_credentials"


def test_execute_uses_mock_transport_and_report_has_percentiles(monkeypatch):
    monkeypatch.setenv("TEST_PROVIDER_KEY", "mock-key")
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": VALID_ENVELOPE}}],
                "usage": {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7},
            },
        )
    )
    result = run_benchmark(
        [provider_spec()],
        [SyntheticFixture("one", "نمونه یک"), SyntheticFixture("two", "نمونه دو")],
        execute=True,
        transport_factory=lambda _spec: transport,
    )

    report = result["providers"][0]
    assert report["status"] == "executed"
    assert report["schema_valid_rate"] == 1.0
    assert set(report["latency_ms"]) == {"p50", "p95", "p99"}
    assert report["usage"] == {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14}
    assert "mock-key" not in json.dumps(result)


def test_fixture_loader_refuses_files_without_synthetic_declaration(tmp_path: Path):
    path = tmp_path / "unsafe.json"
    path.write_text(
        json.dumps({"fixtures": [{"id": "unknown", "message": "ممکن است واقعی باشد"}]}),
        encoding="utf-8",
    )

    with pytest.raises(FixturePolicyError, match="synthetic_only"):
        load_synthetic_fixtures(path)


def test_summary_marks_cost_unknown_when_price_or_usage_is_unknown():
    spec = provider_spec(input_cost_per_million=None, output_cost_per_million=None)
    summary = summarize_provider(spec, [])
    assert summary["estimated_cost"] is None
    assert summary["latency_ms"] == {"p50": None, "p95": None, "p99": None}


def test_recursive_redaction_removes_key_values():
    redacted = redact_secrets(
        {"authorization": "Bearer secret", "nested": {"api_key": "secret", "ok": 1}}
    )
    assert redacted == {
        "authorization": "[REDACTED]",
        "nested": {"api_key": "[REDACTED]", "ok": 1},
    }

