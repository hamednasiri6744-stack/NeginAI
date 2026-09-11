"""PostgreSQL-backed durable command and agent-job coordination.

The application remains able to run its current single-node SQLite mode.  This
module is the explicit enterprise boundary used when PostgreSQL is configured;
it never falls back to SQLite after an enterprise operation has begun.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class EnterpriseStoreError(RuntimeError):
    """A fail-closed enterprise persistence error."""


class IdempotencyConflict(EnterpriseStoreError):
    """An idempotency key was reused with different immutable input."""


@dataclass(frozen=True)
class ClaimedCommand:
    command_id: str
    idempotency_key: str
    command_type: str
    subject: str
    payload: dict[str, Any]
    attempt_count: int
    worker_id: str = ""


def canonical_payload(payload: dict[str, Any]) -> tuple[str, str]:
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return encoded, hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class EnterpriseStore:
    """Small transactional store with lease-based, skip-locked command claims."""

    def __init__(
        self,
        database_url: str,
        *,
        pool_factory: Callable[..., Any] = ConnectionPool,
        min_size: int = 1,
        max_size: int = 20,
    ) -> None:
        if not database_url.strip():
            raise EnterpriseStoreError("enterprise database URL is required")
        if min_size < 1 or max_size < min_size:
            raise EnterpriseStoreError("invalid PostgreSQL pool size")
        self._pool = pool_factory(
            conninfo=database_url,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row, "autocommit": False},
            open=False,
        )

    def open(self) -> None:
        self._pool.open(wait=True)

    def close(self) -> None:
        self._pool.close()

    def check(self) -> None:
        self._pool.check()
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 AS ready")
                row = cursor.fetchone()
                if not row or int(row["ready"]) != 1:
                    raise EnterpriseStoreError("PostgreSQL readiness check failed")
                cursor.execute("SELECT 1 FROM schema_migrations WHERE version=%s", ("001_enterprise_core",))
                if cursor.fetchone() is None:
                    raise EnterpriseStoreError("required PostgreSQL enterprise migration is not applied")

    def apply_migration(self, migration_path: Path) -> None:
        sql = migration_path.read_text(encoding="utf-8")
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(sql)

    def enqueue_command(
        self,
        *,
        idempotency_key: str,
        command_type: str,
        subject: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        if not idempotency_key.strip() or not command_type.strip() or not subject.strip():
            raise EnterpriseStoreError("command identity fields are required")
        encoded, payload_hash = canonical_payload(payload)
        command_id = str(uuid.uuid4())
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO command_outbox
                        (command_id, idempotency_key, command_type, subject, payload)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (idempotency_key) DO NOTHING
                    RETURNING command_id::text, status, command_type, subject,
                              encode(digest(payload::text, 'sha256'), 'hex') AS payload_hash
                    """,
                    (command_id, idempotency_key, command_type, subject, encoded),
                )
                row = cursor.fetchone()
                created = row is not None
                if row is None:
                    cursor.execute(
                        """SELECT command_id::text, status, command_type, subject,
                                  encode(digest(payload::text, 'sha256'), 'hex') AS payload_hash
                           FROM command_outbox WHERE idempotency_key=%s FOR UPDATE""",
                        (idempotency_key,),
                    )
                    row = cursor.fetchone()
                if not row:
                    raise EnterpriseStoreError("command enqueue did not produce a durable row")
                # PostgreSQL jsonb normalizes formatting. Compare semantic input as
                # well as the immutable routing fields to reject key collisions.
                cursor.execute(
                    "SELECT payload FROM command_outbox WHERE command_id=%s",
                    (row["command_id"],),
                )
                stored = cursor.fetchone()
                stored_payload = stored["payload"] if stored else None
                if (
                    row["command_type"] != command_type
                    or row["subject"] != subject
                    or stored_payload != payload
                ):
                    raise IdempotencyConflict("idempotency key belongs to another command")
                return {
                    "command_id": row["command_id"],
                    "status": row["status"],
                    "created": created,
                    "payload_hash": payload_hash,
                }

    def claim_command(
        self, *, worker_id: str, lease_seconds: int = 60
    ) -> ClaimedCommand | None:
        if not worker_id.strip() or not 10 <= lease_seconds <= 3600:
            raise EnterpriseStoreError("invalid command lease")
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    WITH candidate AS (
                        SELECT command_id FROM command_outbox
                        WHERE status IN ('pending', 'retry')
                          AND available_at <= clock_timestamp()
                          AND (locked_until IS NULL OR locked_until < clock_timestamp())
                        ORDER BY created_at
                        FOR UPDATE SKIP LOCKED
                        LIMIT 1
                    )
                    UPDATE command_outbox AS command
                    SET status='processing', attempt_count=attempt_count+1,
                        locked_by=%s,
                        locked_until=clock_timestamp() + (%s * interval '1 second'),
                        updated_at=clock_timestamp()
                    FROM candidate
                    WHERE command.command_id=candidate.command_id
                    RETURNING command.command_id::text, command.idempotency_key,
                              command.command_type, command.subject, command.payload,
                              command.attempt_count
                    """,
                    (worker_id, lease_seconds),
                )
                row = cursor.fetchone()
                if not row:
                    return None
                return ClaimedCommand(**dict(row), worker_id=worker_id)

    def renew_command_lease(
        self, command: ClaimedCommand, *, lease_seconds: int = 60
    ) -> None:
        if not command.worker_id.strip() or not 10 <= lease_seconds <= 3600:
            raise EnterpriseStoreError("invalid command lease renewal")
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE command_outbox
                       SET locked_until=clock_timestamp() + (%s * interval '1 second'),
                           updated_at=clock_timestamp()
                       WHERE command_id=%s AND status='processing'
                         AND locked_by=%s AND attempt_count=%s
                         AND locked_until >= clock_timestamp()""",
                    (lease_seconds, command.command_id, command.worker_id, command.attempt_count),
                )
                if cursor.rowcount != 1:
                    raise EnterpriseStoreError("command lease was lost before renewal")
    def mark_succeeded(
        self,
        command: ClaimedCommand,
        *,
        external_system: str,
        external_id: str,
        details: dict[str, Any],
    ) -> None:
        _, payload_hash = canonical_payload(command.payload)
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE command_outbox SET status='succeeded', locked_by=NULL,
                              locked_until=NULL, updated_at=clock_timestamp()
                       WHERE command_id=%s AND status='processing'
                         AND locked_by=%s AND attempt_count=%s
                         AND locked_until >= clock_timestamp()""",
                    (command.command_id, command.worker_id, command.attempt_count),
                )
                if cursor.rowcount != 1:
                    raise EnterpriseStoreError("command lease was lost before success")
                cursor.execute(
                    """INSERT INTO command_receipts
                           (command_id, stage, outcome, external_system, external_id,
                            payload_hash, details)
                       VALUES (%s, 'commit', 'succeeded', %s, %s, %s, %s::jsonb)
                       ON CONFLICT DO NOTHING""",
                    (
                        command.command_id,
                        external_system,
                        external_id,
                        payload_hash,
                        json.dumps(details, ensure_ascii=False, separators=(",", ":")),
                    ),
                )

    def mark_failed(
        self,
        command: ClaimedCommand,
        *,
        error_code: str,
        safe_message: str,
        outcome_unknown: bool,
        max_attempts: int = 8,
    ) -> str:
        if max_attempts < 1:
            raise EnterpriseStoreError("max attempts must be positive")
        final = command.attempt_count >= max_attempts
        status = "dead_letter" if final else "retry"
        delay = min(3600, 2 ** min(command.attempt_count, 11))
        _, payload_hash = canonical_payload(command.payload)
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """UPDATE command_outbox
                       SET status=%s, available_at=clock_timestamp() + (%s * interval '1 second'),
                           locked_by=NULL, locked_until=NULL, last_error_code=%s,
                           last_error_message=%s, updated_at=clock_timestamp()
                       WHERE command_id=%s AND status='processing'
                         AND locked_by=%s AND attempt_count=%s
                         AND locked_until >= clock_timestamp()""",
                    (status, delay, error_code[:100], safe_message[:600], command.command_id, command.worker_id, command.attempt_count),
                )
                if cursor.rowcount != 1:
                    raise EnterpriseStoreError("command lease was lost before failure receipt")
                cursor.execute(
                    """INSERT INTO command_receipts
                           (command_id, stage, outcome, payload_hash, details)
                       VALUES (%s, 'dispatch', %s, %s, %s::jsonb)
                       ON CONFLICT DO NOTHING""",
                    (
                        command.command_id,
                        "unknown" if outcome_unknown else "failed",
                        payload_hash,
                        json.dumps(
                            {"error_code": error_code[:100], "attempt": command.attempt_count},
                            separators=(",", ":"),
                        ),
                    ),
                )
        return status

    def recover_expired_leases(self) -> int:
        """Move abandoned work to retry while preserving an unknown-outcome receipt."""
        with self._pool.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    WITH expired AS (
                        UPDATE command_outbox
                        SET status='retry', available_at=clock_timestamp(), locked_by=NULL,
                            locked_until=NULL, last_error_code='LEASE_EXPIRED',
                            last_error_message='worker lease expired; reconcile before retry',
                            updated_at=clock_timestamp()
                        WHERE status='processing' AND locked_until < clock_timestamp()
                        RETURNING command_id, payload
                    )
                    INSERT INTO command_receipts
                        (command_id, stage, outcome, payload_hash, details)
                    SELECT command_id, 'lease', 'unknown',
                           encode(digest(payload::text, 'sha256'), 'hex'),
                           '{"error_code":"LEASE_EXPIRED"}'::jsonb
                    FROM expired
                    ON CONFLICT DO NOTHING
                    RETURNING receipt_id
                    """
                )
                return len(cursor.fetchall())
