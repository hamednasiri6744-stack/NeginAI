from dataclasses import replace

import pytest


@pytest.mark.parametrize(
    "question",
    [
        "آخرین حواله مربوط به چه ساعتی است و ثبت‌کننده آن چه کسی است؟",
        "بیشترین فروش را چه بازاریاب‌هایی داشتند؟",
        "کدام مشتریان این ماه بیشترین برگشتی را داشته‌اند؟",
    ],
)
def test_all_business_questions_use_the_general_agent_path(
    settings, monkeypatch, question
):
    from app.chat_service import AgentReply, chat

    calls = []

    class FakeResult:
        final_output = AgentReply(answer="پاسخ مبتنی بر داده", evidence_status="database_result")

    def fake_run_sync(agent, *args, **kwargs):
        calls.append({"agent": agent, **kwargs})
        kwargs["context"].last_result = {
            "columns": ["Value"],
            "rows": [[1]],
            "row_count": 1,
            "execution_time": 0.01,
            "truncated": False,
            "sources": ["dbo.VerifiedSource"],
            "sql": "SELECT 1 AS Value",
        }
        return FakeResult()

    def direct_query_must_not_run(*_args, **_kwargs):
        raise AssertionError("Question-specific code bypassed the general agent")

    monkeypatch.setattr("app.chat_service.Runner.run_sync", fake_run_sync)
    monkeypatch.setattr("app.chat_service.execute_query", direct_query_must_not_run)
    monkeypatch.setattr(
        "app.chat_service.prepare_analysis_context",
        lambda *_args: {
            "business_definitions": [{"term": "نمونه"}],
            "successful_report_examples": [],
            "schema_candidates": [],
            "known_source_failures": [],
        },
    )
    tuned = replace(settings, openai_api_key="test-key")

    response = chat(tuned, question, "general-agent")

    assert response["answer"] == "پاسخ مبتنی بر داده"
    assert len(calls) == 1
    tool_names = {tool.name for tool in calls[0]["agent"].tools}
    assert {
        "search_successful_report_memory",
        "search_database_schema",
        "execute_read_only_sql",
        "accept_verified_empty_result",
    } <= tool_names


def test_follow_up_history_is_sent_to_the_general_agent(settings, monkeypatch):
    from app.chat_service import AgentReply, chat
    from app.database import sqlite_connection

    with sqlite_connection(settings.sqlite_path) as conn:
        conn.executemany(
            """INSERT INTO chat_messages
               (conversation_id, role, content, sources_json, created_at)
               VALUES ('follow-up', ?, ?, '[]', ?)""",
            [
                ("user", "فروش امروز تهران را بگو", "2026-08-08T00:00:00"),
                ("assistant", "گزارش تهران", "2026-08-08T00:00:01"),
            ],
        )

    captured = {}

    class FakeResult:
        final_output = AgentReply(answer="رتبه‌بندی", evidence_status="database_result")

    def fake_run_sync(_agent, *args, **kwargs):
        captured["input"] = kwargs["input"]
        kwargs["context"].last_result = {
            "columns": ["Name"], "rows": [["الف"]], "row_count": 1,
            "execution_time": 0.01, "truncated": False,
            "sources": ["dbo.SalesReviewFast"], "sql": "SELECT N'الف' AS Name",
        }
        return FakeResult()

    monkeypatch.setattr("app.chat_service.Runner.run_sync", fake_run_sync)
    monkeypatch.setattr("app.chat_service.prepare_analysis_context", lambda *_args: {})
    tuned = replace(settings, openai_api_key="test-key")

    chat(tuned, "به تفکیک بازاریاب بده", "follow-up")

    assert [item["content"] for item in captured["input"]] == [
        "فروش امروز تهران را بگو",
        "گزارش تهران",
        "به تفکیک بازاریاب بده",
    ]


