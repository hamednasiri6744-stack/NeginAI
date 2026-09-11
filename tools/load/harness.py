"""Read-only asyncio/httpx load harness for NeginAI.

The harness deliberately exposes no HTTP method option: every request is GET,
redirects are disabled, and absolute endpoint URLs are rejected.  It is safe to
import from tests; network traffic occurs only when ``run_load_test`` is called.
"""

from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import math
import os
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Mapping, Sequence
from urllib.parse import urlsplit

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8006"
DEFAULT_ENDPOINT = "/health"


@dataclass(frozen=True)
class LoadConfig:
    """Validated settings for one bounded, read-only load run."""

    base_url: str = DEFAULT_BASE_URL
    endpoints: tuple[str, ...] = (DEFAULT_ENDPOINT,)
    concurrency: int = 200
    iterations: int = 1
    ramp_seconds: float = 10.0
    timeout_seconds: float = 10.0
    warmup_requests: int = 5
    header_name: str = "X-API-Key"
    header_env: str = "NEGIN_ACTION_API_KEY"
    max_error_rate: float = 0.01
    max_p95_ms: float = 1_000.0
    min_throughput_rps: float = 1.0

    @property
    def total_requests(self) -> int:
        return self.concurrency * self.iterations


def percentile(values: Sequence[float], percentile_value: float) -> float:
    """Return a nearest-rank percentile, suitable for latency SLO reporting."""

    if not values:
        return 0.0
    if not 0 <= percentile_value <= 100:
        raise ValueError("percentile must be between 0 and 100")
    ordered = sorted(values)
    if percentile_value == 0:
        return float(ordered[0])
    rank = math.ceil((percentile_value / 100.0) * len(ordered))
    return float(ordered[max(0, rank - 1)])


def redact_text(value: object, secrets: Sequence[str]) -> str:
    """Remove configured secret values from bounded diagnostic text."""

    redacted = str(value)
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted[:300]


def validate_endpoint(endpoint: str) -> str:
    """Accept only origin-relative paths; an absolute URL could bypass base_url."""

    parsed = urlsplit(endpoint)
    if not endpoint.startswith("/") or endpoint.startswith("//"):
        raise ValueError(f"endpoint must be an origin-relative path: {endpoint!r}")
    if parsed.scheme or parsed.netloc or parsed.fragment:
        raise ValueError(f"endpoint must not contain a scheme, host, or fragment: {endpoint!r}")
    return endpoint


