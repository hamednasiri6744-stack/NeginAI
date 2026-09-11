# NeginAI enterprise substrate

This compose project provides only the local/staging state and observability
substrate. It does not publish NeginAI or enable any Varanegar write path.

Required secrets are supplied through environment variables or an untracked
environment file. Never reuse SQL Server, action API, OAuth or model-provider
credentials here.

Services are bound to loopback and share an internal container network:

- PostgreSQL 18 for authoritative NeginAI transactional state;
- Redis 8 for distributed rate limits, leases, cache and bounded coordination;
- OpenTelemetry Collector for OTLP ingest. The checked-in exporter is `debug`
  until an explicitly approved telemetry backend and retention policy exist.

The first PostgreSQL initialization applies files from
`migrations/postgres/`. Production deployments must use a non-superuser
application role, encrypted storage, managed backups and TLS; the local
compose file is not by itself a production deployment.
