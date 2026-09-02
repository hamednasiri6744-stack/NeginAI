import json
from datetime import datetime

from app.database import init_sqlite, sqlite_connection
from app.reasoning_context import (
    customer_financial_period_clarification_required,
    find_successful_report_examples,
    prepare_analysis_context,
    resolve_customer_financial_period_followup,
    resolve_temporal_context,
)
from app.definition_service import search_definitions
from app.varanegar_knowledge import detect_varanegar_route


def test_customer_financial_reports_require_period_choice_when_missing():
    assert customer_financial_period_clarification_required("کاردکس مشتری را بده")
    assert customer_financial_period_clarification_required("مانده حساب این مشتری چقدر است؟")
    assert customer_financial_period_clarification_required("مانده فاکتورهای باز مشتری را بده")
    assert customer_financial_period_clarification_required("مانده سوپر برتر چقدره؟")


def test_customer_financial_period_choice_is_not_reasked_when_explicit():
    assert not customer_financial_period_clarification_required("کاردکس امروز مشتری را بده")
    assert not customer_financial_period_clarification_required("کاردکس مشتری از 1405/05/01 تا 1405/05/20")
    assert not customer_financial_period_clarification_required("کل کاردکس و مانده مشتری را بده")
    assert not customer_financial_period_clarification_required("کاردکس کالای کدکس را بده")
    for answer in ("کلش", "همش", "همه‌ش", "تمامش", "کاملش"):
        assert not customer_financial_period_clarification_required(answer)


def test_all_cardex_followup_preserves_previous_customer_request():
    history = [
        {"role": "user", "content": "کد مشتری ۲۶۱۰۸۶۲ کاردکسش میاری"},
        {
            "role": "assistant",
            "content": "کل کاردکس را می‌خواهید یا بازه تاریخی خاصی؟",
        },
    ]

    resolved = resolve_customer_financial_period_followup("کل کاردکس گفتم", history)

    assert resolved is not None
    assert resolved["original_customer_request"] == history[0]["content"]
    assert resolved["period_scope"] == "all_available_records"


def test_colloquial_all_cardex_followups_preserve_previous_customer_request():
    history = [
        {"role": "user", "content": "2610304 کاردکس این مشتری بهم بده"},
        {"role": "assistant", "content": "کل کاردکس یا بازه خاص؟"},
    ]

    for answer in ("کلش", "همش", "همه‌ش", "تمامش", "کاملش"):
        resolved = resolve_customer_financial_period_followup(answer, history)
        assert resolved is not None
        assert resolved["period_scope"] == "all_available_records"
        assert resolved["route_name"] == "customer_cardex"


def test_colloquial_all_scope_does_not_inherit_today():
    temporal = resolve_temporal_context(
        "کلش",
        [{"role": "assistant", "content": "امروز گزارشی ثبت نشده است"}],
    )

    assert temporal["scope"] == "all_available_records"
    assert temporal["source"] == "current_request"


def test_dated_cardex_followup_preserves_previous_customer_request():
    history = [
        {"role": "user", "content": "مانده فاکتورهای باز مشتری ۲۶۱۰۸۶۲ را بده"},
        {"role": "assistant", "content": "کل یا بازه خاص؟"},
    ]

    resolved = resolve_customer_financial_period_followup(
        "از ۱۴۰۵/۰۱/۰۱ تا ۱۴۰۵/۰۵/۲۱", history
    )

    assert resolved is not None
    assert resolved["period_scope"] == "explicit_date_or_range"
    assert resolved["route_name"] == "invoice_balance"


def test_cardex_followup_preloads_official_cardex_sources(settings):
    history = [
        {"role": "user", "content": "کد مشتری ۲۶۱۰۸۶۲ کاردکسش میاری"},
        {"role": "assistant", "content": "کل یا بازه خاص؟"},
    ]

    context = prepare_analysis_context(settings, "کل کاردکس گفتم", history)

    assert context["analysis_route"].startswith("customer_cardex")
    assert context["active_customer_financial_followup"]["route_name"] == "customer_cardex"


def _save_report(conn, conversation_id, question, answer, sql, sources, base_id):
    conn.execute(
        """INSERT INTO chat_messages
           (id, conversation_id, role, content, sources_json, created_at)
           VALUES (?, ?, 'user', ?, '[]', '2026-08-08T00:00:00')""",
        (base_id, conversation_id, question),
    )
    conn.execute(
        """INSERT INTO chat_messages
           (id, conversation_id, role, content, sql_text, sources_json, created_at)
           VALUES (?, ?, 'assistant', ?, ?, ?, '2026-08-08T00:00:01')""",
        (base_id + 1, conversation_id, answer, sql, json.dumps(sources)),
    )


