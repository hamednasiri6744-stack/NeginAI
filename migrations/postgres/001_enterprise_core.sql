BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version text PRIMARY KEY,
    applied_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS neginai_users (
    username text PRIMARY KEY,
    password_hash text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    session_generation bigint NOT NULL DEFAULT 0 CHECK (session_generation >= 0),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS oauth_token_families (
    family_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    username text NOT NULL REFERENCES neginai_users(username) ON DELETE CASCADE,
    absolute_expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    revoke_reason text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CHECK (absolute_expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS oauth_token_families_active_user_idx
    ON oauth_token_families(username, absolute_expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS oauth_tokens (
    token_hash text PRIMARY KEY,
    family_id uuid NOT NULL REFERENCES oauth_token_families(family_id) ON DELETE CASCADE,
    username text NOT NULL REFERENCES neginai_users(username) ON DELETE CASCADE,
    token_type text NOT NULL CHECK (token_type IN ('access', 'refresh')),
    scope text NOT NULL,
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz,
    revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS oauth_tokens_active_user_idx
    ON oauth_tokens(username, token_type, expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS command_outbox (
    command_id uuid PRIMARY KEY,
    idempotency_key text NOT NULL UNIQUE,
    command_type text NOT NULL,
    subject text NOT NULL,
    payload jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'succeeded', 'retry', 'dead_letter')),
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    locked_by text,
    locked_until timestamptz,
    last_error_code text,
    last_error_message text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS command_outbox_claim_idx
    ON command_outbox(status, available_at, created_at)
    WHERE status IN ('pending', 'retry');

CREATE TABLE IF NOT EXISTS command_receipts (
    receipt_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    command_id uuid NOT NULL REFERENCES command_outbox(command_id),
    stage text NOT NULL,
    outcome text NOT NULL CHECK (outcome IN ('accepted', 'rejected', 'succeeded', 'failed', 'unknown')),
    external_system text,
    external_id text,
    payload_hash text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (command_id, stage, outcome, payload_hash)
);
CREATE INDEX IF NOT EXISTS command_receipts_external_idx
    ON command_receipts(external_system, external_id)
    WHERE external_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS agent_jobs (
    job_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    subject text NOT NULL,
    job_type text NOT NULL,
    input jsonb NOT NULL,
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    attempt_count integer NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    locked_by text,
    locked_until timestamptz,
    result jsonb,
    error_code text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX IF NOT EXISTS agent_jobs_claim_idx
    ON agent_jobs(status, available_at, created_at)
    WHERE status = 'queued';

CREATE TABLE IF NOT EXISTS audit_events (
    event_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    trace_id text NOT NULL,
    subject text NOT NULL,
    action text NOT NULL,
    resource_type text NOT NULL,
    resource_id text,
    decision text NOT NULL CHECK (decision IN ('allowed', 'denied', 'succeeded', 'failed')),
    policy_version text NOT NULL,
    details jsonb NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS audit_events_subject_time_idx
    ON audit_events(subject, occurred_at DESC);
CREATE INDEX IF NOT EXISTS audit_events_trace_idx
    ON audit_events(trace_id);

INSERT INTO schema_migrations(version)
VALUES ('001_enterprise_core')
ON CONFLICT (version) DO NOTHING;

COMMIT;
