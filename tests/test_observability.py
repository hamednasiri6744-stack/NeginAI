import pytest

from app.observability import ObservabilityConfigurationError, _signal_endpoint


def test_signal_endpoint_appends_standard_otlp_http_paths():
    assert _signal_endpoint("http://127.0.0.1:4318", "traces") == (
        "http://127.0.0.1:4318/v1/traces"
    )
    assert _signal_endpoint("https://otel.example/v1/metrics", "metrics") == (
        "https://otel.example/v1/metrics"
    )


@pytest.mark.parametrize("endpoint", ["", "collector:4318", "file:///tmp/otel"])
def test_invalid_otlp_endpoint_fails_closed(endpoint):
    with pytest.raises(ObservabilityConfigurationError):
        _signal_endpoint(endpoint, "traces")