def test_successful_report_memory_prefers_semantically_relevant_question(settings):
    with sqlite_connection(settings.sqlite_path) as conn:
        _save_report(
            conn,
            "voucher",
            "آخرین حواله در چه ساعتی ثبت شده و کاربر آن کیست؟",
            "حواله ۴۸۶۰۹ ساعت ۲۱ ثبت شده است",
            "SELECT TOP (1) * FROM SLE.tblSaleHdr ORDER BY CreationDate DESC",
            ["SLE.tblSaleHdr", "dbo.AppUserFast"],
            100,
        )
        _save_report(
            conn,
            "inventory",
            "موجودی کالای زاکی را بده",
            "موجودی کالا",
            "SELECT TOP (10) * FROM dbo.InventoryFast",
            ["dbo.InventoryFast"],
            200,
        )

    examples = find_successful_report_examples(
        settings, "ثبت‌کننده و زمان آخرین حواله فروش را بگو", 3
    )

    assert examples
    assert "SLE.tblSaleHdr" in examples[0]["sql_pattern"]
    assert "InventoryFast" not in examples[0]["sql_pattern"]


def test_prepared_context_combines_semantics_schema_and_report_memory(settings):
    sale_header = {
        "schema": "SLE",
        "name": "tblSaleHdr",
        "type": "TABLE",
        "columns": [
            {"name": "SaleVocherNo"},
            {"name": "CreationDate"},
            {"name": "CreationBy"},
            {"name": "UserRef"},
        ],
        "foreign_keys": [],
        "referenced_by": [],
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO schema_objects
               (schema_name, object_name, object_type, details_json, scanned_at)
               VALUES ('SLE', 'tblSaleHdr', 'TABLE', ?, '2026-08-08T00:00:00')""",
            (json.dumps(sale_header),),
        )
        _save_report(
            conn,
            "voucher-context",
            "آخرین حواله و ثبت‌کننده را بگو",
            "نتیجه زنده",
            "SELECT TOP (1) SaleVocherNo FROM SLE.tblSaleHdr ORDER BY CreationDate DESC",
            ["SLE.tblSaleHdr"],
            300,
        )

    context = prepare_analysis_context(
        settings,
        "زمان و کاربر ثبت‌کننده آخرین حواله را بگو",
        [],
    )

    assert context["successful_report_examples"]
    assert any(item["name"] == "tblSaleHdr" for item in context["schema_candidates"])
    assert any("cached answers" in rule for rule in context["runtime_policy"])
    assert context["reporting_exclusions"]["person_ids"] == [7, 137, 192, 510]
    assert context["organization_structure"]["alborz"]["lines"]["لاین مارکت"]["team_split"] == "brand"
    assert context["organization_structure"]["alborz"]["lines"]["لاین گالری"]["team_split"] == "region_or_customer"


def test_general_context_prefers_matching_view_before_base_table(settings):
    view = {
        "schema": "dbo", "name": "SalesReportView", "type": "VIEW",
        "columns": [{"name": "SaleDate"}, {"name": "NetSales"}],
        "foreign_keys": [], "referenced_by": [],
    }
    table = {
        "schema": "dbo", "name": "SalesRawTable", "type": "TABLE",
        "columns": [{"name": "SaleDate"}, {"name": "NetSales"}],
        "foreign_keys": [], "referenced_by": [],
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        for item in (view, table):
            conn.execute(
                """INSERT INTO schema_objects
                   (schema_name, object_name, object_type, details_json, scanned_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (item["schema"], item["name"], item["type"], json.dumps(item), "2026-08-08T00:00:00"),
            )

    context = prepare_analysis_context(settings, "sales report", [])

    assert [item["name"] for item in context["schema_candidates"]] == ["SalesReportView"]
    assert context["schema_source_policy"] == "view_first"


def test_admin_context_searches_views_and_tables_across_full_catalog(settings):
    view = {
        "schema": "dbo", "name": "SalesReportView", "type": "VIEW",
        "columns": [{"name": "SaleDate"}, {"name": "NetSales"}],
        "foreign_keys": [], "referenced_by": [],
    }
    table = {
        "schema": "SLE", "name": "SalesManufacturerFacts", "type": "TABLE",
        "columns": [{"name": "SaleDate"}, {"name": "ManufacturerName"}],
        "foreign_keys": [], "referenced_by": [],
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        for item in (view, table):
            conn.execute(
                """INSERT INTO schema_objects
                   (schema_name, object_name, object_type, details_json, scanned_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (item["schema"], item["name"], item["type"], json.dumps(item), "2026-08-08T00:00:00"),
            )

    context = prepare_analysis_context(
        settings, "sales manufacturer report", [], None, True
    )

    assert {item["type"] for item in context["schema_candidates"]} == {"VIEW", "TABLE"}
    assert context["schema_source_policy"] == "admin_all_database"
    assert context["catalog_scope"]["search_scope"] == "all_catalogued_tables_and_views"
    assert any("not an allowlist" in rule for rule in context["runtime_policy"])


def test_view_first_context_keeps_only_six_initial_views(settings):
    with sqlite_connection(settings.sqlite_path) as conn:
        for index in range(7):
            item = {
                "schema": "dbo", "name": f"SalesView{index}", "type": "VIEW",
                "columns": [{"name": "NetSales"}], "foreign_keys": [], "referenced_by": [],
            }
            conn.execute(
                """INSERT INTO schema_objects
                   (schema_name, object_name, object_type, details_json, scanned_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (item["schema"], item["name"], item["type"], json.dumps(item), "2026-08-08T00:00:00"),
            )

    context = prepare_analysis_context(settings, "sales", [])

    assert len(context["schema_candidates"]) == 6
    assert {item["type"] for item in context["schema_candidates"]} == {"VIEW"}


def test_sales_route_uses_only_catalogued_sales_sources_and_examples(settings):
    sales = {
        "schema": "dbo", "name": "SalesReviewFast", "type": "VIEW",
        "columns": [{"name": "SaleDate"}, {"name": "NetSales"}],
        "foreign_keys": [], "referenced_by": [],
    }
    inventory = {
        "schema": "dbo", "name": "InventoryFast", "type": "VIEW",
        "columns": [{"name": "StockCount"}], "foreign_keys": [], "referenced_by": [],
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        for item, classification in ((sales, "customer_sales"), (inventory, "inventory")):
            conn.execute(
                """INSERT INTO schema_objects
                   (schema_name, object_name, object_type, details_json, scanned_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (item["schema"], item["name"], item["type"], json.dumps(item), "2026-08-08T00:00:00"),
            )
            conn.execute(
                """INSERT INTO schema_catalog
                   (schema_name, object_name, persian_name, description, domain,
                    data_classification, seller_access, aliases_json, updated_at)
                   VALUES (?, ?, '', '', '', ?, 'restricted', '[]', ?)""",
                (item["schema"], item["name"], classification, "2026-08-08T00:00:00"),
            )
        _save_report(
            conn, "sales-route", "فروش امروز", "گزارش فروش",
            "SELECT NetSales FROM dbo.SalesReviewFast", ["dbo.SalesReviewFast"], 400,
        )
        _save_report(
            conn, "inventory-route", "موجودی امروز", "گزارش موجودی",
            "SELECT StockCount FROM dbo.InventoryFast", ["dbo.InventoryFast"], 500,
        )

    context = prepare_analysis_context(settings, "فروش امروز را بگو", [])

    assert context["analysis_route"] == "sales"
    assert [item["name"] for item in context["schema_candidates"]] == ["SalesReviewFast"]
    assert context["successful_report_examples"]
    assert all("InventoryFast" not in item["sql_pattern"] for item in context["successful_report_examples"])


def test_legacy_sales_clarification_rule_is_migrated(settings):
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO definitions
               (term, definition, rules, related_objects_json, created_at, updated_at)
               VALUES (?, ?, ?, '[]', ?, ?)""",
            (
                "مبنای فروش / حواله / فاکتور / فروش خالص",
                "قدیمی",
                "این سوال شفاف‌ساز اجباری است.",
                "2026-08-08T00:00:00",
                "2026-08-08T00:00:00",
            ),
        )

    init_sqlite(settings.sqlite_path)

    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT definition, rules FROM definitions ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert "مجموع حواله و فاکتور" in row["definition"]
    assert "سؤال شفاف‌ساز نپرس" in row["rules"]


def test_temporal_context_inherits_today_from_recent_user_request():
    resolved = resolve_temporal_context(
        "کدام کاربر بیشترین دریافت خزانه را ثبت کرده؟",
        [
            {"role": "user", "content": "فروش امروز را بگو"},
            {"role": "assistant", "content": "گزارش فروش آماده شد"},
        ],
    )

    assert resolved["scope"] == "today"
    assert resolved["source"] == "previous_user_message"
    assert "without asking" in resolved["instruction"]


def test_relative_days_ago_is_an_explicit_current_period():
    resolved = resolve_temporal_context(
        "فروش دو روز پیش را بگو",
        [{"role": "user", "content": "فروش امروز را بگو"}],
    )

    assert resolved["scope"] == "relative_days_ago"
    assert resolved["matched_text"] == "دو روز پیش"
    assert resolved["source"] == "current_request"


def test_temporal_context_can_inherit_today_from_immediate_answer():
    resolved = resolve_temporal_context(
        "کدام کاربر بیشترین دریافت خزانه را ثبت کرده؟",
        [
            {
                "role": "assistant",
                "content": "آخرین حواله امروز ساعت ۲۱:۰۸ ثبت شده است.",
            }
        ],
    )

    assert resolved["scope"] == "today"
    assert resolved["source"] == "previous_assistant_message"


def test_all_records_request_overrides_an_inherited_today_period():
    resolved = resolve_temporal_context(
        "\u06a9\u0644 \u0645\u0633\u06cc\u0631\u0647\u0627\u06cc \u0639\u0627\u0631\u0641 \u06a9\u0627\u0645\u0631\u0627\u0646 \u0631\u0627 \u0628\u06af\u0648",
        [{"role": "user", "content": "\u0645\u0633\u06cc\u0631\u0647\u0627\u06cc \u0627\u0645\u0631\u0648\u0632 \u0631\u0627 \u0628\u06af\u0648"}],
    )

    assert resolved["scope"] == "all_available_records"
    assert resolved["source"] == "current_request"
    assert "Do not add a date filter" in resolved["instruction"]


def test_explicit_current_period_overrides_conversation_period():
    resolved = resolve_temporal_context(
        "بیشترین دریافت این ماه را بگو",
        [{"role": "user", "content": "فروش امروز را بگو"}],
    )

    assert resolved["scope"] == "current_month"
    assert resolved["source"] == "current_request"


def test_time_dependent_question_defaults_to_today_without_clarification():
    resolved = resolve_temporal_context(
        "کدام کاربر بیشترین دریافت خزانه را ثبت کرده؟",
        [],
    )

    assert resolved == {
        "scope": "today",
        "matched_text": "امروز",
        "source": "default_current_business_date",
        "instruction": (
            "For a time-dependent operational report, use the current business date without "
            "asking and briefly say that today was assumed."
        ),
    }


def test_prepared_context_exposes_resolved_temporal_scope(settings):
    context = prepare_analysis_context(
        settings,
        "کدام کاربر بیشترین دریافت خزانه را ثبت کرده؟",
        [{"role": "user", "content": "آخرین حواله امروز را بگو"}],
    )

    assert context["resolved_temporal_context"]["scope"] == "today"
    assert context["resolved_temporal_context"]["source"] == "previous_user_message"


def test_prepared_context_includes_verified_tehran_jalali_date(settings):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    context = prepare_analysis_context(
        settings,
        "\u0641\u0631\u0648\u0634 \u0627\u0645\u0631\u0648\u0632 \u0631\u0627 \u0628\u06af\u0648",
        [],
        datetime(2026, 8, 9, 14, 0, tzinfo=ZoneInfo("Asia/Tehran")),
    )

    temporal = context["resolved_temporal_context"]
    assert temporal["scope"] == "today"
    assert temporal["current_business_date"] == "1405/05/18"
    assert temporal["current_tehran_datetime"].startswith("2026-08-09T14:00:00")
    assert "1405/05/18" in " ".join(context["runtime_policy"])


def test_latest_record_without_a_period_is_not_forced_to_today():
    resolved = resolve_temporal_context(
        "\u0622\u062e\u0631\u06cc\u0646 \u0641\u0627\u06a9\u062a\u0648\u0631 \u0645\u0634\u062a\u0631\u06cc \u062c\u0627\u0645\u0628\u0648 \u06a9\u06cc \u0628\u0648\u062f\u0647\u061f",
        [],
    )

    assert resolved["scope"] == "all_time_latest_record"
    assert resolved["source"] == "current_request"


def _insert_view(conn, schema: str, name: str, columns: list[str]):
    item = {
        "schema": schema,
        "name": name,
        "type": "VIEW",
        "columns": [{"name": column} for column in columns],
        "foreign_keys": [],
        "referenced_by": [],
        "referenced_tables": [],
    }
    conn.execute(
        """INSERT INTO schema_objects
           (schema_name, object_name, object_type, details_json, scanned_at)
           VALUES (?, ?, 'VIEW', ?, '2026-08-11T00:00:00')""",
        (schema, name, json.dumps(item, ensure_ascii=False)),
    )


def test_varanegar_router_prefers_invoice_balance_view_over_generic_sales(settings):
    with sqlite_connection(settings.sqlite_path) as conn:
        _insert_view(conn, "dbo", "SalesReviewFast", ["SalesNetAmount"])
        _insert_view(
            conn,
            "Acc",
            "vwRcvSaleReview",
            ["SalesNetAmount", "SettlementAmount", "RemainingAmount", "PaymentStatus"],
        )

    context = prepare_analysis_context(settings, "مانده فاکتورهای باز مشتری را بده", [])

    assert context["analysis_route"] == "invoice_balance"
    assert context["analysis_route_label"] == "مانده و وضعیت تسویه فاکتور"
    assert context["schema_candidates"][0]["name"] == "vwRcvSaleReview"
    assert context["report_basis"] == "مبلغ خالص فاکتور منهای مبلغ تسویه‌شده"


def test_varanegar_router_separates_receipt_settlement_cardex_and_voucher():
    assert detect_varanegar_route("دریافت‌های باز خزانه").name == "receipt"
    assert detect_varanegar_route("جزئیات تسویه فاکتور").name == "settlement"
    assert detect_varanegar_route("کاردکس مشتری را بده").name == "customer_cardex"
    assert detect_varanegar_route("آخرین حواله فروش").name == "sales_voucher"


def test_varanegar_router_exposes_executable_operational_contract(settings):
    route = detect_varanegar_route("چک برگشتی فعال این مشتری را نشان بده")

    assert route is not None
    assert route.name == "returned_cheque"
    assert route.activity == "read"
    assert route.risk_level == "read_only"
    assert "customer" in route.required_context

    context = prepare_analysis_context(
        settings,
        "چک برگشتی فعال این مشتری را نشان بده",
        [],
    )

    assert context["analysis_route"].startswith("returned_cheque")
    assert context["operational_contract"]["activity"] == "read"
    assert context["operational_contract"]["risk_level"] == "read_only"
    assert "customer" in context["operational_contract"]["required_context"]
    assert any(
        "current status" in guard.lower()
        for guard in context["operational_contract"]["guards"]
    )


def test_varanegar_router_connects_order_activity_to_safe_previsit_workflow():
    route = detect_varanegar_route("برای این مشتری سفارش ثبت کن")

    assert route is not None
    assert route.name == "previsit_order"
    assert route.activity == "workflow"
    assert route.risk_level == "controlled_write"
    assert route.required_context == (
        "seller",
        "route",
        "customer",
        "warehouse",
        "order_type",
        "payment_type",
        "order_lines",
    )
    assert any("preview" in guard.lower() for guard in route.guards)


def test_varanegar_sales_contract_requires_scope_and_preserves_dimensions(settings):
    context = prepare_analysis_context(settings, "فروش این ماه را بده", [])

    contract = context["operational_contract"]
    assert context["analysis_route"].startswith("sales")
    assert contract["required_context"] == [
        "period",
        "organization_scope",
        "document_basis",
    ]
    assert any("distribution center" in guard.lower() for guard in contract["guards"])


def test_from_start_of_month_is_resolved_as_month_to_date(settings):
    context = prepare_analysis_context(
        settings,
        "فروش من به تفکیک برند بده از اول ماه برای عارف کامران",
        [],
        datetime(2026, 9, 1, 12, 0, 0),
    )

    temporal = context["resolved_temporal_context"]
    assert temporal["scope"] == "current_month_to_date"
    assert temporal["matched_text"] == "از اول ماه"
    assert temporal["current_business_date"] == "1405/06/10"


def test_profit_by_last_purchase_price_wins_over_settlement_modifier():
    route = detect_varanegar_route(
        "سود این ماه بر اساس آخرین قیمت خرید به تفکیک برند بده؛ "
        "تخفیفات تسویه را هم از فاکتورها کم کن"
    )

    assert route is not None
    assert route.name == "profit_last_purchase"
    assert route.sources[:3] == (
        "dbo.SalesReviewFast",
        "dbo.SalesReturnReviewFast",
        "FRU.GoodsModel",
    )
    assert any("ROW_NUMBER" in rule for rule in route.guidance)
    assert any("invoice" in rule.lower() and "brand" in rule.lower() for rule in route.guidance)


def test_varanegar_router_does_not_confuse_bank_transfer_with_sales_voucher():
    route = detect_varanegar_route("مبلغ حواله بانکی امروز چقدر بود؟")

    assert route is None or route.name != "sales_voucher"


def test_definition_search_does_not_match_only_on_generic_today(settings):
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO definitions
               (term, definition, rules, related_objects_json, created_at, updated_at)
               VALUES ('فروش امروز', 'تعریف فروش', '', '[]', ?, ?)""",
            ("2026-08-11T00:00:00", "2026-08-11T00:00:00"),
        )

    assert search_definitions(settings, "دریافت امروز") == []
