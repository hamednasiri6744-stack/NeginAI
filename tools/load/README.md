# NeginAI read-only load harness

This harness measures a bounded read-only workload with `asyncio` and `httpx`.
It only sends `GET`, never follows redirects, defaults to local `/health`, and
does not log credential values.

Run against a locally started service:

```powershell
.\.venv\Scripts\python.exe -m tools.load.harness `
  --base-url http://127.0.0.1:8006 `
  --concurrency 200 `
  --iterations 10 `
  --ramp-seconds 30 `
  --warmup-requests 20 `
  --max-error-rate 0.01 `
  --max-p95-ms 1000 `
  --min-throughput-rps 20 `
  --output artifacts/load/local-health.json
```

Use `--endpoint /some/read-only-path` repeatedly to distribute requests over
other read-only endpoints. There is intentionally no method or mutation flag.
Absolute endpoint URLs are rejected.

Remote targets require `--allow-remote`; remote cleartext HTTP additionally
requires `--allow-insecure-http`. Those switches are acknowledgements, not
authorization to test a production service. Obtain the system owner's approval
and choose safe limits before any non-local run.

For an authenticated read-only endpoint, put the value in an environment
variable and identify only its name:

```powershell
$env:NEGIN_LOAD_KEY = '<secret>'
.\.venv\Scripts\python.exe -m tools.load.harness `
  --endpoint /health/readiness `
  --header-name X-API-Key `
  --header-env NEGIN_LOAD_KEY
```

The JSON result contains p50/p95/p99 latency, throughput, status/error counts,
and every threshold decision. Exit code `0` means all gates passed, `1` means a
performance gate failed, and `2` means the command was invalid.
