import asyncio
import json

from agents.tool_context import ToolContext

from app.chat_service import (
    AgentContext,
    accept_verified_empty_result,
    execute_read_only_sql,
    resolve_supervisor,
)


def _tool_context(context, name, arguments):
    return ToolContext(
        context=context,
        tool_name=name,
        tool_call_id="test-call",
        tool_arguments=json.dumps(arguments),
    )


def test_empty_query_requires_explicit_verification(settings, monkeypatch):
    def fake_execute(_settings, validated):
        return {
            "columns": ["Value"],
            "rows": [],
            "row_count": 0,
            "execution_time": 0.01,
            "truncated": False,
            "sources": validated.sources,
        }

    monkeypatch.setattr("app.chat_service.execute_query", fake_execute)
    context = AgentContext(settings=settings)
    output = asyncio.run(
        execute_read_only_sql.on_invoke_tool(
            _tool_context(context, "execute_read_only_sql", {"sql": "SELECT Value FROM dbo.Test"}),
            json.dumps({"sql": "SELECT Value FROM dbo.Test"}),
        )
    )
    payload = json.loads(output)

    assert payload["status"] == "empty_unverified"
    assert context.last_result is None
    assert context.last_empty_result is not None

    verification = asyncio.run(
        accept_verified_empty_result.on_invoke_tool(
            _tool_context(
                context,
                "accept_verified_empty_result",
                {"verification_reason": "تاریخ، فیلتر و منبع جایگزین بررسی شد"},
            ),
            json.dumps({"verification_reason": "تاریخ، فیلتر و منبع جایگزین بررسی شد"}),
        )
    )
    assert json.loads(verification)["error"] == "authorized_catalog_search_required"
    context.authorized_catalog_sweeps = 1
    verification = asyncio.run(
        accept_verified_empty_result.on_invoke_tool(
            _tool_context(
                context,
                "accept_verified_empty_result",
                {"verification_reason": "تاریخ، فیلتر و کل کاتالوگ مجاز بررسی شد"},
            ),
            json.dumps({"verification_reason": "تاریخ، فیلتر و کل کاتالوگ مجاز بررسی شد"}),
        )
    )
    assert json.loads(verification)["status"] == "verified_empty"
    assert context.last_result["row_count"] == 0


def test_duplicate_sql_is_not_executed_twice(settings, monkeypatch):
    calls = []

    def fake_execute(_settings, validated):
        calls.append(validated.sql)
        raise RuntimeError("temporary SQL error")

    monkeypatch.setattr("app.chat_service.execute_query", fake_execute)
    context = AgentContext(settings=settings)
    arguments = {"sql": "SELECT Value FROM dbo.Test"}
    first = asyncio.run(
        execute_read_only_sql.on_invoke_tool(
            _tool_context(context, "execute_read_only_sql", arguments), json.dumps(arguments)
        )
    )
    second = asyncio.run(
        execute_read_only_sql.on_invoke_tool(
            _tool_context(context, "execute_read_only_sql", arguments), json.dumps(arguments)
        )
    )

    assert json.loads(first)["error_type"] == "sql_execution_error"
    assert json.loads(second)["error_type"] == "duplicate_attempt"
    assert len(calls) == 1


def test_resolve_supervisor_uses_live_sales_supervisor_directory(settings, monkeypatch):
    def fake_execute(_settings, validated):
        assert validated.sources == ["dbo.SalesReviewFast"]
        return {
            "columns": ["SupervisorId", "SupervisorName", "SalesEvidenceCount"],
            "rows": [[14, "نويد اسماعيل زاده", 89697]],
            "row_count": 1,
            "execution_time": 0.01,
            "truncated": False,
            "sources": validated.sources,
        }

    monkeypatch.setattr("app.chat_service.execute_query", fake_execute)
    context = AgentContext(settings=settings)
    arguments = {"name": "نوید اسماعیل زاده"}
    output = asyncio.run(
        resolve_supervisor.on_invoke_tool(
            _tool_context(context, "resolve_supervisor", arguments), json.dumps(arguments)
        )
    )
    payload = json.loads(output)

    assert payload["matches"][0]["supervisor_id"] == 14
    assert payload["matches"][0]["exact_normalized_match"] is True


def test_receipt_query_requires_payment_type_filter(settings, monkeypatch):
    calls = []

    def fake_execute(_settings, validated):
        calls.append(validated.sql)
        return {"columns": [], "rows": [], "row_count": 0, "sources": validated.sources}

    monkeypatch.setattr("app.chat_service.execute_query", fake_execute)
    context = AgentContext(settings=settings, prepared_context={"receipt_policy": True})
    arguments = {
        "sql": (
            "SELECT PayTypeName, SUM(PayAmount) AS TotalReceipt "
            "FROM Acc.vwRcvPaymentsReview "
            "WHERE PayDate >= N'1405/05/01' GROUP BY PayTypeName"
        )
    }
    output = asyncio.run(
        execute_read_only_sql.on_invoke_tool(
            _tool_context(context, "execute_read_only_sql", arguments), json.dumps(arguments)
        )
    )

    assert json.loads(output)["error_type"] == "receipt_type_filter_required"
    assert calls == []


def test_today_query_cannot_use_max_database_date(settings, monkeypatch):
    calls = []

    def fake_execute(_settings, validated):
        calls.append(validated.sql)
        return {
            "columns": ["BusinessDate", "NetSales"],
            "rows": [["1405/05/19", 2655153123]],
            "row_count": 1,
            "execution_time": 0.01,
            "truncated": False,
            "sources": validated.sources,
        }

    monkeypatch.setattr("app.chat_service.execute_query", fake_execute)
    context = AgentContext(
        settings=settings,
        prepared_context={
            "resolved_temporal_context": {
                "scope": "today",
                "current_business_date": "1405/05/18",
            }
        },
    )
    arguments = {
        "sql": (
            "WITH D AS (SELECT MAX(ReportDate) AS BusinessDate FROM dbo.SalesReviewFast) "
            "SELECT BusinessDate FROM D"
        )
    }
    output = asyncio.run(
        execute_read_only_sql.on_invoke_tool(
            _tool_context(context, "execute_read_only_sql", arguments), json.dumps(arguments)
        )
    )
    payload = json.loads(output)

    assert payload["error_type"] == "today_cannot_use_latest_database_date"
    assert payload["required_business_date"] == "1405/05/18"
    assert calls == []
    assert context.last_result is None


def test_today_query_rejects_a_result_for_tomorrow(settings, monkeypatch):
    def fake_execute(_settings, validated):
        return {
            "columns": ["BusinessDate", "NetSales"],
            "rows": [["1405/05/19", 2655153123]],
            "row_count": 1,
            "execution_time": 0.01,
            "truncated": False,
            "sources": validated.sources,
        }

    monkeypatch.setattr("app.chat_service.execute_query", fake_execute)
    context = AgentContext(
        settings=settings,
        prepared_context={
            "resolved_temporal_context": {
                "scope": "today",
                "current_business_date": "1405/05/18",
            }
        },
    )
    arguments = {
        "sql": (
            "SELECT N'1405/05/18' AS BusinessDate, SUM(NetSales) AS NetSales "
            "FROM dbo.SalesReviewFast WHERE ReportDate=N'1405/05/18'"
        )
    }
    output = asyncio.run(
        execute_read_only_sql.on_invoke_tool(
            _tool_context(context, "execute_read_only_sql", arguments), json.dumps(arguments)
        )
    )
    payload = json.loads(output)

    assert payload["error_type"] == "today_result_date_mismatch"
    assert payload["returned_dates"] == ["1405/05/19"]
    assert context.last_result is None