def test_oauth_follow_up_reuses_active_session_when_action_omits_id(settings):
    from datetime import datetime

    from app.chat_service import _resolve_conversation_id

    now = datetime(2026, 8, 8, 19, 30, 0)
    first_id = _resolve_conversation_id(
        settings,
        None,
        "Admin",
        "فروش دو روز پیش را بگو",
        now,
    )
    follow_up_id = _resolve_conversation_id(
        settings,
        None,
        "Admin",
        "کل دریافت چقدر بوده؟",
        now,
    )

    assert follow_up_id == first_id


def test_standalone_request_without_action_id_starts_a_new_user_session(settings):
    from datetime import datetime, timedelta

    from app.chat_service import _resolve_conversation_id

    now = datetime(2026, 8, 8, 19, 30, 0)
    first_id = _resolve_conversation_id(
        settings, None, "Admin", "فروش امروز را بگو", now
    )
    next_id = _resolve_conversation_id(
        settings,
        None,
        "Admin",
        "فروش دو روز پیش را بگو",
        now + timedelta(minutes=1),
    )

    assert next_id != first_id


def test_profit_result_contract_rejects_diagnostic_only_evidence(settings):
    from app.chat_service import AgentContext, AgentReply, _reply_needs_recovery

    context = AgentContext(
        settings=settings,
        prepared_context={
            "required_result_columns": {
                "groups": [
                    ["BrandName"],
                    ["ProfitAtLastPurchasePrice", "GrossProfitAtLastPurchasePrice"],
                    ["SettlementDiscountAmount", "AllocatedSettlementDiscount"],
                ]
            }
        },
        last_result={
            "columns": ["SoldGoodsCount", "GoodsWithPrice", "GoodsWithoutPrice"],
            "rows": [[1620, 1620, 0]],
            "row_count": 1,
        },
    )
    reply = AgentReply(answer="قیمت‌ها در دسترس هستند", evidence_status="database_result")

    assert _reply_needs_recovery(reply, context) is True

    context.last_result = {
        "columns": [
            "BrandName",
            "COGSAtLastPurchasePrice",
            "AllocatedSettlementDiscount",
            "ProfitAtLastPurchasePrice",
        ],
        "rows": [["برند نمونه", 70, 5, 25]],
        "row_count": 1,
    }

    assert _reply_needs_recovery(reply, context) is False


def test_brand_request_rejects_manufacturer_aliased_as_brand(settings):
    from app.chat_service import AgentContext, _brand_dimension_query_policy_error
    from app.sql_guard import validate_read_only_sql

    context = AgentContext(
        settings=settings,
        prepared_context={
            "resolved_request": {
                "standalone_request": "فروش از اول ماه عارف کامران به تفکیک برند"
            }
        },
    )
    invalid = validate_read_only_sql(
        "SELECT ManufacturerId, ManufacturerName AS BrandName "
        "FROM dbo.SalesReviewFast GROUP BY ManufacturerId, ManufacturerName"
    )

    error = _brand_dimension_query_policy_error(context, invalid)

    assert error is not None
    assert error["error_type"] == "brand_dimension_requires_brand_source"
    assert "ManufacturerName" in error["instruction"]

    valid = validate_read_only_sql(
        "SELECT gm.BrandRef, gm.BrandName FROM FRU.GoodsModel AS gm "
        "GROUP BY gm.BrandRef, gm.BrandName"
    )
    assert _brand_dimension_query_policy_error(context, valid) is None


def test_customer_financial_reply_without_live_evidence_requires_recovery(settings):
    from app.chat_service import AgentContext, AgentReply, _reply_needs_recovery

    context = AgentContext(
        settings=settings,
        prepared_context={"requires_live_database_evidence": True},
    )
    fabricated_denial = AgentReply(
        answer="کل کاردکس این مشتری خارج از سطح دسترسی شماست.",
        evidence_status="not_required",
    )

    assert _reply_needs_recovery(fabricated_denial, context) is True

    context.access_denied = True
    assert _reply_needs_recovery(fabricated_denial, context) is False


