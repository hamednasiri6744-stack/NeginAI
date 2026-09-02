import asyncio
import json

import pytest
from agents.tool_context import ToolContext

from app.access_control import (
    DataAccessDenied,
    enforce_sql_access,
    filter_schema_items,
    policy_for_user,
    restricted_request_message,
)
from app.auth_service import provision_users
from app.chat_service import AgentContext, execute_read_only_sql
from app.database import sqlite_connection
from app.sql_guard import validate_read_only_sql


BRANCH = "دفتر فروش البرز"
LINE = "لاین مارکت"


def _seller(settings) -> None:
    provision_users(
        settings,
        [
            {
                "username": "A.kamran",
                "personnel_id": 22,
                "full_name": "عارف کامران",
                "role": "فروشنده",
                "branch": BRANCH,
                "sales_line": LINE,
                "phone": "09120000000",
                "phone_status": "معتبر",
                "supervisor_personnel_id": 14,
            }
        ],
        temporary_password="1",
    )


def _schema_object(settings, schema: str, name: str, columns: list[str]) -> None:
    details = {
        "schema": schema,
        "name": name,
        "type": "VIEW",
        "columns": [
            {"ordinal": index, "name": column, "data_type": "int"}
            for index, column in enumerate(columns, 1)
        ],
        "foreign_keys": [],
        "referenced_by": [],
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO schema_objects
               (schema_name, object_name, object_type, details_json, scanned_at)
               VALUES (?, ?, 'VIEW', ?, '2026-08-10T00:00:00')""",
            (schema, name, json.dumps(details, ensure_ascii=False)),
        )


def _seed_customer_sources(settings) -> None:
    _schema_object(
        settings,
        "dbo",
        "SalesReviewFast",
        [
            "CustomerId",
            "CustomerLevelId",
            "CustomerLevelName",
            "CustomerCategoryId",
            "CustomerCategoryName",
            "SellNetAmount",
        ],
    )
    _schema_object(
        settings,
        "FRU",
        "NGT_TourCustomerModel",
        [
            "UniqueId",
            "BackOfficeId",
            "CustomerLevelId",
            "CustomerCategoryId",
            "CustomerLevelRef",
            "CustomerCategoryRef",
            "CustomerName",
        ],
    )
    _schema_object(
        settings,
        "GNR",
        "vwCust",
        ["ID", "CustGUID", "CustLevelName", "CustCtgrName"],
    )
    _schema_object(
        settings,
        "dbo",
        "CustomerCardex_Info",
        ["CustID", "VchDate", "BedAmount", "BesAmount", "BuyAmount"],
    )
    _schema_object(
        settings,
        "Acc",
        "vwRcvPaymentsReview",
        ["CustId", "ReportDate", "PayAmount"],
    )
    _schema_object(
        settings,
        "dbo",
        "vwReview_RcvAccountSale2",
        ["FilterID", "SaleNo", "RemainingAmount", "PaymentStatus"],
    )
    _schema_object(
        settings,
        "dbo",
        "vwReview_RcvAccountPayment2",
        ["FilterID", "PayNo", "PayAmount"],
    )
    _schema_object(
        settings,
        "dbo",
        "vwReview_RcvAccountSettlement2",
        ["FilterID", "SaleNo", "PayAmount"],
    )
    _schema_object(
        settings,
        "dbo",
        "vwReview_RcvAccountCardex2",
        ["FilterID", "VchNo", "BedAmount", "BesAmount", "Cardex"],
    )
    _schema_object(
        settings,
        "FRU",
        "CustomerCallPaymentsModel",
        ["CustId", "ReceiptNo", "Amount"],
    )
    _schema_object(
        settings,
        "dbo",
        "vwReview_StockAcc8028_Customer2",
        ["CustId", "SaleNetAmount", "IcaFinalAmount", "ProfitAmount"],
    )
    _schema_object(settings, "dbo", "vwBuyReview", ["CustId", "BuyAmount"])
    _schema_object(settings, "FRU", "NGT_TourModel", ["TourNo", "AgentId", "TotalOrderAmount"])


def test_seller_customer_reports_are_rewritten_to_branch_and_line_scope(settings):
    _seller(settings)
    _seed_customer_sources(settings)
    policy = policy_for_user(settings, "A.kamran")

    assert policy.is_restricted_seller is True
    assert policy.branch == BRANCH
    assert policy.sales_line == LINE

    for sql, source_alias in [
        ("SELECT SUM(BesAmount) FROM dbo.CustomerCardex_Info", "CustomerCardex_Info"),
        ("SELECT SUM(PayAmount) FROM Acc.vwRcvPaymentsReview", "vwRcvPaymentsReview"),
        ("SELECT SUM(Amount) FROM FRU.CustomerCallPaymentsModel", "CustomerCallPaymentsModel"),
        ("SELECT CustomerName FROM FRU.NGT_TourCustomerModel", "NGT_TourCustomerModel"),
    ]:
        secured = enforce_sql_access(settings, policy, validate_read_only_sql(sql))
        assert source_alias in secured.sql
        assert BRANCH in secured.sql
        assert LINE in secured.sql
        assert "vwCust" in secured.sql
        assert "CustLevelName" in secured.sql
        assert "CustCtgrName" in secured.sql
        assert BRANCH.encode("utf-8").decode("latin1") in secured.sql
        assert LINE.encode("utf-8").decode("latin1") in secured.sql
        assert LINE.replace("ی", "ي").encode("utf-8").decode("latin1") in secured.sql
        validate_read_only_sql(secured.sql)


def test_seller_sales_reports_cover_the_signed_in_sellers_branch_and_line(settings):
    _seller(settings)
    _seed_customer_sources(settings)
    policy = policy_for_user(settings, "A.kamran")

    secured = enforce_sql_access(
        settings, policy, validate_read_only_sql("SELECT SUM(SellNetAmount) FROM dbo.SalesReviewFast")
    )

    assert BRANCH in secured.sql
    assert LINE in secured.sql
    assert "SupervisorId] = 14" not in secured.sql
    assert "DealerId" in secured.sql
    assert "SupervisorId" in secured.sql
    assert secured.sql.count("IN (7, 137, 192, 510)") == 2


def test_seller_official_customer_financial_views_use_branch_and_line_scope(settings):
    _seller(settings)
    _seed_customer_sources(settings)
    policy = policy_for_user(settings, "A.kamran")

    for source, metric in (
        ("dbo.vwReview_RcvAccountSale2", "RemainingAmount"),
        ("dbo.vwReview_RcvAccountPayment2", "PayAmount"),
        ("dbo.vwReview_RcvAccountSettlement2", "PayAmount"),
        ("dbo.vwReview_RcvAccountCardex2", "Cardex"),
    ):
        secured = enforce_sql_access(
            settings,
            policy,
            validate_read_only_sql(f"SELECT SUM({metric}) FROM {source}"),
        )
        assert "FilterID" in secured.sql
        assert "vwCust" in secured.sql
        assert BRANCH in secured.sql
        assert LINE in secured.sql
        validate_read_only_sql(secured.sql)


def test_schema_keeps_customer_source_but_hides_forbidden_columns(settings):
    _seller(settings)
    _seed_customer_sources(settings)
    policy = policy_for_user(settings, "A.kamran")
    item = {
        "schema": "dbo",
        "name": "CustomerCardex_Info",
        "columns": [
            {"name": "CustID"},
            {"name": "BesAmount"},
            {"name": "BuyAmount"},
        ],
    }

    visible = filter_schema_items(policy, [item])

    assert len(visible) == 1
    assert [column["name"] for column in visible[0]["columns"]] == [
        "CustID",
        "BesAmount",
    ]
    assert policy.trusted_context()["preferred_sources"]["receipts"] == [
        "Acc.vwRcvPaymentsReview"
    ]
    assert policy.trusted_context()["preferred_sources"]["cardex"][0] == (
        "dbo.vwReview_RcvAccountCardex2"
    )


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT ProfitAmount FROM dbo.vwReview_StockAcc8028_Customer2",
        "SELECT IcaFinalAmount FROM dbo.vwReview_StockAcc8028_Customer2",
        "SELECT BuyAmount FROM dbo.vwBuyReview",
        "SELECT TourNo, TotalOrderAmount FROM FRU.NGT_TourModel",
    ],
)
def test_seller_cannot_query_cost_profit_or_unscoped_operational_data(settings, sql):
    _seller(settings)
    _seed_customer_sources(settings)

    with pytest.raises(DataAccessDenied):
        enforce_sql_access(
            settings,
            policy_for_user(settings, "A.kamran"),
            validate_read_only_sql(sql),
        )


def test_admin_sql_is_not_rewritten(settings):
    _seed_customer_sources(settings)
    policy = policy_for_user(settings, "Admin")
    validated = validate_read_only_sql("SELECT ProfitAmount FROM dbo.vwReview_StockAcc8028_Customer2")

    secured = enforce_sql_access(settings, policy, validated)

    assert secured == validated
    assert policy.is_admin is True
    assert policy.trusted_context()["mode"] == "admin_full_database_read"
    assert policy.trusted_context()["database_scope"] == "all_catalogued_tables_and_views"


def test_seller_gets_direct_denial_for_cost_but_not_customer_receipts(settings):
    _seller(settings)
    policy = policy_for_user(settings, "A.kamran")

    denied = restricted_request_message(policy, "قیمت خرید این کالا چقدر است؟")
    allowed = restricted_request_message(policy, "مجموع دریافتی مشتریان لاین من چقدر است؟")

    assert denied and "دسترسی ندارید" in denied
    assert BRANCH in denied and LINE in denied
    assert allowed is None


def test_agent_sql_tool_enforces_seller_scope_before_execution(settings, monkeypatch):
    _seller(settings)
    _seed_customer_sources(settings)
    executed = []

    def fake_execute(_settings, validated):
        executed.append(validated.sql)
        return {
            "columns": ["TotalReceived"],
            "rows": [[123]],
            "row_count": 1,
            "execution_time": 0.01,
            "truncated": False,
            "sources": validated.sources,
        }

    monkeypatch.setattr("app.chat_service.execute_query", fake_execute)
    context = AgentContext(
        settings=settings,
        username="A.kamran",
        access_policy=policy_for_user(settings, "A.kamran"),
    )
    tool_context = ToolContext(
        context=context,
        tool_name="execute_read_only_sql",
        tool_call_id="test-call",
        tool_arguments=json.dumps({"sql": "SELECT SUM(PayAmount) FROM Acc.vwRcvPaymentsReview"}),
    )

    output = asyncio.run(
        execute_read_only_sql.on_invoke_tool(
            tool_context,
            json.dumps({"sql": "SELECT SUM(PayAmount) FROM Acc.vwRcvPaymentsReview"}),
        )
    )

    assert json.loads(output)["row_count"] == 1
    assert BRANCH in executed[0]
    assert LINE in executed[0]


def test_agent_sql_tool_returns_safe_denial_for_purchase_cost(settings):
    _seller(settings)
    _seed_customer_sources(settings)
    context = AgentContext(
        settings=settings,
        username="A.kamran",
        access_policy=policy_for_user(settings, "A.kamran"),
    )
    arguments = {"sql": "SELECT BuyAmount FROM dbo.vwBuyReview"}
    tool_context = ToolContext(
        context=context,
        tool_name="execute_read_only_sql",
        tool_call_id="test-call",
        tool_arguments=json.dumps(arguments),
    )

    output = asyncio.run(
        execute_read_only_sql.on_invoke_tool(tool_context, json.dumps(arguments))
    )

    payload = json.loads(output)
    assert payload["error_type"] == "access_denied"
    assert "vwBuyReview" not in payload["message"]
    assert context.access_denied is True
