import asyncio
import json

import httpx
import pytest

import tools.load.harness as harness
from tools.load.harness import (
    LoadConfig,
    evaluate_thresholds,
    percentile,
    redact_text,
    run_load_test,
    validate_base_url,
    validate_endpoint,
)


def test_percentile_uses_nearest_rank_for_slo_boundaries():
    samples = list(range(1, 101))

    assert percentile(samples, 0) == 1
    assert percentile(samples, 50) == 50
    assert percentile(samples, 95) == 95
    assert percentile(samples, 99) == 99
    assert percentile([], 95) == 0


def test_defaults_are_bounded_to_200_read_only_local_health_requests():
    config = LoadConfig()

    assert config.concurrency == 200
    assert config.total_requests == 200
    assert config.base_url == "http://127.0.0.1:8006"
    assert config.endpoints == ("/health",)


def test_redaction_removes_every_secret_and_bounds_diagnostics():
    message = "Authorization=top-secret; mirror=top-secret; " + ("x" * 500)

    result = redact_text(message, ("top-secret",))

    assert "top-secret" not in result
    assert result.count("[REDACTED]") == 2
    assert len(result) == 300


def test_endpoint_and_remote_target_safety_guards():
    assert validate_endpoint("/health?probe=1") == "/health?probe=1"
    with pytest.raises(ValueError, match="origin-relative"):
        validate_endpoint("https://example.test/health")
    with pytest.raises(ValueError, match="origin-relative"):
        validate_endpoint("//example.test/health")
    with pytest.raises(ValueError, match="allow-remote"):
        validate_base_url(
            "https://example.test",
            allow_remote=False,
            allow_insecure_http=False,
        )
    with pytest.raises(ValueError, match="allow-insecure-http"):
        validate_base_url(
            "http://example.test",
            allow_remote=True,
            allow_insecure_http=False,
        )


def test_thresholds_report_each_gate_and_fail_closed():
    config = LoadConfig(max_error_rate=0.01, max_p95_ms=100, min_throughput_rps=20)

    gates = evaluate_thresholds(
        error_rate=0.02,
        p95_ms=99,
        throughput_rps=19,
        config=config,
    )

    assert gates["error_rate"]["passed"] is False
    assert gates["p95_ms"]["passed"] is True
    assert gates["throughput_rps"]["passed"] is False
    assert not all(gate["passed"] for gate in gates.values())


def test_mock_transport_proves_concurrency_metrics_and_secret_redaction():
    active = 0
    maximum_active = 0
    lock = asyncio.Lock()
    secret = "do-not-print-this-key"

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, maximum_active
        assert request.method == "GET"
        assert request.headers["X-Test-Key"] == secret
        async with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        await asyncio.sleep(0.01)
        async with lock:
            active -= 1
        return httpx.Response(200, json={"status": "ok"})

    config = LoadConfig(
        base_url="https://load.test",
        endpoints=("/health",),
        concurrency=4,
        iterations=3,
        ramp_seconds=0,
        timeout_seconds=1,
        warmup_requests=2,
        header_name="X-Test-Key",
        header_env="LOAD_TEST_SECRET",
        max_error_rate=0,
        max_p95_ms=500,
        min_throughput_rps=1,
    )
    report = asyncio.run(
        run_load_test(
            config,
            transport=httpx.MockTransport(handler),
            environ={"LOAD_TEST_SECRET": secret},
        )
    )

    assert maximum_active == 4
    assert report["result"] == "PASS"
    assert report["workload"]["measured_requests"] == 12
    assert report["metrics"]["successful_requests"] == 12
    assert report["metrics"]["failed_requests"] == 0
    assert report["metrics"]["latency_ms"]["p95"] > 0
    assert report["target"]["credential_configured"] is True
    assert secret not in json.dumps(report)


def test_http_failures_drive_json_exit_gate_without_leaking_credentials():
    secret = "private-load-key"

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text=f"upstream rejected {secret}")

    config = LoadConfig(
        base_url="https://load.test",
        concurrency=2,
        iterations=2,
        ramp_seconds=0,
        warmup_requests=0,
        header_env="LOAD_SECRET",
        max_error_rate=0,
        max_p95_ms=1_000,
        min_throughput_rps=0,
    )
    report = asyncio.run(
        run_load_test(
            config,
            transport=httpx.MockTransport(handler),
            environ={"LOAD_SECRET": secret},
        )
    )

    assert report["result"] == "FAIL"
    assert report["metrics"]["failed_requests"] == 4
    assert report["thresholds"]["error_rate"]["passed"] is False
    assert secret not in json.dumps(report)


def test_cli_exit_code_is_one_when_a_measured_gate_fails(monkeypatch, capsys):
    async def fake_run(config):
        return {"schema_version": 1, "result": "FAIL", "thresholds": {}}

    monkeypatch.setattr(harness, "run_load_test", fake_run)

    exit_code = harness.main(
        [
            "--base-url",
            "http://127.0.0.1:8006",
            "--concurrency",
            "1",
            "--warmup-requests",
            "0",
            "--ramp-seconds",
            "0",
        ]
    )

    assert exit_code == 1
    assert json.loads(capsys.readouterr().out)["result"] == "FAIL"