def test_all_cardex_code_followup_uses_previous_customer_without_date_filter(
    settings, monkeypatch
):
    from app.access_control import DataAccessPolicy
    from app.chat_service import _customer_cardex_period_followup_report

    captured = {}

    def fake_execute(_settings, validated):
        captured["sql"] = validated.sql
        return {
            "columns": ["Id", "CustID", "CustCode", "CustFullName"],
            "rows": [[1, 866, "2610862", "مشتری نمونه", None, None, "1405/01/01", None, None, 100, 40, 60, 1, 100, 40, 60, None, None, None]],
            "row_count": 1,
            "execution_time": 0.01,
            "truncated": False,
            "sources": ["dbo.CustomerCardex_Info"],
        }

    monkeypatch.setattr("app.chat_service.execute_query", fake_execute)
    report = _customer_cardex_period_followup_report(
        settings,
        DataAccessPolicy(username="Admin"),
        {
            "active_customer_financial_followup": {
                "route_name": "customer_cardex",
                "original_customer_request": "کد مشتری ۲۶۱۰۸۶۲ کاردکسش میاری",
            },
            "resolved_temporal_context": {"scope": "all_available_records"},
        },
    )

    assert report is not None
    assert "CustCode = N'2610862'" in captured["sql"]
    assert "VchDate =" not in captured["sql"]
    assert "COUNT(*)" not in captured["sql"]
    assert report["row_count"] == 1
    assert report["columns"] == [
        "تاریخ", "نوع سند", "شماره سند", "بدهکار", "بستانکار", "مانده", "شرح", "فروشنده"
    ]


def test_line_by_line_cardex_expands_and_returns_full_safe_page(settings, monkeypatch):
    from app.access_control import DataAccessPolicy
    from app.chat_service import _customer_cardex_period_followup_report

    captured = {}
    source_row = [
        1, 866, "2610304", "مشتری نمونه", "فاکتور", "12", "1405/01/01",
        None, None, 100, 40, 60, 572, 100, 40, 60, "شرح", None, "فروشنده",
    ]

    def fake_execute(_settings, validated):
        captured["sql"] = validated.sql
        return {
            "columns": [], "rows": [source_row] * 572, "row_count": 572,
            "execution_time": 0.01, "truncated": False,
            "sources": ["dbo.CustomerCardex_Info"],
        }

    monkeypatch.setattr("app.chat_service.execute_query", fake_execute)
    report = _customer_cardex_period_followup_report(
        settings,
        DataAccessPolicy(username="Admin"),
        {
            "active_customer_financial_followup": {
                "route_name": "customer_cardex",
                "original_customer_request": "کد مشتری ۲۶۱۰۳۰۴ کاردکسش بده",
            },
            "resolved_temporal_context": {"scope": "all_available_records"},
            "contextual_followup": {
                "original_message": "کاردکسش خط به خط بده",
                "standalone_request": "کل کاردکس مشتری ۲۶۱۰۳۰۴ را خط به خط بده",
            },
        },
    )

    assert "TOP 1000" in captured["sql"]
    assert report["row_count"] == 572
    assert report["presentation"]["expand_result"] is True
    assert report["presentation"]["visible_row_limit"] == 572
    assert "خط‌به‌خط" in report["answer"]


def test_short_contextual_followup_is_selected_after_assistant_question():
    from app.chat_service import _should_contextualize_followup

    history = [
        {"role": "user", "content": "کاردکس مشتری ۲۶۱۰۳۰۴ را بده"},
        {"role": "assistant", "content": "کل کاردکس یا بازه خاصی؟"},
    ]

    assert _should_contextualize_followup("کلش", history)
    assert _should_contextualize_followup("نه ماه قبل", history)
    assert _should_contextualize_followup("اون یکی رو هم بگو", history)
    assert not _should_contextualize_followup(
        "گزارش کامل فروش تهران را از ابتدای ماه به تفکیک برند بده", history
    )


def test_compound_refinements_and_corrections_are_contextualized():
    from app.chat_service import _should_contextualize_followup

    history = [
        {"role": "user", "content": "فروش این ماه عارف کامران را بگو"},
        {"role": "assistant", "content": "فروش این ماه عارف کامران آماده است."},
    ]

    assert _should_contextualize_followup(
        "حالا برگشتی‌هاشو کم کن و به تفکیک برند بده", history
    )
    assert _should_contextualize_followup("به تفکیک برندش کن", history)
    assert _should_contextualize_followup("منظورم عارف بود نه نوید", history)


