from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "deploy" / "enterprise" / "compose.yml"
MIGRATION = ROOT / "migrations" / "postgres" / "001_enterprise_core.sql"


def test_enterprise_services_are_loopback_only_and_secrets_are_required():
    document = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    services = document["services"]

    assert set(services) == {"postgres", "redis", "otel-collector"}
    assert services["postgres"]["image"] == "postgres:18.6-alpine"
    assert services["redis"]["image"] == "redis:8.10.1-alpine"
    assert services["otel-collector"]["image"] == "otel/opentelemetry-collector-contrib:0.153.0"
    for service in services.values():
        for published in service.get("ports", []):
            assert published.startswith("127.0.0.1:")
    assert "set NEGINAI_POSTGRES_PASSWORD" in services["postgres"]["environment"]["POSTGRES_PASSWORD"]
    assert "set NEGINAI_REDIS_PASSWORD" in services["redis"]["environment"]["REDIS_PASSWORD"]


def test_enterprise_core_migration_has_idempotency_claim_and_audit_invariants():
    source = MIGRATION.read_text(encoding="utf-8")

    required_fragments = {
        "idempotency_key text NOT NULL UNIQUE",
        "attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0)",
        "locked_until timestamptz",
        "payload_hash text NOT NULL",
        "session_generation bigint NOT NULL DEFAULT 0",
        "absolute_expires_at timestamptz NOT NULL",
        "policy_version text NOT NULL",
        "ON CONFLICT (version) DO NOTHING",
    }
    assert all(fragment in source for fragment in required_fragments)