def validate_base_url(
    base_url: str,
    *,
    allow_remote: bool,
    allow_insecure_http: bool,
) -> str:
    """Guard accidental production traffic and cleartext remote credentials."""

    parsed = urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("base URL must be an http(s) origin")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("base URL must not contain credentials, query, or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("base URL must not contain a path; use --endpoint")

    hostname = parsed.hostname.lower().rstrip(".")
    is_loopback = hostname == "localhost"
    try:
        is_loopback = is_loopback or ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        pass

    if not is_loopback and not allow_remote:
        raise ValueError("remote targets require the explicit --allow-remote flag")
    if not is_loopback and parsed.scheme != "https" and not allow_insecure_http:
        raise ValueError("remote HTTP requires the explicit --allow-insecure-http flag")
    return base_url.rstrip("/")


def resolve_headers(
    config: LoadConfig,
    environ: Mapping[str, str] | None = None,
) -> tuple[dict[str, str], tuple[str, ...]]:
    """Resolve an optional credential without ever returning it as metadata."""

    source = os.environ if environ is None else environ
    secret = source.get(config.header_env, "")
    if not secret:
        return {}, ()
    return {config.header_name: secret}, (secret,)


def evaluate_thresholds(
    *,
    error_rate: float,
    p95_ms: float,
    throughput_rps: float,
    config: LoadConfig,
) -> dict[str, dict[str, float | bool | str]]:
    """Evaluate deterministic pass/fail gates for automation and CI."""

    return {
        "error_rate": {
            "operator": "<=",
            "observed": round(error_rate, 6),
            "limit": config.max_error_rate,
            "passed": error_rate <= config.max_error_rate,
        },
        "p95_ms": {
            "operator": "<=",
            "observed": round(p95_ms, 3),
            "limit": config.max_p95_ms,
            "passed": p95_ms <= config.max_p95_ms,
        },
        "throughput_rps": {
            "operator": ">=",
            "observed": round(throughput_rps, 3),
            "limit": config.min_throughput_rps,
            "passed": throughput_rps >= config.min_throughput_rps,
        },
    }


async def run_load_test(
    config: LoadConfig,
    *,
    transport: httpx.AsyncBaseTransport | None = None,
    environ: Mapping[str, str] | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict[str, object]:
    """Run one bounded load test and return a secret-safe JSON-compatible report."""

    _validate_config(config)
    headers, secrets = resolve_headers(config, environ)
    limits = httpx.Limits(
        max_connections=config.concurrency,
        max_keepalive_connections=config.concurrency,
    )
    timeout = httpx.Timeout(config.timeout_seconds)
    latencies_ms: list[float] = []
    status_codes: Counter[str] = Counter()
    error_types: Counter[str] = Counter()
    error_samples: list[str] = []
    semaphore = asyncio.Semaphore(config.concurrency)

    async with httpx.AsyncClient(
        base_url=config.base_url,
        headers=headers,
        timeout=timeout,
        limits=limits,
        transport=transport,
        follow_redirects=False,
        # A developer machine may define an outbound HTTP proxy. Load traffic
        # must reach the explicitly validated target directly, especially for
        # localhost, and must not leak authentication headers to that proxy.
        trust_env=False,
    ) as client:
        for index in range(config.warmup_requests):
            endpoint = config.endpoints[index % len(config.endpoints)]
            try:
                await client.get(endpoint)
            except httpx.HTTPError:
                # Warmup primes connections and is deliberately excluded from gates.
                pass

        async def one_request(index: int) -> None:
            if config.ramp_seconds > 0 and config.total_requests > 1:
                await sleep(config.ramp_seconds * index / (config.total_requests - 1))
            endpoint = config.endpoints[index % len(config.endpoints)]
            async with semaphore:
                started = time.perf_counter()
                try:
                    response = await client.get(endpoint)
                    elapsed_ms = (time.perf_counter() - started) * 1_000
                    latencies_ms.append(elapsed_ms)
                    status_codes[str(response.status_code)] += 1
                    if not 200 <= response.status_code < 400:
                        error_types["http_status"] += 1
                        if len(error_samples) < 5:
                            error_samples.append(f"HTTP {response.status_code} for {endpoint}")
                except httpx.HTTPError as exc:
                    elapsed_ms = (time.perf_counter() - started) * 1_000
                    latencies_ms.append(elapsed_ms)
                    error_types[type(exc).__name__] += 1
                    if len(error_samples) < 5:
                        error_samples.append(redact_text(exc, secrets))

        measured_started = time.perf_counter()
        await asyncio.gather(*(one_request(index) for index in range(config.total_requests)))
        duration_seconds = max(time.perf_counter() - measured_started, 1e-9)

    failures = sum(error_types.values())
    error_rate = failures / config.total_requests
    throughput_rps = config.total_requests / duration_seconds
    p50_ms = percentile(latencies_ms, 50)
    p95_ms = percentile(latencies_ms, 95)
    p99_ms = percentile(latencies_ms, 99)
    thresholds = evaluate_thresholds(
        error_rate=error_rate,
        p95_ms=p95_ms,
        throughput_rps=throughput_rps,
        config=config,
    )
    passed = all(bool(gate["passed"]) for gate in thresholds.values())

    return {
        "schema_version": 1,
        "result": "PASS" if passed else "FAIL",
        "read_only": True,
        "method": "GET",
        "target": {
            "base_url": config.base_url,
            "endpoints": list(config.endpoints),
            "redirects_followed": False,
            "credential_header": config.header_name if headers else None,
            "credential_source_env": config.header_env if headers else None,
            "credential_configured": bool(headers),
        },
        "workload": {
            "concurrency": config.concurrency,
            "iterations_per_worker": config.iterations,
            "measured_requests": config.total_requests,
            "warmup_requests": config.warmup_requests,
            "ramp_seconds": config.ramp_seconds,
            "timeout_seconds": config.timeout_seconds,
        },
        "metrics": {
            "duration_seconds": round(duration_seconds, 6),
            "throughput_rps": round(throughput_rps, 3),
            "successful_requests": config.total_requests - failures,
            "failed_requests": failures,
            "error_rate": round(error_rate, 6),
            "latency_ms": {
                "p50": round(p50_ms, 3),
                "p95": round(p95_ms, 3),
                "p99": round(p99_ms, 3),
                "min": round(min(latencies_ms), 3) if latencies_ms else 0.0,
                "max": round(max(latencies_ms), 3) if latencies_ms else 0.0,
            },
            "status_codes": dict(sorted(status_codes.items())),
            "error_types": dict(sorted(error_types.items())),
            "error_samples": [redact_text(sample, secrets) for sample in error_samples],
        },
        "thresholds": thresholds,
    }


def _validate_config(config: LoadConfig) -> None:
    if not 1 <= config.concurrency <= 10_000:
        raise ValueError("concurrency must be between 1 and 10000")
    if not 1 <= config.iterations <= 1_000_000:
        raise ValueError("iterations must be between 1 and 1000000")
    if config.total_requests > 5_000_000:
        raise ValueError("total measured requests must not exceed 5000000")
    numeric_limits = (
        config.ramp_seconds,
        config.timeout_seconds,
        config.max_error_rate,
        config.max_p95_ms,
        config.min_throughput_rps,
    )
    if not all(math.isfinite(value) for value in numeric_limits):
        raise ValueError("numeric settings must be finite")
    if config.ramp_seconds < 0 or config.timeout_seconds <= 0 or config.warmup_requests < 0:
        raise ValueError("ramp/warmup cannot be negative and timeout must be positive")
    if not 0 <= config.max_error_rate <= 1:
        raise ValueError("max error rate must be between 0 and 1")
    if config.max_p95_ms <= 0 or config.min_throughput_rps < 0:
        raise ValueError("latency limit must be positive and throughput limit non-negative")
    if not config.header_name or "\n" in config.header_name or "\r" in config.header_name:
        raise ValueError("header name is invalid")
    if not config.header_env:
        raise ValueError("header env name cannot be empty")
    for endpoint in config.endpoints:
        validate_endpoint(endpoint)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bounded, GET-only load/soak harness for NeginAI.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument(
        "--endpoint",
        action="append",
        dest="endpoints",
        help="Origin-relative, read-only GET path. Repeat to distribute requests.",
    )
    parser.add_argument("--concurrency", type=int, default=200)
    parser.add_argument("--iterations", type=int, default=1, help="Measured requests per worker.")
    parser.add_argument("--ramp-seconds", type=float, default=10.0)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--warmup-requests", type=int, default=5)
    parser.add_argument("--header-name", default="X-API-Key")
    parser.add_argument("--header-env", default="NEGIN_ACTION_API_KEY")
    parser.add_argument("--max-error-rate", type=float, default=0.01)
    parser.add_argument("--max-p95-ms", type=float, default=1_000.0)
    parser.add_argument("--min-throughput-rps", type=float, default=1.0)
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Acknowledge that the target is not localhost. Obtain authorization first.",
    )
    parser.add_argument(
        "--allow-insecure-http",
        action="store_true",
        help="Acknowledge cleartext HTTP to a remote target. Secrets may be exposed in transit.",
    )
    parser.add_argument("--output", type=Path, help="Also write the JSON report to this file.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        base_url = validate_base_url(
            args.base_url,
            allow_remote=args.allow_remote,
            allow_insecure_http=args.allow_insecure_http,
        )
        config = LoadConfig(
            base_url=base_url,
            endpoints=tuple(args.endpoints or [DEFAULT_ENDPOINT]),
            concurrency=args.concurrency,
            iterations=args.iterations,
            ramp_seconds=args.ramp_seconds,
            timeout_seconds=args.timeout_seconds,
            warmup_requests=args.warmup_requests,
            header_name=args.header_name,
            header_env=args.header_env,
            max_error_rate=args.max_error_rate,
            max_p95_ms=args.max_p95_ms,
            min_throughput_rps=args.min_throughput_rps,
        )
        _validate_config(config)
        report = asyncio.run(run_load_test(config))
    except (ValueError, httpx.HTTPError) as exc:
        error = {"schema_version": 1, "result": "CONFIG_ERROR", "error": redact_text(exc, ())}
        print(json.dumps(error, ensure_ascii=False, indent=2))
        return 2

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
