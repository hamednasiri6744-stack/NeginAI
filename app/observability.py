"""OpenTelemetry runtime with bounded, low-cardinality HTTP telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any
from urllib.parse import urlparse

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class ObservabilityConfigurationError(RuntimeError):
    pass


def _signal_endpoint(base: str, signal: str) -> str:
    clean = base.strip().rstrip("/")
    parsed = urlparse(clean)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ObservabilityConfigurationError("invalid OTLP endpoint")
    suffix = f"/v1/{signal}"
    return clean if parsed.path.endswith(suffix) else clean + suffix


@dataclass
class ObservabilityRuntime:
    tracer_provider: TracerProvider
    meter_provider: MeterProvider
    tracer: Any
    duration: Any
    requests: Any

    def shutdown(self) -> None:
        self.meter_provider.shutdown()
        self.tracer_provider.shutdown()


def configure_observability(
    *, service_name: str, environment: str, endpoint: str
) -> ObservabilityRuntime:
    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment.name": environment,
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=_signal_endpoint(endpoint, "traces")))
    )
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=_signal_endpoint(endpoint, "metrics")),
        export_interval_millis=30_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    tracer = tracer_provider.get_tracer("neginai.http")
    meter = meter_provider.get_meter("neginai.http")
    return ObservabilityRuntime(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        tracer=tracer,
        duration=meter.create_histogram(
            "http.server.request.duration", unit="s", description="HTTP server latency"
        ),
        requests=meter.create_counter(
            "http.server.request.count", description="HTTP server requests"
        ),
    )


def record_http(runtime: ObservabilityRuntime, attributes: dict[str, Any], seconds: float) -> None:
    runtime.requests.add(1, attributes)
    runtime.duration.record(seconds, attributes)


def monotonic_seconds() -> float:
    return perf_counter()
