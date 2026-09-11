import asyncio
import json

import pytest
from agents.tool_context import ToolContext

from app.access_control import (
    DataAccessDenied,
    authorize_catalogued_sql,
    policy_for_user,
)
from app.auth_service import provision_users
from app.chat_service import AgentContext, search_successful_report_memory
from app.database import sqlite_connection
from app.reasoning_context import find_successful_report_examples
from app.sql_guard import validate_read_only_sql


def _schema_object(settings, schema: str, name: str, columns=None) -> None:
    details = {
        "schema": schema,
        "name": name,
        "type": "VIEW",
        "columns": [{"name": value} for value in (columns or ["Value"])],
        "foreign_keys": [],
        "referenced_by": [],
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO schema_objects
               (schema_name, object_name, object_type, details_json, scanned_at)
               VALUES (?, ?, 'VIEW', ?, '2026-09-02T00:00:00')""",
            (schema, name, json.dumps(details)),
        )


def _save_report(
    settings,
    *,
    conversation_id: str,
    username: str,
    question: str,
    sql: str,
    sources: list[str],
    base_id: int,
) -> None:
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO chat_conversations
               (id, username, title, pinned, created_at, updated_at)
               VALUES (?, ?, 'report', 0, '2026-09-02T00:00:00', '2026-09-02T00:00:01')""",
            (conversation_id, username),
        )
        conn.execute(
            """INSERT INTO chat_messages
               (id, conversation_id, role, content, sources_json, created_at)
               VALUES (?, ?, 'user', ?, '[]', '2026-09-02T00:00:00')""",
            (base_id, conversation_id, question),
        )
        conn.execute(
            """INSERT INTO chat_messages
               (id, conversation_id, role, content, sql_text, sources_json, created_at)
               VALUES (?, ?, 'assistant', 'result', ?, ?, '2026-09-02T00:00:01')""",
            (base_id + 1, conversation_id, sql, json.dumps(sources)),
        )


def test_catalog_authorization_preserves_valid_reporting_queries(settings):
    _schema_object(settings, "dbo", "SalesReviewFast", ["SellNetAmount"])
    policy = policy_for_user(settings, "action-api-key")

    for sql in (
        "SELECT SellNetAmount FROM dbo.SalesReviewFast",
        "SELECT SellNetAmount FROM NeginPakhsh.dbo.SalesReviewFast",
        "SELECT SellNetAmount FROM SalesReviewFast",
        "WITH report AS (SELECT SellNetAmount FROM dbo.SalesReviewFast) SELECT * FROM report",
    ):
        authorized = authorize_catalogued_sql(
            settings, policy, validate_read_only_sql(sql)
        )
        assert authorized.sources == ["dbo.salesreviewfast"]
        assert "[dbo].[SalesReviewFast]" in authorized.sql


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM OtherDatabase.dbo.SalesReviewFast",
        "SELECT * FROM LinkedServer.NeginPakhsh.dbo.SalesReviewFast",
        "SELECT * FROM dbo.NotInCatalog",
        "SELECT * FROM OPENQUERY(remote_server, 'SELECT 1')",
        "SELECT * FROM dbo.ReportFunction(1)",
        "SELECT dbo.SecretFunction(1) FROM dbo.SalesReviewFast",
    ],
)
def test_catalog_authorization_rejects_cross_database_external_and_uncatalogued_sources(
    settings, sql
):
    _schema_object(settings, "dbo", "SalesReviewFast")

    with pytest.raises(DataAccessDenied):
        authorize_catalogued_sql(
            settings,
            policy_for_user(settings, "action-api-key"),
            validate_read_only_sql(sql),
        )


def test_raw_sql_route_authorizes_catalog_before_execution(client, auth, settings, monkeypatch):
    _schema_object(settings, "dbo", "SalesReviewFast", ["SellNetAmount"])
    executed = []

    def fake_execute(_settings, validated):
        executed.append(validated)
        return {
            "columns": ["SellNetAmount"],
            "rows": [[100]],
            "row_count": 1,
            "execution_time": 0.001,
            "truncated": False,
            "sources": validated.sources,
        }

    monkeypatch.setattr("app.routes.sql.execute_query", fake_execute)

    allowed = client.post(
        "/sql/query",
        json={"sql": "SELECT SellNetAmount FROM dbo.SalesReviewFast"},
        headers=auth,
    )
    denied = client.post(
        "/sql/query",
        json={"sql": "SELECT * FROM master.sys.databases"},
        headers=auth,
    )

    assert allowed.status_code == 200
    assert executed[0].sources == ["dbo.salesreviewfast"]
    assert denied.status_code == 403
    assert len(executed) == 1


def test_successful_report_memory_is_scoped_to_conversation_owner_even_for_admin(settings):
    for index, owner in enumerate(("alice", "bob", "admin"), 1):
        _save_report(
            settings,
            conversation_id=f"conversation-{owner}",
            username=owner,
            question="sales today",
            sql=f"SELECT '{owner}' AS OwnerName FROM dbo.SalesReviewFast",
            sources=["dbo.SalesReviewFast"],
            base_id=index * 10,
        )

    alice = find_successful_report_examples(
        settings, "sales today", principal="alice"
    )
    admin = find_successful_report_examples(
        settings, "sales today", principal="admin"
    )

    assert [item["sql_pattern"] for item in alice] == [
        "SELECT 'alice' AS OwnerName FROM dbo.SalesReviewFast"
    ]
    assert [item["sql_pattern"] for item in admin] == [
        "SELECT 'admin' AS OwnerName FROM dbo.SalesReviewFast"
    ]
    assert find_successful_report_examples(settings, "sales today") == []


def test_seller_report_memory_requires_every_source_to_match_seller_policy(settings):
    provision_users(
        settings,
        [
            {
                "username": "seller-one",
                "personnel_id": 22,
                "full_name": "Seller One",
                "role": "فروشنده",
                "branch": "دفتر فروش البرز",
                "sales_line": "لاین مارکت",
                "phone": "09120000000",
                "phone_status": "معتبر",
                "supervisor_personnel_id": 14,
            }
        ],
    )
    _schema_object(settings, "dbo", "SalesReviewFast", ["CustomerId", "SellNetAmount"])
    _schema_object(settings, "dbo", "vwBuyReview", ["CustId", "BuyAmount"])
    _save_report(
        settings,
        conversation_id="seller-safe",
        username="seller-one",
        question="sales report",
        sql="SELECT SellNetAmount FROM dbo.SalesReviewFast",
        sources=["dbo.SalesReviewFast"],
        base_id=100,
    )
    _save_report(
        settings,
        conversation_id="seller-mixed",
        username="seller-one",
        question="sales report",
        sql="SELECT SellNetAmount, BuyAmount FROM dbo.SalesReviewFast, dbo.vwBuyReview",
        sources=["dbo.SalesReviewFast", "dbo.vwBuyReview"],
        base_id=200,
    )
    context = AgentContext(
        settings=settings,
        username="seller-one",
        access_policy=policy_for_user(settings, "seller-one"),
    )
    arguments = {"query": "sales report", "limit": 8}
    tool_context = ToolContext(
        context=context,
        tool_name="search_successful_report_memory",
        tool_call_id="memory-test",
        tool_arguments=json.dumps(arguments),
    )

    output = asyncio.run(
        search_successful_report_memory.on_invoke_tool(
            tool_context, json.dumps(arguments)
        )
    )
    examples = json.loads(output)

    assert len(examples) == 1
    assert examples[0]["sources"] == ["dbo.SalesReviewFast"]