def test_conversation_resolver_receives_saved_report_state(settings, monkeypatch):
    import json
    from types import SimpleNamespace

    from app.chat_service import ContextualFollowup, _resolve_conversation_request

    captured = {}
    resolved = ContextualFollowup(
        is_followup=True,
        standalone_request=(
            "فروش خالص این ماه عارف کامران را پس از کسر برگشتی "
            "به تفکیک برند بده"
        ),
        confidence=0.99,
        inherited_elements=["عارف کامران", "این ماه", "فروش"],
        intent="refinement",
        domain="sales",
        entity_mentions=["عارف کامران"],
        metrics=["فروش خالص", "برگشتی"],
        dimensions=["برند"],
        period_text="این ماه",
        corrections=["کسر برگشتی"],
    )

    def fake_run_sync(_agent, *args, **kwargs):
        captured["material"] = json.loads(kwargs["input"].split("\n", 1)[1])
        return SimpleNamespace(final_output=resolved)

    monkeypatch.setattr("app.chat_service.Runner.run_sync", fake_run_sync)
    result = _resolve_conversation_request(
        settings,
        "حالا برگشتی‌هاشو کم کن و به تفکیک برند بده",
        [
            {"role": "user", "content": "فروش این ماه عارف کامران را بگو"},
            {"role": "assistant", "content": "گزارش آماده است."},
        ],
        [
            {
                "report_context": {
                    "route": "sales",
                    "resolved_request": {
                        "standalone_request": "فروش این ماه عارف کامران را بگو",
                        "entity_mentions": ["عارف کامران"],
                        "period_text": "این ماه",
                    },
                }
            }
        ],
    )

    assert result.standalone_request == resolved.standalone_request
    state = captured["material"]["saved_report_state"][0]["report_context"]
    assert state["route"] == "sales"
    assert state["resolved_request"]["entity_mentions"] == ["عارف کامران"]


def test_same_report_followup_preserves_saved_period_without_model(settings, monkeypatch):
    from app.chat_service import _resolve_conversation_request

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("deterministic same-report follow-up must not call the model")

    monkeypatch.setattr("app.chat_service.Runner.run_sync", fail_if_called)
    state = [
        {
            "report_context": {
                "resolved_request": {
                    "standalone_request": "فروش کامل تاریخ 1405/05/27 را با درجه مشتری بده",
                    "domain": "sales",
                    "metrics": ["فروش"],
                    "dimensions": ["درجه مشتری"],
                    "period_text": "1405/05/27",
                }
            }
        }
    ]
    history = [
        {"role": "user", "content": "فروش بیست و هفت پنج را کامل بده"},
        {"role": "assistant", "content": "گزارش فروش 1405/05/27 آماده است."},
    ]

    resolved = _resolve_conversation_request(
        settings,
        "حالا همین فروش را به تفکیک تولیدکننده بده",
        history,
        state,
    )

    assert resolved.is_followup is True
    assert resolved.period_text == "1405/05/27"
    assert "1405/05/27" in resolved.standalone_request
    assert "به تفکیک تولیدکننده" in resolved.standalone_request


def test_clear_cardex_detail_followup_resolves_without_model():
    from app.chat_service import _deterministic_contextual_followup

    history = [
        {"role": "user", "content": "کد مشتری ۲۶۱۰۳۰۴ کاردکسش بده"},
        {"role": "assistant", "content": "کل کاردکس یا بازه خاصی؟"},
        {"role": "user", "content": "کلش"},
        {
            "role": "assistant",
            "content": "کل کاردکس آقای رضا مدیری (کد 2610304): 572 گردش",
        },
    ]

    resolved = _deterministic_contextual_followup(
        "کاردکسش خط به خط بده", history
    )

    assert resolved == (
        "کل کاردکس مشتری با کد 2610304 را خط‌به‌خط و با تمام ردیف‌های قابل‌دسترسی بده"
    )
    assert _deterministic_contextual_followup("کلش", history) == "کلش"
    assert _deterministic_contextual_followup("فروش امروز را بگو", history) is None


