# NeginAI provider benchmark

This benchmark compares OpenAI-compatible gateways only for strict structured
intent extraction. A provider is not allowed to answer business questions,
calculate metrics, produce SQL, choose permissions, select tools, or create
commands. All authoritative work remains inside NeginAI.

## Safety defaults

- Dry-run is the default and makes zero network calls.
- Real calls require the explicit `--execute` flag and may incur charges.
- API keys are read only from the environment variable named in local config.
- The bundled Persian fixtures are synthetic and contain no customer data.
- Results contain fixture IDs and metrics, never prompts, raw model responses,
  authorization headers, or API-key values.
- Endpoint, model ID, and token prices are never guessed. Configure current
  values from the provider console; absent prices remain `null`.

## Official-source notes (checked 2026-09-02)

- AvalAI documents use of official OpenAI-compatible SDKs with a custom base
  URL and environment-based API keys: <https://docs.avalai.ir/en/libraries>.
  Current models and prices must still be verified in its current documentation
  or console before a paid run.
- Liara's official AI product page describes centralized model access and
  usage/latency monitoring: <https://liara.ir/products/ai>. Its current plan and
  model-cost information is published at <https://liara.ir/pricing>; copy the
  current endpoint, model identifier, and applicable prices from the console.

These are candidate notes, not endorsements. A live benchmark remains pending
until explicit execution is authorized and valid credentials are supplied.

## Run

Inspect the built-in candidate catalog without a provider configuration:

```powershell
.\.venv\Scripts\python.exe -m tools.providers.benchmark
```

Create a private local JSON config (do not commit it):

```json
{
  "providers": [
    {
      "name": "provider-name",
      "base_url": "https://current-provider-endpoint.example/v1",
      "model": "current-model-id",
      "api_key_env": "PROVIDER_API_KEY",
      "supports_structured_json": true,
      "input_cost_per_million": null,
      "output_cost_per_million": null,
      "currency": null,
      "timeout_seconds": 20
    }
  ]
}
```

Validate the config and fixture set without making calls:

```powershell
.\.venv\Scripts\python.exe -m tools.providers.benchmark --config .\private-providers.json
```

Only after approval, set each configured environment variable and explicitly
allow potentially paid calls:

```powershell
.\.venv\Scripts\python.exe -m tools.providers.benchmark --config .\private-providers.json --execute --output .\provider-benchmark.json
```

The report includes strict-schema validity, p50/p95/p99 latency, safe error
classes, token usage, and estimated cost when both current token prices were
configured.
