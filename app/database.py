from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID

import pyodbc
import pytds

from app.config import Settings
from app.sql_guard import ValidatedSql


def init_sqlite(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=30) as conn:
        conn.execute("PRAGMA busy_timeout=30000")
        current_journal_mode = str(conn.execute("PRAGMA journal_mode").fetchone()[0]).casefold()
        if current_journal_mode != "wal":
            conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_objects (
              id INTEGER PRIMARY KEY, schema_name TEXT NOT NULL, object_name TEXT NOT NULL,
              object_type TEXT NOT NULL, details_json TEXT NOT NULL, scanned_at TEXT NOT NULL,
              UNIQUE(schema_name, object_name)
            );
            CREATE TABLE IF NOT EXISTS schema_catalog (
              schema_name TEXT NOT NULL, object_name TEXT NOT NULL,
              persian_name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
              domain TEXT NOT NULL DEFAULT 'عملیاتی',
              data_classification TEXT NOT NULL DEFAULT 'needs_review',
              seller_access TEXT NOT NULL DEFAULT 'restricted'
                CHECK(seller_access IN ('restricted', 'customer_scope', 'reference')),
              aliases_json TEXT NOT NULL DEFAULT '[]', is_manual INTEGER NOT NULL DEFAULT 0,
              updated_at TEXT NOT NULL,
              PRIMARY KEY(schema_name, object_name)
            );
            CREATE TABLE IF NOT EXISTS definitions (
              id INTEGER PRIMARY KEY AUTOINCREMENT, term TEXT NOT NULL,
              definition TEXT NOT NULL, rules TEXT NOT NULL DEFAULT '',
              approved_sql TEXT, related_objects_json TEXT NOT NULL DEFAULT '[]',
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS query_audit (
              id INTEGER PRIMARY KEY AUTOINCREMENT, sql_text TEXT NOT NULL,
              succeeded INTEGER NOT NULL, row_count INTEGER, execution_time REAL,
              sources_json TEXT NOT NULL DEFAULT '[]', error_text TEXT,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS entity_catalog (
              entity_type TEXT NOT NULL CHECK(entity_type IN ('brand', 'manufacturer')),
              source_id INTEGER NOT NULL, display_name TEXT NOT NULL,
              normalized_name TEXT NOT NULL, source_object TEXT NOT NULL,
              synced_at TEXT NOT NULL,
              PRIMARY KEY(entity_type, source_id)
            );
            CREATE TABLE IF NOT EXISTS entity_sync_status (
              singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
              last_attempt TEXT, last_success TEXT, last_error TEXT
            );
            CREATE TABLE IF NOT EXISTS chat_messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              conversation_id TEXT NOT NULL, role TEXT NOT NULL,
              content TEXT NOT NULL, sql_text TEXT,
              sources_json TEXT NOT NULL DEFAULT '[]',
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_conversation
            ON chat_messages(conversation_id, id);
            CREATE TABLE IF NOT EXISTS chat_sessions (
              username TEXT PRIMARY KEY,
              conversation_id TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_conversations (
              id TEXT PRIMARY KEY,
              username TEXT NOT NULL,
              title TEXT NOT NULL,
              pinned INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_recent
              ON chat_conversations(username, pinned DESC, updated_at DESC);
            CREATE TABLE IF NOT EXISTS automations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL,
              title TEXT NOT NULL,
              query_text TEXT NOT NULL,
              condition_text TEXT,
              schedule_kind TEXT NOT NULL CHECK(schedule_kind IN ('interval', 'daily')),
              interval_minutes INTEGER,
              daily_time TEXT,
              timezone TEXT NOT NULL DEFAULT 'Asia/Tehran',
              active INTEGER NOT NULL DEFAULT 1,
              next_run_at TEXT NOT NULL,
              last_run_at TEXT,
              last_status TEXT,
              last_error TEXT,
              last_triggered INTEGER,
              locked_until TEXT,
              deleted_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_automations_due
              ON automations(active, next_run_at, locked_until);
            CREATE INDEX IF NOT EXISTS idx_automations_user
              ON automations(username, active, id);
            CREATE TABLE IF NOT EXISTS automation_runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              automation_id INTEGER NOT NULL,
              username TEXT NOT NULL,
              scheduled_for TEXT NOT NULL,
              started_at TEXT NOT NULL,
              finished_at TEXT,
              status TEXT NOT NULL,
              triggered INTEGER,
              answer TEXT,
              response_json TEXT,
              error_text TEXT,
              FOREIGN KEY(automation_id) REFERENCES automations(id)
            );
            CREATE INDEX IF NOT EXISTS idx_automation_runs_task
              ON automation_runs(automation_id, id DESC);
            CREATE TABLE IF NOT EXISTS notifications (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL,
              automation_id INTEGER,
              title TEXT NOT NULL,
              body TEXT NOT NULL,
              payload_json TEXT NOT NULL DEFAULT '{}',
              read_at TEXT,
              created_at TEXT NOT NULL,
              FOREIGN KEY(automation_id) REFERENCES automations(id)
            );
            CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
              ON notifications(username, read_at, id DESC);
            CREATE TABLE IF NOT EXISTS push_subscriptions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              username TEXT NOT NULL,
              endpoint TEXT NOT NULL UNIQUE,
              p256dh TEXT NOT NULL,
              auth TEXT NOT NULL,
              user_agent TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              last_success_at TEXT,
              last_error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user
              ON push_subscriptions(username, id);
            CREATE INDEX IF NOT EXISTS idx_schema_names
              ON schema_objects(schema_name, object_name);
            CREATE INDEX IF NOT EXISTS idx_schema_catalog_domain
              ON schema_catalog(domain, seller_access);
            -- Inverted index for schema discovery.  This keeps question-time
            -- retrieval bounded to matching objects instead of deserialising
            -- the entire schema cache on every request.
            CREATE TABLE IF NOT EXISTS schema_search_terms (
              term TEXT NOT NULL COLLATE NOCASE,
              schema_name TEXT NOT NULL,
              object_name TEXT NOT NULL,
              PRIMARY KEY(term, schema_name, object_name),
              FOREIGN KEY(schema_name, object_name)
                REFERENCES schema_objects(schema_name, object_name)
            );
            CREATE INDEX IF NOT EXISTS idx_schema_search_terms_lookup
              ON schema_search_terms(term, schema_name, object_name);
            CREATE TABLE IF NOT EXISTS schema_translation_review (
              column_name TEXT PRIMARY KEY COLLATE NOCASE,
              occurrence_count INTEGER NOT NULL,
              sample_sources_json TEXT NOT NULL,
              suggested_label TEXT NOT NULL,
              reason TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS varanegar_column_labels (
              resource_name TEXT NOT NULL,
              technical_name TEXT NOT NULL COLLATE NOCASE,
              persian_name TEXT NOT NULL,
              PRIMARY KEY(resource_name, technical_name)
            );
            CREATE INDEX IF NOT EXISTS idx_varanegar_column_labels_technical
              ON varanegar_column_labels(technical_name);
            CREATE INDEX IF NOT EXISTS idx_definitions_term ON definitions(term);
            CREATE INDEX IF NOT EXISTS idx_entity_name
              ON entity_catalog(entity_type, normalized_name);
            CREATE TABLE IF NOT EXISTS oauth_codes (
              code_hash TEXT PRIMARY KEY, username TEXT NOT NULL,
              client_id TEXT NOT NULL, redirect_uri TEXT NOT NULL,
              scope TEXT NOT NULL, code_challenge TEXT,
              code_challenge_method TEXT, expires_at INTEGER NOT NULL,
              used INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS oauth_tokens (
              token_hash TEXT PRIMARY KEY, username TEXT NOT NULL,
              token_type TEXT NOT NULL CHECK(token_type IN ('access', 'refresh')),
              scope TEXT NOT NULL, expires_at INTEGER NOT NULL,
              revoked INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user
              ON oauth_tokens(username, token_type, expires_at);
            CREATE TABLE IF NOT EXISTS users (
              username TEXT PRIMARY KEY COLLATE NOCASE,
              password_hash TEXT NOT NULL,
              active INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS oauth_client_diagnostics (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              auth_method TEXT NOT NULL,
              content_type TEXT NOT NULL,
              client_id_present INTEGER NOT NULL,
              client_id_match INTEGER NOT NULL,
              client_secret_present INTEGER NOT NULL,
              client_secret_length INTEGER NOT NULL,
              client_secret_match INTEGER NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS chat_failures (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              conversation_id TEXT,
              error_type TEXT NOT NULL,
              error_message TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS team_structure_rules (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              branch TEXT NOT NULL,
              sales_line TEXT NOT NULL,
              supervisor_id INTEGER,
              supervisor_name TEXT,
              team_split TEXT NOT NULL CHECK(team_split IN ('brand','region_or_customer','unspecified')),
              brand_portfolio_json TEXT NOT NULL DEFAULT '[]',
              status TEXT NOT NULL DEFAULT 'confirmed' CHECK(status IN ('confirmed','proposed','retired')),
              valid_from TEXT,
              valid_to TEXT,
              notes TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(branch, sales_line, supervisor_id, status)
            );
            CREATE TABLE IF NOT EXISTS team_change_proposals (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              proposal_type TEXT NOT NULL,
              branch TEXT NOT NULL,
              sales_line TEXT NOT NULL DEFAULT '',
              subject_type TEXT NOT NULL,
              subject_id INTEGER,
              current_value_json TEXT NOT NULL DEFAULT '{}',
              proposed_value_json TEXT NOT NULL DEFAULT '{}',
              evidence_json TEXT NOT NULL DEFAULT '{}',
              confidence REAL NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','dismissed')),
              created_by TEXT NOT NULL DEFAULT 'system',
              reviewed_by TEXT,
              reviewed_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_team_change_proposals_pending
            ON team_change_proposals(status, created_at DESC);
            -- Negin Planning is a write-back store for plans and forecasts.
            -- It is deliberately separate from the read-only NGT/Varanegar
            -- connection so planning activity can never mutate ERP actuals.
            CREATE TABLE IF NOT EXISTS planning_scenarios (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              code TEXT NOT NULL UNIQUE COLLATE NOCASE,
              name TEXT NOT NULL,
              scenario_type TEXT NOT NULL
                CHECK(scenario_type IN ('budget','forecast','plan')),
              fiscal_year INTEGER NOT NULL,
              start_period TEXT NOT NULL,
              end_period TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'draft'
                CHECK(status IN ('draft','submitted','approved','locked','archived')),
              base_scenario_id INTEGER,
              assumptions_json TEXT NOT NULL DEFAULT '{}',
              created_by TEXT NOT NULL,
              submitted_at TEXT,
              approved_by TEXT,
              approved_at TEXT,
              locked_at TEXT,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(base_scenario_id) REFERENCES planning_scenarios(id)
            );
            CREATE INDEX IF NOT EXISTS idx_planning_scenarios_year_status
              ON planning_scenarios(fiscal_year, status, id DESC);
            CREATE TABLE IF NOT EXISTS planning_values (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              scenario_id INTEGER NOT NULL,
              period TEXT NOT NULL,
              metric TEXT NOT NULL,
              branch TEXT NOT NULL DEFAULT '',
              sales_line TEXT NOT NULL DEFAULT '',
              supervisor_id TEXT NOT NULL DEFAULT '',
              seller_id TEXT NOT NULL DEFAULT '',
              customer_id TEXT NOT NULL DEFAULT '',
              brand TEXT NOT NULL DEFAULT '',
              product_id TEXT NOT NULL DEFAULT '',
              amount REAL NOT NULL,
              unit TEXT NOT NULL DEFAULT 'rial',
              note TEXT NOT NULL DEFAULT '',
              created_by TEXT NOT NULL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              FOREIGN KEY(scenario_id) REFERENCES planning_scenarios(id),
              UNIQUE(
                scenario_id, period, metric, branch, sales_line,
                supervisor_id, seller_id, customer_id, brand, product_id
              )
            );
            CREATE INDEX IF NOT EXISTS idx_planning_values_scenario_period
              ON planning_values(scenario_id, period, metric);
            CREATE TABLE IF NOT EXISTS planning_audit (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              scenario_id INTEGER NOT NULL,
              username TEXT NOT NULL,
              action TEXT NOT NULL,
              details_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              FOREIGN KEY(scenario_id) REFERENCES planning_scenarios(id)
            );
            CREATE INDEX IF NOT EXISTS idx_planning_audit_scenario
              ON planning_audit(scenario_id, id DESC);
            -- Local, offline-first pre-visit state.  These records are not
            -- Varanegar documents; only the NGT bridge may create one later.
            CREATE TABLE IF NOT EXISTS previsit_visits (
              id TEXT PRIMARY KEY,
              username TEXT NOT NULL,
              route_id TEXT NOT NULL,
              customer_id TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('active','completed','cancelled')),
              started_at TEXT NOT NULL,
              ended_at TEXT,
              start_latitude REAL,
              start_longitude REAL,
              end_latitude REAL,
              end_longitude REAL,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_previsit_visits_user_status
              ON previsit_visits(username, status, started_at DESC);
            CREATE TABLE IF NOT EXISTS previsit_drafts (
              id TEXT PRIMARY KEY,
              visit_id TEXT NOT NULL UNIQUE,
              username TEXT NOT NULL,
              idempotency_key TEXT NOT NULL UNIQUE,
              cart_json TEXT NOT NULL DEFAULT '[]',
              payment_type TEXT NOT NULL DEFAULT '',
              order_type TEXT NOT NULL DEFAULT '',
              warehouse_ref INTEGER,
              warehouse_name TEXT NOT NULL DEFAULT '',
              outcome TEXT NOT NULL DEFAULT 'draft'
                CHECK(outcome IN ('draft','order','no_order','skipped')),
              outcome_reason TEXT NOT NULL DEFAULT '',
              updated_at TEXT NOT NULL,
              FOREIGN KEY(visit_id) REFERENCES previsit_visits(id)
            );
            CREATE TABLE IF NOT EXISTS previsit_saved_requests (
              id TEXT PRIMARY KEY,
              visit_id TEXT NOT NULL,
              username TEXT NOT NULL,
              route_id TEXT NOT NULL,
              customer_id TEXT NOT NULL,
              request_number INTEGER NOT NULL CHECK(request_number > 0),
              cart_json TEXT NOT NULL DEFAULT '[]',
              payment_type TEXT NOT NULL DEFAULT '',
              order_type TEXT NOT NULL DEFAULT '',
              warehouse_ref INTEGER,
              warehouse_name TEXT NOT NULL DEFAULT '',
              preview_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(visit_id, username, request_number),
              FOREIGN KEY(visit_id) REFERENCES previsit_visits(id)
            );
            CREATE INDEX IF NOT EXISTS idx_previsit_saved_requests_customer
              ON previsit_saved_requests(username, customer_id, updated_at DESC);
            CREATE TABLE IF NOT EXISTS previsit_submissions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              draft_id TEXT NOT NULL,
              idempotency_key TEXT NOT NULL UNIQUE,
              payload_json TEXT NOT NULL,
              status TEXT NOT NULL CHECK(status IN ('prepared','sent','failed')),
              response_code INTEGER,
              response_json TEXT,
              created_at TEXT NOT NULL,
              sent_at TEXT,
              FOREIGN KEY(draft_id) REFERENCES previsit_drafts(id)
            );
            CREATE INDEX IF NOT EXISTS idx_previsit_submissions_draft
              ON previsit_submissions(draft_id, id DESC);
            CREATE TABLE IF NOT EXISTS customer_geo_locations (
              customer_id TEXT PRIMARY KEY,
              latitude REAL NOT NULL,
              longitude REAL NOT NULL,
              source TEXT NOT NULL CHECK(source IN ('erp', 'salesperson_pinned', 'geocoded')),
              updated_by TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            -- Customer edits are staged locally until the official NGT tour
            -- sync includes them.  This table is never an operational ERP write.
            CREATE TABLE IF NOT EXISTS previsit_customer_update_drafts (
              username TEXT NOT NULL,
              route_id TEXT NOT NULL,
              customer_id TEXT NOT NULL,
              update_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY(username, route_id, customer_id)
            );
            -- The management console writes only to this local NeginAI store.
            -- It never uses the read-only SQL Server/NGT connection below.
            CREATE TABLE IF NOT EXISTS control_positions (
              id TEXT PRIMARY KEY,
              code TEXT NOT NULL UNIQUE COLLATE NOCASE,
              title TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              active INTEGER NOT NULL DEFAULT 1,
              revision INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              deleted_at TEXT
            );
            CREATE TABLE IF NOT EXISTS control_permissions (
              key TEXT PRIMARY KEY COLLATE NOCASE,
              title TEXT NOT NULL,
              description TEXT NOT NULL DEFAULT '',
              category TEXT NOT NULL DEFAULT 'general',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS control_position_permissions (
              position_id TEXT NOT NULL,
              permission_key TEXT NOT NULL COLLATE NOCASE,
              created_at TEXT NOT NULL,
              PRIMARY KEY(position_id, permission_key),
              FOREIGN KEY(position_id) REFERENCES control_positions(id),
              FOREIGN KEY(permission_key) REFERENCES control_permissions(key)
            );
            CREATE TABLE IF NOT EXISTS control_personnel (
              id TEXT PRIMARY KEY,
              personnel_code TEXT NOT NULL UNIQUE COLLATE NOCASE,
              full_name TEXT NOT NULL,
              position_id TEXT NOT NULL,
              username TEXT UNIQUE COLLATE NOCASE,
              phone TEXT NOT NULL DEFAULT '',
              branch TEXT NOT NULL DEFAULT '',
              sales_line TEXT NOT NULL DEFAULT '',
              active INTEGER NOT NULL DEFAULT 1,
              source TEXT NOT NULL DEFAULT 'local',
              revision INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              deleted_at TEXT,
              FOREIGN KEY(position_id) REFERENCES control_positions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_control_personnel_position
              ON control_personnel(position_id, active, full_name);
            CREATE TABLE IF NOT EXISTS control_personnel_views (
              id TEXT PRIMARY KEY,
              username TEXT NOT NULL COLLATE NOCASE,
              name TEXT NOT NULL COLLATE NOCASE,
              is_default INTEGER NOT NULL DEFAULT 0,
              page_size INTEGER NOT NULL DEFAULT 50
                CHECK(page_size IN (50, 100, 500, 1000)),
              status_filter TEXT NOT NULL DEFAULT 'all'
                CHECK(status_filter IN ('all', 'active', 'inactive')),
              visible_columns_json TEXT NOT NULL,
              filters_json TEXT NOT NULL DEFAULT '{}',
              revision INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              deleted_at TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_control_personnel_views_name
              ON control_personnel_views(username, name) WHERE deleted_at IS NULL;
            CREATE INDEX IF NOT EXISTS idx_control_personnel_views_user
              ON control_personnel_views(username, is_default DESC, name);
            CREATE TABLE IF NOT EXISTS control_branch_assignment_state (
              id INTEGER PRIMARY KEY CHECK(id=1),
              revision INTEGER NOT NULL DEFAULT 0,
              updated_by TEXT,
              updated_at TEXT
            );
            INSERT OR IGNORE INTO control_branch_assignment_state (id, revision)
              VALUES (1, 0);
            CREATE TABLE IF NOT EXISTS control_branch_assignments (
              personnel_id INTEGER PRIMARY KEY,
              branch_code TEXT NOT NULL
                CHECK(branch_code IN ('alborz','tehran','qazvin','rasht','headquarters')),
              assigned_by TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_control_branch_assignments_branch
              ON control_branch_assignments(branch_code, personnel_id);
            CREATE TABLE IF NOT EXISTS control_operation_receipts (
              operation_id TEXT PRIMARY KEY,
              username TEXT NOT NULL,
              entity TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              response_json TEXT NOT NULL,
              applied_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS control_audit (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              operation_id TEXT NOT NULL UNIQUE,
              username TEXT NOT NULL,
              entity TEXT NOT NULL,
              entity_id TEXT NOT NULL,
              action TEXT NOT NULL,
              payload_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_control_audit_recent
              ON control_audit(id DESC);
            """
        )
        # Serialise the read-then-ALTER migrations below. Multiple app workers
        # can start together; without an immediate write lock they can both
        # observe a missing column and race to add it.
        conn.execute("BEGIN IMMEDIATE")
        chat_columns = {row[1] for row in conn.execute("PRAGMA table_info(chat_messages)")}
        if "response_json" not in chat_columns:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN response_json TEXT")
        user_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
        team_rule_columns = {row[1] for row in conn.execute("PRAGMA table_info(team_structure_rules)")}
        if "brand_portfolio_json" not in team_rule_columns:
            conn.execute("ALTER TABLE team_structure_rules ADD COLUMN brand_portfolio_json TEXT NOT NULL DEFAULT '[]'")
        catalog_columns = {row[1] for row in conn.execute("PRAGMA table_info(schema_catalog)")}
        if "data_classification" not in catalog_columns:
            conn.execute(
                "ALTER TABLE schema_catalog ADD COLUMN data_classification TEXT NOT NULL DEFAULT 'needs_review'"
            )
        visit_columns = {row[1] for row in conn.execute("PRAGMA table_info(previsit_visits)")}
        visit_migrations = {
            "start_accuracy": "start_accuracy REAL",
            "end_accuracy": "end_accuracy REAL",
            "start_distance_meters": "start_distance_meters REAL",
        }
        for column_name, definition in visit_migrations.items():
            if column_name not in visit_columns:
                conn.execute(f"ALTER TABLE previsit_visits ADD COLUMN {definition}")
        draft_columns = {row[1] for row in conn.execute("PRAGMA table_info(previsit_drafts)")}
        draft_migrations = {
            "outcome_reason_id": "outcome_reason_id TEXT",
            "visit_status_id": "visit_status_id TEXT",
            "warehouse_ref": "warehouse_ref INTEGER",
            "warehouse_name": "warehouse_name TEXT NOT NULL DEFAULT ''",
        }
        for column_name, definition in draft_migrations.items():
            if column_name not in draft_columns:
                conn.execute(f"ALTER TABLE previsit_drafts ADD COLUMN {definition}")
        user_profile_columns = {
            "personnel_id": "personnel_id INTEGER",
            "full_name": "full_name TEXT",
            "role": "role TEXT",
            "branch": "branch TEXT",
            "sales_line": "sales_line TEXT",
            "phone": "phone TEXT",
            "phone_status": "phone_status TEXT",
            "supervisor_personnel_id": "supervisor_personnel_id INTEGER",
            "must_change_password": "must_change_password INTEGER NOT NULL DEFAULT 0",
        }
        for column_name, definition in user_profile_columns.items():
            if column_name not in user_columns:
                conn.execute(f"ALTER TABLE users ADD COLUMN {definition}")
        conn.execute(
            """CREATE UNIQUE INDEX IF NOT EXISTS idx_users_personnel_id
               ON users(personnel_id) WHERE personnel_id IS NOT NULL"""
        )
        conn.execute(
            """UPDATE definitions
               SET definition = ?, rules = ?, updated_at = ?
               WHERE term LIKE ? AND rules LIKE ?""",
            (
                "وقتی کاربر فروش را بدون تعیین مبنا می‌خواهد، گزارش پیش‌فرض مجموع حواله و فاکتور است. اگر مبنا را صریحاً مشخص کرد، همان مبنا اجرا می‌شود.",
                "برای سؤال‌های معمول درباره نوع سند سؤال شفاف‌ساز نپرس. فروش خالص از فروش مبنای انتخاب‌شده پس از کسر برگشتی همان بازه محاسبه می‌شود. پیش‌فرض‌ها و تاریخ مبنا را کوتاه در پاسخ اعلام کن.",
                datetime.utcnow().isoformat(),
                "%حواله%فاکتور%",
                "%شفاف‌ساز اجباری%",
            ),
        )


@contextmanager
def sqlite_connection(path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _connection_string(settings: Settings) -> str:
    trust = "yes" if settings.sql_trust_certificate else "no"
    return (
        f"DRIVER={{{settings.sql_driver}}};SERVER={settings.sql_server};"
        f"DATABASE={settings.sql_database};UID={settings.sql_username};"
        f"PWD={settings.sql_password};TrustServerCertificate={trust};"
        "ApplicationIntent=ReadOnly;"
    )


def _pytds_connection(settings: Settings) -> Any:
    server, separator, port_value = settings.sql_server.partition(",")
    return pytds.connect(
        dsn=server.strip(),
        port=int(port_value) if separator and port_value.isdigit() else None,
        database=settings.sql_database,
        user=settings.sql_username,
        password=settings.sql_password,
        timeout=settings.sql_query_timeout,
        login_timeout=settings.sql_query_timeout,
        readonly=True,
        validate_host=True,
    )


@contextmanager
def sql_connection(settings: Settings) -> Iterator[Any]:
    if not settings.sql_configured:
        raise RuntimeError("SQL Server connection is not configured")
    client = settings.sql_client
    if client not in {"odbc", "pytds", "auto"}:
        raise RuntimeError("SQL_CLIENT must be odbc, pytds, or auto")
    if client == "pytds":
        conn = _pytds_connection(settings)
    else:
        try:
            conn = pyodbc.connect(_connection_string(settings), timeout=settings.sql_query_timeout)
        except pyodbc.Error:
            if client != "auto":
                raise
            conn = _pytds_connection(settings)
    try:
        if hasattr(conn, "autocommit"):
            conn.autocommit = False
        if hasattr(conn, "timeout"):
            conn.timeout = settings.sql_query_timeout
        yield conn
    finally:
        try:
            conn.rollback()
        finally:
            conn.close()


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date, dt_time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def record_audit(
    settings: Settings,
    sql: str,
    succeeded: bool,
    sources: list[str],
    row_count: int | None = None,
    execution_time: float | None = None,
    error: str | None = None,
) -> None:
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO query_audit
               (sql_text, succeeded, row_count, execution_time, sources_json, error_text, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sql, int(succeeded), row_count, execution_time, json.dumps(sources), error, datetime.utcnow().isoformat()),
        )


def record_oauth_client_diagnostic(
    settings: Settings,
    *,
    auth_method: str,
    content_type: str,
    client_id_present: bool,
    client_id_match: bool,
    client_secret_present: bool,
    client_secret_length: int,
    client_secret_match: bool,
) -> None:
    """Persist only non-secret OAuth client-auth metadata for troubleshooting."""
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO oauth_client_diagnostics
               (auth_method, content_type, client_id_present, client_id_match,
                client_secret_present, client_secret_length, client_secret_match, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                auth_method[:32],
                content_type[:32],
                int(client_id_present),
                int(client_id_match),
                int(client_secret_present),
                max(0, client_secret_length),
                int(client_secret_match),
                datetime.utcnow().isoformat(),
            ),
        )
        conn.execute(
            """DELETE FROM oauth_client_diagnostics
               WHERE id NOT IN (
                 SELECT id FROM oauth_client_diagnostics ORDER BY id DESC LIMIT 100
               )"""
        )


def record_chat_failure(
    settings: Settings,
    conversation_id: str | None,
    error_type: str,
    error_message: str,
) -> None:
    """Record bounded technical diagnostics without credentials or request content."""
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO chat_failures
               (conversation_id, error_type, error_message, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                (conversation_id or "")[:100] or None,
                error_type[:200],
                error_message[:2000],
                datetime.utcnow().isoformat(),
            ),
        )
        conn.execute(
            """DELETE FROM chat_failures
               WHERE id NOT IN (
                 SELECT id FROM chat_failures ORDER BY id DESC LIMIT 200
               )"""
        )


def execute_query(settings: Settings, validated: ValidatedSql) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with sql_connection(settings) as conn:
            cursor = conn.cursor()
            cursor.execute(validated.sql)
            if cursor.description is None:
                raise RuntimeError("The statement did not return a result set")
            columns = [str(column[0]) for column in cursor.description]
            fetched = cursor.fetchmany(settings.sql_max_rows + 1)
            truncated = len(fetched) > settings.sql_max_rows
            rows = [[_json_value(value) for value in row] for row in fetched[: settings.sql_max_rows]]
        elapsed = round(time.perf_counter() - started, 6)
        record_audit(settings, validated.sql, True, validated.sources, len(rows), elapsed)
        return {"columns": columns, "rows": rows, "row_count": len(rows), "execution_time": elapsed,
                "truncated": truncated, "sources": validated.sources}
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 6)
        record_audit(settings, validated.sql, False, validated.sources, execution_time=elapsed, error=str(exc)[:4000])
        raise