def test_colloquial_all_uses_saved_standalone_request(settings):
    from app.chat_service import _resolve_conversation_request

    history = [
        {"role": "user", "content": "کاردکس مشتری ۲۶۱۰۳۰۴ را بده"},
        {"role": "assistant", "content": "کل کاردکس یا بازه خاصی؟"},
    ]
    state = [
        {
            "report_context": {
                "resolved_request": {
                    "standalone_request": "کاردکس مشتری ۲۶۱۰۳۰۴ را بده",
                    "domain": "customer_cardex",
                    "entity_mentions": ["مشتری ۲۶۱۰۳۰۴"],
                    "metrics": ["کاردکس"],
                }
            }
        }
    ]

    resolved = _resolve_conversation_request(settings, "کلش", history, state)

    assert resolved.is_followup is True
    assert resolved.standalone_request.startswith("کاردکس مشتری ۲۶۱۰۳۰۴")
    assert "بدون محدودیت تاریخ" in resolved.standalone_request
    assert resolved.entity_mentions == ["مشتری ۲۶۱۰۳۰۴"]
    assert resolved.period_text == "کل سوابق"


def test_contextual_followup_accepts_only_confident_model_resolution(settings, monkeypatch):
    from types import SimpleNamespace
    from app.chat_service import ContextualFollowup, _contextualize_followup

    history = [
        {"role": "user", "content": "کاردکس مشتری ۲۶۱۰۳۰۴ را بده"},
        {"role": "assistant", "content": "کل کاردکس یا بازه خاصی؟"},
    ]
    resolved = ContextualFollowup(
        is_followup=True,
        standalone_request="کل کاردکس مشتری ۲۶۱۰۳۰۴ بدون محدودیت تاریخ را بده",
        confidence=0.98,
        inherited_elements=["مشتری ۲۶۱۰۳۰۴", "کاردکس"],
    )
    monkeypatch.setattr(
        "app.chat_service.Runner.run_sync",
        lambda *_args, **_kwargs: SimpleNamespace(final_output=resolved),
    )

    assert _contextualize_followup(settings, "کلش", history) == resolved.standalone_request

    resolved.confidence = 0.4
    assert _contextualize_followup(settings, "کلش", history) == "کلش"


def test_profit_report_keeps_earlier_complete_result_when_diagnostic_runs_last(settings):
    from app.chat_service import AgentContext, AgentReply, _prefer_contract_result

    complete_result = {
        "columns": [
            "BrandName",
            "COGSAtLastPurchasePrice",
            "AllocatedSettlementDiscount",
            "ProfitAtLastPurchasePrice",
        ],
        "rows": [["برند نمونه", 70, 5, 25]],
        "row_count": 1,
        "sources": ["dbo.SalesReviewFast"],
        "sql": "SELECT N'برند نمونه' AS BrandName",
    }
    diagnostic_result = {
        "columns": ["SoldGoodsCount", "GoodsWithPrice", "GoodsWithoutPrice"],
        "rows": [[1620, 1620, 0]],
        "row_count": 1,
        "sources": ["FRU.GoodsSupplierWithPriceModel"],
        "sql": "SELECT 1620 AS SoldGoodsCount",
    }
    context = AgentContext(
        settings=settings,
        prepared_context={
            "required_result_columns": {
                "groups": [
                    ["BrandName"],
                    ["ProfitAtLastPurchasePrice", "GrossProfitAtLastPurchasePrice"],
                    ["SettlementDiscountAmount", "AllocatedSettlementDiscount"],
                ]
            }
        },
        last_result=diagnostic_result,
        successful_results=[complete_result, diagnostic_result],
    )

    reply = _prefer_contract_result(
        AgentReply(answer="پوشش قیمت بررسی شد", evidence_status="database_result"),
        context,
    )

    assert context.last_result == complete_result
    assert reply.evidence_status == "database_result"
    assert "برند نمونه" in reply.answer
