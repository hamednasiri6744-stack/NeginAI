from contextlib import contextmanager
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.auth_service import provision_users
from app.database import sqlite_connection
from app.seller_workspace_service import (
    SellerDayRouteMismatch,
    _active_customer_update_fields,
    _customer_cheque_intelligence,
    _ngt_visit_outcome_data,
    _route_visit_resolutions,
    _resolve_seller_location_policy,
    _seller_all_routes_test_override_enabled,
    require_seller_day_route,
    seller_brands, seller_customer_open_invoices, seller_customer_visit_workspace,
    seller_distribution_in_progress, seller_open_invoices,
    save_seller_route_customer_profile_draft, seller_route_customer_profile,
    seller_route_customers, seller_route_day_analytics, seller_routes, seller_visit_policy,
)


BRANCH = "\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632"
LINE = "\u0644\u0627\u06cc\u0646 \u0645\u0627\u0631\u06a9\u062a"


def test_route_visit_resolutions_show_completed_customer_and_saved_request_count(settings):
    now = datetime.now(timezone.utc).isoformat()
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            """INSERT INTO previsit_visits
               (id, username, route_id, customer_id, status, started_at, ended_at, created_at, updated_at)
               VALUES ('resolved-visit', 'A.kamran', 'route-1', '262', 'completed', ?, ?, ?, ?)""",
            (now, now, now, now),
        )
        connection.execute(
            """INSERT INTO previsit_drafts
               (id, visit_id, username, idempotency_key, cart_json, payment_type, order_type,
                outcome, outcome_reason, updated_at)
               VALUES ('resolved-draft', 'resolved-visit', 'A.kamran', 'resolved-idem', '[]', '', '',
                       'order', '', ?)""",
            (now,),
        )
        connection.execute(
            """INSERT INTO previsit_saved_requests
               (id, visit_id, username, route_id, customer_id, request_number, cart_json,
                payment_type, order_type, warehouse_name, preview_json, created_at, updated_at)
               VALUES ('saved-1', 'resolved-visit', 'A.kamran', 'route-1', '262', 1, '[]',
                       '', '', '', '{}', ?, ?)""",
            (now, now),
        )

    resolutions = _route_visit_resolutions(settings, "A.kamran", "route-1")

    assert resolutions["262"]["status"] == "completed"
    assert resolutions["262"]["outcome"] == "order"
    assert resolutions["262"]["saved_request_count"] == 1


def _seller(settings):
    provision_users(settings, [{
        "username": "A.kamran", "personnel_id": 22, "full_name": "\u0639\u0627\u0631\u0641 \u06a9\u0627\u0645\u0631\u0627\u0646",
        "role": "\u0641\u0631\u0648\u0634\u0646\u062f\u0647", "branch": BRANCH, "sales_line": LINE,
        "supervisor_personnel_id": 14,
    }])


def test_seller_brands_come_from_current_ngt_product_template(settings, monkeypatch):
    _seller(settings)
    calls = []

    class Cursor:
        description = []
        rows = []
        def execute(self, sql):
            calls.append(sql)
            self.description = [(name,) for name in (
                "ProductTemplateName", "BrandRef", "BrandName", "ProductCount",
            )]
            self.rows = [
                ("Alborz line 2", 1, "Confident", 107),
                ("Alborz line 2", 2, "Codex", 53),
            ]
        def fetchall(self): return self.rows

    class Connection:
        def cursor(self): return Cursor()
        def rollback(self): pass
        def close(self): pass

    @contextmanager
    def fake_connection(_settings):
        yield Connection()

    monkeypatch.setattr("app.seller_workspace_service.sql_connection", fake_connection)

    result = seller_brands(settings, "A.kamran")

    assert result["supervisor"]["personnel_id"] == 14
    assert result["product_template"] == "Alborz line 2"
    assert result["configured"] is True
    assert result["brands"] == ["Confident", "Codex"]
    assert result["brand_details"][0] == {"id": 1, "name": "Confident", "product_count": 107}
    assert result["source"] == "NGT.ProductTemplateDetails"
    assert result["live_assignment"] is True
    assert len(calls) == 1
    assert "BackOfficeId = N'22'" in calls[0]
    assert "NGT.ProductTemplateDetails" in calls[0]
    assert "GNR.tblGoods" in calls[0]
    assert "GNR.tblBrand" in calls[0]


def test_day_route_invoice_recency_weights_prioritize_recent_and_four_to_six_month_invoices():
    source = open("app/seller_workspace_service.py", encoding="utf-8").read()

    assert "9 if current_month - month <= 2 else 6 if 4 <= current_month - month <= 6 else 1" in source


def test_seller_routes_use_current_ngt_visit_template_only(settings, monkeypatch):
    _seller(settings)
    calls = []

    class Cursor:
        description = []
        rows = []
        def execute(self, sql):
            calls.append(sql)
            self.description = [(name,) for name in (
                "VisitTemplateName", "PathId", "PathTitle", "RowIndex", "LastUpdate", "CustomerCount",
            )]
            self.rows = [
                ("Kamran current template", "11111111-1111-1111-1111-111111111111", "Route A", 1, None, 36),
                ("Kamran current template", "22222222-2222-2222-2222-222222222222", "Route B", 2, None, 35),
            ]
        def fetchall(self): return self.rows

    class Connection:
        def cursor(self): return Cursor()
        def rollback(self): pass
        def close(self): pass

    @contextmanager
    def fake_connection(_settings):
        yield Connection()

    monkeypatch.setattr("app.seller_workspace_service.sql_connection", fake_connection)
    monkeypatch.setattr(
        "app.seller_workspace_service._resolve_seller_day_route",
        lambda *_args: {
            "id": "22222222-2222-2222-2222-222222222222",
            "title": "Route B",
            "date": "1405/06/01",
            "source": "NGT.VisitPlans",
        },
    )
    monkeypatch.setattr(
        "app.seller_workspace_service._resolve_seller_location_policy",
        lambda *_args: {
            "enabled": True,
            "max_distance_meters": 100,
            "scope": "مشتریان روز",
            "scope_code": "CheckDistanceType.DayPathCustomers",
            "enforced": False,
            "mode": "observe_only",
            "source": "NGT.DeviceUsers -> NGT.DeviceSettings",
        },
    )

    result = seller_routes(settings, "A.kamran")

    assert result["live_assignment"] is True
    assert result["source"] == "NGT.Personnels.VisitTemplateUniqueId"
    assert result["visit_template"] == "Kamran current template"
    assert [route["title"] for route in result["routes"]] == ["Route A", "Route B"]
    assert result["routes"][0]["customer_count"] == 36
    assert result["routes"][0]["id"] == "11111111-1111-1111-1111-111111111111"
    assert result["routes"][0]["can_start_day_route"] is False
    assert result["routes"][1]["can_start_day_route"] is True
    assert result["routes"][1]["can_start_visit"] is True
    assert result["day_route"] == {
        "id": "22222222-2222-2222-2222-222222222222",
        "title": "Route B",
        "date": "1405/06/01",
        "source": "NGT.VisitPlans",
    }
    assert result["visit_location_policy"]["enabled"] is True
    assert result["visit_location_policy"]["max_distance_meters"] == 100
    assert result["visit_location_policy"]["enforced"] is False
    assert len(calls) == 1
    assert all("BackOfficeId = N'22'" in sql for sql in calls)
    assert all("NGT.Tours" not in sql and "NGT.DayPaths" not in sql for sql in calls)


def test_seller_location_policy_preserves_ngt_rule_while_start_check_is_suspended(settings, monkeypatch):
    calls = []

    def fake_rows(_settings, sql):
        calls.append(sql)
        return [{
            "CheckDistance": True,
            "MaxDistance": 100,
            "CheckDistanceTypeName": "مشتریان روز",
            "CheckDistanceTypeCode": "CheckDistanceType.DayPathCustomers",
            "EnableGPS": True,
        }]

    monkeypatch.setattr("app.seller_workspace_service._query_rows", fake_rows)

    policy = _resolve_seller_location_policy(settings, 22)

    assert policy["enabled"] is True
    assert policy["max_distance_meters"] == 100
    assert policy["scope"] == "مشتریان روز"
    assert policy["scope_code"] == "CheckDistanceType.DayPathCustomers"
    assert policy["enforced"] is False
    assert policy["mode"] == "suspended_for_testing"
    assert policy["enforcement_stage"] == "disabled"
    assert policy["gps_enabled"] is True
    assert policy["reports"] == {
        "invoices": False, "cardex": False, "open_invoices": False,
        "sale_history": False, "finance": False,
    }
    assert policy["source"] == "NGT.DeviceUsers -> NGT.DeviceSettings + NGT.AppSettings"
    assert len(calls) == 1
    assert "NGT.Users AS users" in calls[0]
    assert "NGT.DeviceUsers AS device_user" in calls[0]
    assert "NGT.DeviceSettings AS device_settings" in calls[0]
    assert "users.BackOfficePersonnelId = 22" in calls[0]
    assert "CheckDistance" in calls[0]
    assert "MaxDistance" in calls[0]
    assert "EnableGPS" in calls[0]
    assert "SetCustomerLocation" in calls[0]
    assert "AllowEditCustomer" in calls[0]
    assert "MandatoryCustomerVisit" in calls[0]

    enabled_policy = _resolve_seller_location_policy(
        replace(settings, previsit_start_distance_check_enabled=True), 22
    )
    assert enabled_policy["enabled"] is True
    assert enabled_policy["enforced"] is True
    assert enabled_policy["mode"] == "enforced_at_start"
    assert enabled_policy["enforcement_stage"] == "start"


def test_suspended_distance_rule_does_not_block_visit_start_for_missing_location(settings, monkeypatch):
    monkeypatch.setattr(
        "app.seller_workspace_service._assigned_route_customer",
        lambda *_args: (
            {
                "route": {"id": "route-1", "title": "مسیر امروز"},
                "visit_location_policy": {
                    "enabled": True,
                    "enforced": False,
                    "mode": "suspended_for_testing",
                    "max_distance_meters": 100,
                    "required_customer_fields": [],
                },
            },
            {
                "id": "2647417",
                "name": "امیر",
                "store_name": "امیر",
                "latitude": None,
                "longitude": None,
                "location_check_exempt": False,
            },
        ),
    )
    monkeypatch.setattr(
        "app.seller_workspace_service._ngt_visit_outcome_data",
        lambda *_args: {"reasons": {"no_order": [], "no_visit": []}, "visit_status_ids": {}},
    )

    policy = seller_visit_policy(settings, "A.kamran", "route-1", "2647417")

    assert policy["controls"]["enabled"] is True
    assert policy["controls"]["enforced"] is False
    assert policy["start_blockers"] == []
    assert policy["can_start_visit"] is True


def test_saved_customer_draft_satisfies_required_visit_fields(settings, monkeypatch):
    route_id = "route-required"
    customer_id = "2647417"
    monkeypatch.setattr(
        "app.seller_workspace_service._assigned_route_customer",
        lambda *_args: (
            {"route": {"id": route_id, "title": "مسیر امروز"}, "visit_location_policy": {"required_customer_fields": ["phone"], "enforced": False}},
            {"id": customer_id, "name": "امیر", "phone": "", "latitude": None, "longitude": None},
        ),
    )
    monkeypatch.setattr("app.seller_workspace_service._ngt_visit_outcome_data", lambda *_args: {"reasons": {"no_order": [], "no_visit": []}, "visit_status_ids": {}})
    before = seller_visit_policy(settings, "A.kamran", route_id, customer_id)
    assert before["start_blockers"] == []
    assert before["order_blockers"] == ["اطلاعات اجباری مشتری باید پیش از سفارش‌گیری تکمیل شود"]
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            "INSERT INTO previsit_customer_update_drafts (username, route_id, customer_id, update_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("A.kamran", route_id, customer_id, '{"phone":"09120000000"}', "2026-08-29", "2026-08-29"),
        )

    policy = seller_visit_policy(settings, "A.kamran", route_id, customer_id)

    assert policy["missing_required_fields"] == []
    assert policy["start_blockers"] == []
    assert policy["can_start_visit"] is True


def test_visit_outcome_reasons_and_statuses_use_active_ngt_reference_data(settings, monkeypatch):
    calls = []

    def fake_rows(_settings, sql):
        calls.append(sql)
        if "NGT.NoSaleReasons" in sql:
            return [
                {"ReasonId": "r1", "ReasonName": "عدم نیاز به کالا", "ReasonTypeId": "t1", "ReasonTypeName": "NoSaleReasonTypes.NoOrder"},
                {"ReasonId": "r2", "ReasonName": "بسته بودن", "ReasonTypeId": "t2", "ReasonTypeName": "NoSaleReasonTypes.NoVisit"},
            ]
        return [
            {"VisitStatusId": "s1", "VisitStatusName": "عدم سفارش", "VisitStatusCode": "VisitStatusTypes.NoOrder"},
            {"VisitStatusId": "s2", "VisitStatusName": "عدم ویزیت", "VisitStatusCode": "VisitStatusTypes.NoVisit"},
            {"VisitStatusId": "s3", "VisitStatusName": "قطعی", "VisitStatusCode": "VisitStatusTypes.Determind"},
        ]

    monkeypatch.setattr("app.seller_workspace_service._query_rows", fake_rows)
    result = _ngt_visit_outcome_data(settings)

    assert result["reasons"]["no_order"] == [{"id": "r1", "title": "عدم نیاز به کالا", "type_id": "t1"}]
    assert result["reasons"]["no_visit"] == [{"id": "r2", "title": "بسته بودن", "type_id": "t2"}]
    assert result["visit_status_ids"] == {"order": "s3", "no_order": "s1", "no_visit": "s2"}
    assert "ShowForNgt" in calls[0]
    assert "NGT.PublicValues" in calls[0]
    assert "VisitStatusTypes.NoVisit" in calls[1]


def test_day_route_resolver_matches_ngt_override_tour_and_visit_plan_sources(settings, monkeypatch):
    from app.seller_workspace_service import _resolve_seller_day_route

    calls = []

    def fake_rows(_settings, sql):
        calls.append(sql)
        return [{
            "PathId": "22222222-2222-2222-2222-222222222222",
            "PathTitle": "Route B",
            "RoutePDate": "1405/06/01",
            "RouteSource": "NGT.VisitPlans",
        }]

    monkeypatch.setattr("app.seller_workspace_service._query_rows", fake_rows)

    result = _resolve_seller_day_route(settings, 22)

    assert result["id"] == "22222222-2222-2222-2222-222222222222"
    assert result["source"] == "NGT.VisitPlans"
    assert len(calls) == 1
    assert "NGT.DayPaths" in calls[0]
    assert "NGT.Tours" in calls[0]
    assert "NGT.VisitPlans" in calls[0]
    assert "NGT.CalendarTemplates" in calls[0]
    assert "NGT.CalendarTemplateHolidays" in calls[0]
    assert "NGT.VisitPlanVacations" in calls[0]
    assert "HolidayShiftEnabled" in calls[0]


def test_non_day_route_cannot_start_even_when_it_is_in_current_template(settings, monkeypatch):
    monkeypatch.setattr(
        "app.seller_workspace_service._seller_profile",
        lambda *_args: {"personnel_id": 22, "supervisor_personnel_id": 14, "role": "فروشنده"},
    )
    monkeypatch.setattr(
        "app.seller_workspace_service._resolve_seller_day_route",
        lambda *_args: {
            "id": "22222222-2222-2222-2222-222222222222",
            "title": "Route B",
            "date": "1405/06/01",
            "source": "NGT.VisitPlans",
        },
    )

    with pytest.raises(SellerDayRouteMismatch, match="مسیر روز NGT"):
        require_seller_day_route(
            settings,
            "A.kamran",
            "11111111-1111-1111-1111-111111111111",
        )


def test_temporary_all_routes_override_is_scoped_to_username_and_expiry(settings):
    temporary_settings = replace(
        settings,
        previsit_test_all_routes_username="A.kamran",
        previsit_test_all_routes_until="2026-08-28T23:59:59+03:30",
    )

    assert _seller_all_routes_test_override_enabled(
        temporary_settings,
        "a.KAMRAN",
        now=datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc),
    ) is True
    assert _seller_all_routes_test_override_enabled(
        temporary_settings,
        "another.seller",
        now=datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc),
    ) is False
    assert _seller_all_routes_test_override_enabled(
        temporary_settings,
        "A.kamran",
        now=datetime(2026, 8, 28, 21, 0, tzinfo=timezone.utc),
    ) is False


def test_temporary_override_allows_only_assigned_routes_for_configured_seller(settings, monkeypatch):
    temporary_settings = replace(
        settings,
        previsit_test_all_routes_username="A.kamran",
        previsit_test_all_routes_until="2099-12-31T23:59:59+03:30",
    )
    assigned_rows = [
        {
            "VisitTemplateName": "Kamran current template",
            "PathId": "11111111-1111-1111-1111-111111111111",
            "PathTitle": "Route A",
            "RowIndex": 1,
            "LastUpdate": None,
            "CustomerCount": 36,
        },
        {
            "VisitTemplateName": "Kamran current template",
            "PathId": "22222222-2222-2222-2222-222222222222",
            "PathTitle": "Route B",
            "RowIndex": 2,
            "LastUpdate": None,
            "CustomerCount": 35,
        },
    ]
    monkeypatch.setattr(
        "app.seller_workspace_service._seller_profile",
        lambda *_args: {
            "personnel_id": 22,
            "supervisor_personnel_id": 14,
            "role": "فروشنده",
            "full_name": "عارف کامران",
        },
    )
    monkeypatch.setattr(
        "app.seller_workspace_service._resolve_seller_day_route", lambda *_args: None
    )
    monkeypatch.setattr(
        "app.seller_workspace_service._resolve_seller_location_policy", lambda *_args: {}
    )
    monkeypatch.setattr(
        "app.seller_workspace_service._query_rows", lambda *_args: assigned_rows
    )

    routes = seller_routes(temporary_settings, "A.kamran")

    assert routes["day_route"] is None
    assert routes["day_route_status"] == "temporary_all_routes"
    assert routes["test_all_routes_override"] is True
    assert all(route["can_start_visit"] for route in routes["routes"])
    assert all(route["can_start_day_route"] for route in routes["routes"])
    assert not any(route["is_day_route"] for route in routes["routes"])

    allowed = require_seller_day_route(
        temporary_settings,
        "A.kamran",
        "11111111-1111-1111-1111-111111111111",
    )
    assert allowed["source"] == "temporary_test_override"

    with pytest.raises(SellerDayRouteMismatch, match="تخصیص‌یافته"):
        require_seller_day_route(
            temporary_settings,
            "A.kamran",
            "33333333-3333-3333-3333-333333333333",
        )


def test_sales_priority_route_keeps_high_and_medium_probability_customers_first(settings, monkeypatch):
    from app.seller_workspace_service import seller_route_map_plan

    customers = [
        {"id": "low", "name": "Low", "store_name": "Low", "latitude": 35.60, "longitude": 51.30},
        {"id": "high", "name": "High", "store_name": "High", "latitude": 35.70, "longitude": 51.40},
        {"id": "medium", "name": "Medium", "store_name": "Medium", "latitude": 35.65, "longitude": 51.35},
    ]
    monkeypatch.setattr("app.seller_workspace_service.seller_route_customers", lambda *_: {
        "route": {"id": "route"}, "customers": customers, "customer_count": 3,
    })
    monkeypatch.setattr("app.seller_workspace_service.seller_route_day_analytics", lambda *_: {"customers": [
        {"id": "low", "visit_score": 1}, {"id": "high", "visit_score": 10}, {"id": "medium", "visit_score": 5},
    ]})
    monkeypatch.setattr("app.seller_workspace_service._neshan_get", lambda *args: (
        {"points": [{"index": 0}, {"index": 1}]} if "trip" in args[0]
        else {"routes": [{"overview_polyline": {"points": ""}, "legs": []}]}
    ))
    settings = replace(settings, neshan_service_api_key="configured")

    plan = seller_route_map_plan(settings, "A.kamran", "route", 35.50, 51.20, "sales_priority")

    assert [item["id"] for item in plan["ordered_customers"]] == ["high", "medium", "low"]
    assert [item["priority_tier"] for item in plan["ordered_customers"]] == ["high", "medium", "low"]
    assert plan["route_mode"] == "sales_priority"


def test_route_map_plan_keeps_customers_when_optional_analytics_times_out(settings, monkeypatch):
    from app.seller_workspace_service import seller_route_map_plan

    customers = [
        {"id": "one", "name": "One", "store_name": "One", "latitude": 35.70, "longitude": 51.40},
        {"id": "two", "name": "Two", "store_name": "Two", "latitude": 35.65, "longitude": 51.35},
    ]
    monkeypatch.setattr("app.seller_workspace_service.seller_route_customers", lambda *_: {
        "route": {"id": "route"}, "customers": customers, "customer_count": 2,
        "visit_location_policy": {"distance_control_enabled": True},
    })
    analytics_timeouts = []

    def timed_out_analytics(analytics_settings, *_args):
        analytics_timeouts.append(analytics_settings.sql_query_timeout)
        raise TimeoutError("analytics query timed out")

    monkeypatch.setattr("app.seller_workspace_service.seller_route_day_analytics", timed_out_analytics)
    monkeypatch.setattr("app.seller_workspace_service._neshan_get", lambda *args: (
        {"points": [{"index": 0}, {"index": 1}, {"index": 2}]} if "trip" in args[0]
        else {"routes": [{"overview_polyline": {"points": ""}, "legs": []}]}
    ))
    settings = replace(settings, neshan_service_api_key="configured", sql_query_timeout=30)

    plan = seller_route_map_plan(settings, "A.kamran", "route", 35.50, 51.20, "sales_priority")

    assert analytics_timeouts == [5]
    assert plan["analytics_available"] is False
    assert {item["id"] for item in plan["ordered_customers"]} == {"one", "two"}
    assert plan["visit_location_policy"]["distance_control_enabled"] is True


def test_day_route_analytics_exposes_brand_line_amount_date_and_last_seller(settings, monkeypatch):
    monkeypatch.setattr(
        "app.seller_workspace_service._seller_profile",
        lambda *_args: {"personnel_id": 22, "full_name": "عارف کامران"},
    )
    monkeypatch.setattr(
        "app.seller_workspace_service.seller_brands",
        lambda *_args: {"brand_details": [{"id": 1, "name": "میسویک"}]},
    )
    captured = []

    def fake_rows(_settings, sql):
        captured.append(sql)
        if "Acc.vwRcvSaleReview" in sql:
            return [{
                "PathId": "11111111-1111-1111-1111-111111111111", "PathTitle": "مسیر امروز",
                "BackOfficeId": "2647417", "CustomerCode": "2647417", "CustomerName": "امیر",
                "StoreName": "فروشگاه امیر", "CompanyInvoiceCount12M": 8,
                "CompanyNetSales12M": 12_000_000, "LastInvoiceDate": "1405/05/20",
                "SellerInvoiceCount12M": 3, "SellerNetSales12M": 4_000_000,
            }]
        if "N'brand' AS RecordKind" in sql:
            return [
                {
                    "RecordKind": "brand", "CustomerId": 2647417, "BrandName": "میسویک",
                    "InvoiceCount": 3, "NetSales": 4_500_000, "LastPurchaseDate": "1405/05/20",
                    "IsSellerLineBrand": 1, "SalesLine": "لاین مارکت", "BranchName": "دفتر فروش البرز",
                    "LastSellerId": 22, "LastSellerName": "عارف کامران", "LastSellerMobile": "09121234567",
                },
                {
                    "RecordKind": "line", "CustomerId": 2647417, "BrandName": "",
                    "InvoiceCount": 5, "NetSales": 9_000_000, "LastPurchaseDate": "1405/05/20",
                    "IsSellerLineBrand": 0, "SalesLine": "لاین مارکت", "BranchName": "دفتر فروش البرز",
                    "LastSellerId": 22, "LastSellerName": "عارف کامران", "LastSellerMobile": "09121234567",
                },
            ]
        if "SELECT sale.CustomerId, sale.SellId" in sql:
            return [{"CustomerId": 2647417, "SellId": 10, "ReportDate": "1405/05/20"}]
        return [{"BrandName": "میسویک", "InvoiceCount": 3}]

    monkeypatch.setattr("app.seller_workspace_service._query_rows", fake_rows)

    result = seller_route_day_analytics(
        settings, "A.kamran", "11111111-1111-1111-1111-111111111111"
    )
    customer = result["customers"][0]

    assert customer["line_purchased_brands"] == [{
        "name": "میسویک", "invoice_count": 3, "net_sales": 4_500_000.0,
        "last_purchase_date": "1405/05/20", "sales_line": "لاین مارکت",
        "branch": "دفتر فروش البرز", "last_seller_id": 22,
        "last_seller_name": "عارف کامران", "last_seller_mobile": "09121234567",
    }]
    assert customer["line_purchase_summary"] == [{
        "name": "لاین مارکت", "branch": "دفتر فروش البرز", "invoice_count": 5,
        "net_sales": 9_000_000.0, "last_purchase_date": "1405/05/20",
        "last_seller_id": 22, "last_seller_name": "عارف کامران",
        "last_seller_mobile": "09121234567",
    }]
    detail_sql = next(sql for sql in captured if "N'brand' AS RecordKind" in sql)
    assert "sale.SellDetailID" in detail_sql
    assert "sale.SellNetAmount" in detail_sql
    assert "sale.SellReturnNetAmount" in detail_sql
    assert "sale.DealerName" in detail_sql
    assert "sale.CustomerCategoryName" in detail_sql
    assert "COUNT(DISTINCT SellId)" in detail_sql
    assert "dbo.Contact AS contact" in detail_sql
    assert "LastSellerMobile" in detail_sql


def test_seller_can_list_only_customers_on_own_current_route(settings, monkeypatch):
    _seller(settings)
    calls = []
    path_id = "11111111-1111-1111-1111-111111111111"

    class Cursor:
        description = []
        rows = []
        def execute(self, sql):
            calls.append(sql)
            self.description = [(name,) for name in (
                "PathId", "PathTitle", "RowIndex", "BackOfficeId", "CustomerCode",
                "CustomerName", "StoreName", "Address", "Phone", "Mobile",
                "Latitude", "Longitude", "IgnoreLocation",
                "BedCredit", "AsnCredit", "HasBedCredit", "HasAsnCredit",
                "RemBedCredit", "RemAsnCredit", "CustomerRemaining",
                "OpenChequeCount", "OpenChequeAmount", "ReturnChequeCount", "ReturnChequeAmount",
                "CreditDcRef", "CreditLastUpdate",
                "CustomerCardexBalance", "OpenInvoiceRemaining", "OpenInvoiceCount",
            )]
            self.rows = [(
                path_id, "Route A", 1, "262", "2610258", "Ali",
                 "Super Store", "Address A", "33522138", "09120000000", 35.6892, 51.3890, 1,
                 20_000_000, 50_000_000, 1, 1, 7_000_000, 12_000_000, 3_500_000,
                 2, 4_000_000, 1, 1_500_000, 1, "2026-08-23 10:00:00",
                 1250000, 430000, 2,
            )]
        def fetchall(self): return self.rows

    class Connection:
        def cursor(self): return Cursor()
        def rollback(self): pass
        def close(self): pass

    @contextmanager
    def fake_connection(_settings):
        yield Connection()

    monkeypatch.setattr("app.seller_workspace_service.sql_connection", fake_connection)
    monkeypatch.setattr(
        "app.seller_workspace_service._resolve_seller_location_policy",
        lambda *_args: {"enabled": False, "enforced": False, "mode": "observe_only"},
    )
    monkeypatch.setattr(
        "app.seller_workspace_service._route_visit_resolutions",
        lambda *_args: {"262": {"status": "completed", "outcome": "order", "saved_request_count": 2}},
    )
    with sqlite_connection(settings.sqlite_path) as connection:
        connection.execute(
            "INSERT INTO customer_geo_locations(customer_id, latitude, longitude, source, updated_by, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("262", 35.7, 51.4, "erp", "system", "2026-08-16T00:00:00"),
        )

    result = seller_route_customers(settings, "A.kamran", path_id)

    assert result["route"] == {"id": path_id, "title": "Route A"}
    assert result["customer_count"] == 1
    assert result["customers"][0]["store_name"] == "Super Store"
    assert result["customers"][0]["mobile"] == "09120000000"
    assert result["customers"][0]["latitude"] == 35.7
    assert result["customers"][0]["longitude"] == 51.4
    assert result["customers"][0]["cardex_balance"] == 1250000
    assert result["customers"][0]["open_invoice_remaining"] == 430000
    assert result["customers"][0]["open_invoice_count"] == 2
    assert result["customers"][0]["location_check_exempt"] is True
    assert result["customers"][0]["visit_resolution"] == {
        "status": "completed", "outcome": "order", "saved_request_count": 2,
    }
    assert result["customers"][0]["financial_snapshot"] == {
        "bed_credit": 20_000_000.0,
        "remaining_bed_credit": 7_000_000.0,
        "asn_credit": 50_000_000.0,
        "remaining_asn_credit": 12_000_000.0,
        "has_bed_credit": True,
        "has_asn_credit": True,
        "combined_remaining": 19_000_000.0,
        "customer_remaining": 3_500_000.0,
        "open_cheque_count": 2,
        "open_cheque_amount": 4_000_000.0,
        "returned_cheque_count": 1,
        "returned_cheque_amount": 1_500_000.0,
        "dc_ref": 1,
        "updated_at": "2026-08-23 10:00:00",
        "source": "GNR.tblCust + Acc.tblCustRemInfo",
    }
    assert len(calls) == 1
    assert "BackOfficeId = N'22'" in calls[0]
    assert f"path.Id = CAST(N'{path_id}' AS uniqueidentifier)" in calls[0]
    assert "NGT.VisitTemplatePathCustomers" in calls[0]
    assert "NGT.VisitTemplatePathSecondaryCustomers" in calls[0]
    assert "NGT.Customers" in calls[0]
    assert "customer.Latitude, customer.Longitude" in calls[0]
    assert "customer.IgnoreLocation" in calls[0]
    assert "backoffice_customer.BedCredit" in calls[0]
    assert "backoffice_customer.AsnCredit" in calls[0]
    assert "credit_snapshot.RemBedCredit" in calls[0]
    assert "credit_snapshot.RemAsnCredit" in calls[0]
    assert "Acc.tblCustRemInfo" in calls[0]
    assert "SUM(balance.Balance)" in calls[0]
    assert "Acc.vwRcvSaleReview" in calls[0]
    assert "sale.DealerId = 22" in calls[0]
    assert "sale.RemainingAmount > 0" in calls[0]


def test_seller_open_invoices_are_limited_to_current_route_customers_and_seller(settings, monkeypatch):
    _seller(settings)
    calls = []

    class Cursor:
        description = []
        def execute(self, sql):
            calls.append(sql)
            self.description = [(name,) for name in (
                "BackOfficeId", "CustomerCode", "CustomerName", "StoreName", "Address", "Phone", "Mobile",
                "ReturnChequeCount", "ReturnChequeAmount", "CustomerCardexBalance", "OpenInvoiceRemaining",
                "OpenInvoiceCount", "OldestOpenInvoiceDate",
            )]
        def fetchall(self):
            return [("2610258", "2610258", "Ali", "Super Store", "Address A", "33522138", "09120000000", 3, 125000, 1250000, 430000, 2, "1404/01/12")]

    class Connection:
        def cursor(self): return Cursor()
        def rollback(self): pass
        def close(self): pass

    @contextmanager
    def fake_connection(_settings):
        yield Connection()

    monkeypatch.setattr("app.seller_workspace_service.sql_connection", fake_connection)
    result = seller_open_invoices(settings, "A.kamran")

    assert result["customer_count"] == 1
    assert result["open_invoice_remaining"] == 430000
    assert result["customers"][0]["store_name"] == "Super Store"
    assert result["customers"][0]["oldest_open_invoice_date"] == "1404/01/12"
    assert result["customers"][0]["return_cheque_count"] == 3
    assert result["customers"][0]["return_cheque_amount"] == 125000
    assert "sale.DealerId = 22" in calls[0]
    assert "GROUP BY sale.CustId, sale.SaleId" in calls[0]
    assert "ISNULL(customer.IsActive, 1)" not in calls[0]
    assert "Acc.tblCustRemInfo" in calls[0]
    assert "COALESCE(MIN(sale.SaleDate), MIN(sale.SaleVocherDate), MIN(sale.ReportDate)) AS InvoiceDate" in calls[0]
    assert "ORDER BY open_invoices.OldestOpenInvoiceDate" in calls[0]


def test_seller_can_list_a_current_route_customers_open_invoices(settings, monkeypatch):
    _seller(settings)
    calls = []

    class Cursor:
        description = []
        def execute(self, sql):
            calls.append(sql)
            self.description = [(name,) for name in (
                "SaleId", "InvoiceNumber", "InvoiceDate", "InvoiceAmount", "RemainingAmount",
            )]
            self.rows = [(77, "50012", "2024-01-12", 820000, 430000)]
        def fetchall(self): return self.rows

    class Connection:
        def cursor(self): return Cursor()
        def rollback(self): pass
        def close(self): pass

    @contextmanager
    def fake_connection(_settings):
        yield Connection()

    monkeypatch.setattr("app.seller_workspace_service.sql_connection", fake_connection)
    result = seller_customer_open_invoices(settings, "A.kamran", "2610258")

    assert result["customer_id"] == 2610258
    assert result["invoice_count"] == 1
    assert result["invoices"] == [{
        "id": 77, "number": "50012", "date": "2024-01-12", "amount": 820000.0,
        "remaining_amount": 430000.0,
    }]
    assert len(calls) == 1
    assert "sale.CustId = 2610258" in calls[0]
    assert "sale.DealerId = 22" in calls[0]
    assert "GROUP BY sale.SaleId" in calls[0]
    assert "ORDER BY COALESCE(MIN(sale.SaleDate), MIN(sale.SaleVocherDate), MIN(sale.ReportDate)), sale.SaleId" in calls[0]


def test_customer_cheque_intelligence_uses_stable_status_history_and_settlement(settings, monkeypatch):
    calls = []

    def fake_rows(_settings, sql):
        calls.append(sql)
        if "PaidChequeCount12M" in sql:
            return [{
                "PaidChequeCount12M": 4, "PaidChequeAmount12M": 8_000_000,
                "ActiveReturnedCount": 1, "ActiveReturnedAmount": 2_000_000,
                "CollectedAfterReturnCount": 1, "CollectedAfterReturnAmount": 1_500_000,
                "RefundedAfterReturnCount": 2, "RefundedAfterReturnAmount": 3_000_000,
                "LegalReturnedCount": 0, "LegalReturnedAmount": 0,
                "FullySettledReturnedCount": 2, "ReturnedSettlementAmount": 4_500_000,
            }]
        return [{
            "RChequeId": 81, "RChequeNo": "7788", "RChequeDate": "1405/01/20",
            "RChequeAmount": 2_000_000, "BankName": "ملت", "RChequeBranchName": "مرکزی",
            "RChequeStatusId": 5, "RChequeStatusName": "استرداد", "LastStatusDate": "1405/05/20",
            "FirstReturnDate": "1405/04/10", "SettledAmount": 2_300_000,
            "LastSettlementDate": "1405/05/19",
        }]

    monkeypatch.setattr("app.seller_workspace_service._query_rows", fake_rows)
    result = _customer_cheque_intelligence(settings, "2610258")

    assert result["summary"]["paid_12m_amount"] == 8_000_000.0
    assert result["summary"]["active_returned_count"] == 1
    assert result["summary"]["refunded_after_return_count"] == 2
    assert result["summary"]["fully_settled_returned_count"] == 2
    assert result["cheques"][0]["lifecycle"] == "refunded_after_return"
    assert result["cheques"][0]["settled_amount"] == 2_000_000.0
    assert result["cheques"][0]["fully_settled"] is True
    assert "cheque.CustomerId = 2610258" in calls[0]
    assert "cheque.RChequeStatusId = 3" in calls[0]
    assert "history.RChequeStatusId = 4" in calls[0]
    assert "dbo.Settlement2" in calls[0]
    assert "cheque.RChequeStatusId IN (3, 4, 5, 9)" in calls[1]


def test_customer_visit_workspace_combines_authorized_customer_intelligence(settings, monkeypatch):
    profile = {
        "route": {"id": "route-1", "title": "مسیر امروز"},
        "customer": {
            "id": 2610258,
            "name": "مشتری نمونه",
            "store_name": "فروشگاه نمونه",
            "cardex_balance": 1_250_000,
            "financial_snapshot": {"remaining_bed_credit": 3_000_000},
        },
    }
    monkeypatch.setattr(
        "app.seller_workspace_service.seller_route_customer_profile",
        lambda *_args: profile,
    )
    monkeypatch.setattr(
        "app.seller_workspace_service.seller_route_day_analytics",
        lambda *_args: {
            "source": "validated analytics",
            "customers": [
                {"id": 100, "visit_score": 1},
                {
                    "id": 2610258,
                    "visit_score": 24,
                    "line_purchased_brands": [{"name": "میسویک", "invoice_count": 6}],
                },
            ],
        },
    )
    monkeypatch.setattr(
        "app.seller_workspace_service.seller_customer_open_invoices",
        lambda *_args: {
            "customer_id": 2610258,
            "invoice_count": 1,
            "invoices": [{"id": 77, "remaining_amount": 430_000}],
            "source": "validated invoices",
        },
    )
    monkeypatch.setattr(
        "app.seller_workspace_service._customer_cheque_intelligence",
        lambda *_args: {
            "summary": {"paid_12m_amount": 8_000_000},
            "cheques": [{"id": 81, "lifecycle": "refunded_after_return"}],
            "source": "validated cheque history",
        },
    )

    result = seller_customer_visit_workspace(settings, "A.kamran", "route-1", "2610258")

    assert result["customer"]["cardex_balance"] == 1_250_000
    assert result["analytics"]["visit_score"] == 24
    assert result["analytics"]["line_purchased_brands"][0]["name"] == "میسویک"
    assert result["open_invoices"]["invoice_count"] == 1
    assert result["cheques"]["summary"]["paid_12m_amount"] == 8_000_000
    assert result["read_only"] is True
    assert result["sources"] == {
        "profile": "NGT.Customers + current seller route assignment",
        "purchase_intelligence": "validated analytics",
        "open_invoices": "validated invoices",
        "cheques": "validated cheque history",
    }


def test_seller_distribution_in_progress_includes_today_and_tomorrows_scheduled_distribution(settings, monkeypatch):
    _seller(settings)
    calls = []

    class Cursor:
        def execute(self, sql):
            calls.append(sql)
            self.description = [(name,) for name in (
                "SaleId", "SaleNo", "SaleVocherNo", "SaleDate", "TotalAmount", "CustomerCode",
                "CustomerName", "StoreName", "DistNo", "DistDate", "SendDate", "DriverName", "DriverMobile",
            )]
        def fetchall(self):
            return [(81, None, "V-77", "1405/05/24", 830000, "2610258", "Ali", "Super Store", "4751", "1405/05/24", "2026-08-15 09:26:00", "Driver One", "09120000000")]

    class Connection:
        def cursor(self): return Cursor()
        def rollback(self): pass
        def close(self): pass

    @contextmanager
    def fake_connection(_settings):
        yield Connection()

    monkeypatch.setattr("app.seller_workspace_service.sql_connection", fake_connection)
    result = seller_distribution_in_progress(settings, "A.kamran")

    assert result["distribution_date"] == "1405/05/24"
    assert result["distribution_dates"] == ["1405/05/24"]
    assert result["invoice_count"] == 1
    assert result["invoices"] == [{
        "id": 81, "number": "V-77", "sale_date": "1405/05/24", "amount": 830000.0,
        "customer_code": "2610258", "customer_name": "Ali", "customer_store": "Super Store",
        "distribution_number": "4751", "distribution_date": "1405/05/24",
        "sent_at": "2026-08-15 09:26:00", "driver_name": "Driver One", "driver_mobile": "09120000000",
    }]
    assert "sale.DealerRef = 22" in calls[0]
    assert "FORMAT(GETDATE(), 'yyyy/MM/dd', 'fa-IR')" in calls[0]
    assert "FORMAT(DATEADD(DAY, 1, GETDATE()), 'yyyy/MM/dd', 'fa-IR')" in calls[0]
    assert "dist.SendDate IS NOT NULL" in calls[0]
    assert "OR dist.DistDate = FORMAT(DATEADD(DAY, 1, GETDATE()), 'yyyy/MM/dd', 'fa-IR')" in calls[0]
    assert "dist.ReturnDate IS NULL" in calls[0]
    assert "dbo.Contact AS driver" in calls[0]


def test_route_customer_profile_uses_ngt_edit_contract_and_local_draft(settings, monkeypatch):
    route_id = "11111111-1111-1111-1111-111111111111"
    route = {"route": {"id": route_id, "title": "مسیر امروز"}, "visit_location_policy": {"allow_edit_customer": True, "required_customer_fields": []}}
    route_customer = {
        "id": 2610258, "code": "2610258", "name": "مشتری نمونه", "store_name": "فروشگاه نمونه",
        "address": "کرج", "phone": "026", "mobile": "0912", "latitude": 35.8, "longitude": 50.9,
        "cardex_balance": 1000.0, "open_invoice_remaining": 2000.0, "open_invoice_count": 1,
        "financial_snapshot": {"remaining_bed_credit": 3000.0, "remaining_asn_credit": 4000.0},
    }
    monkeypatch.setattr(
        "app.seller_workspace_service._assigned_route_customer",
        lambda *_args: (route, route_customer),
    )
    lookups = {
        "activity": [{"id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", "title": "خرده فروش", "parent_id": "", "ref": 1}],
        "category": [], "level": [], "owner_type": [{"id": "7", "title": "مالک", "parent_id": "", "ref": 7}],
        "state": [], "city": [], "county": [],
    }
    monkeypatch.setattr("app.seller_workspace_service._customer_profile_lookups", lambda *_args: lookups)
    monkeypatch.setattr("app.seller_workspace_service._query_rows", lambda *_args: [{
        "CustomerUniqueId": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", "BackOfficeId": "2610258",
        "CustomerCode": "2610258", "CustomerName": "مشتری نمونه", "StoreName": "فروشگاه نمونه",
        "Address": "کرج", "Phone": "026", "Mobile": "0912", "NationalCode": "001",
        "EconomicCode": "E1", "PostCode": "31", "CityZone": 2, "Latitude": 35.8, "Longitude": 50.9,
        "Alarm": "", "CustomerActivityId": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "CustomerActivityName": "خرده فروش", "CustomerCategoryId": "", "CustomerCategoryName": "",
        "CustomerLevelId": "", "CustomerLevelName": "", "OwnerTypeRef": "7", "CustomerOwnerTypeName": "مالک",
        "StateId": "", "StateName": "", "CityId": "", "CityName": "", "CountyId": "", "CountyName": "",
        "VisitCount": 4, "OrderCount": 3, "OrderLineCount": 12, "SumOrderAmount": 5000,
        "AvgSuccessfulVisit": 0.75, "LastUpdate": "2026-08-23",
    }])

    profile = seller_route_customer_profile(settings, "A.kamran", route_id, "2610258")
    assert profile["customer"]["editable"]["customer_activity_id"] == "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    assert profile["customer"]["editable"]["owner_type_ref"] == 7
    assert profile["editable_contract"]["write_mode"] == "local_draft_only"
    assert "customer_code" in profile["editable_contract"]["fields"]
    assert "latitude" in profile["editable_contract"]["fields"]
    assert set(profile["editable_contract"]["active_fields"]) == set(profile["editable_contract"]["fields"])

    payload = dict(profile["customer"]["editable"])
    payload["store_name"] = "فروشگاه ویرایش شده"
    result = save_seller_route_customer_profile_draft(settings, "A.kamran", route_id, "2610258", payload)
    assert result["write_mode"] == "local_draft_only"
    assert result["draft"]["store_name"] == "فروشگاه ویرایش شده"
    with sqlite_connection(settings.sqlite_path) as connection:
        saved = connection.execute(
            "SELECT update_json FROM previsit_customer_update_drafts WHERE username = ? AND route_id = ? AND customer_id = ?",
            ("A.kamran", route_id, "2610258"),
        ).fetchone()
        saved_location = connection.execute(
            "SELECT latitude, longitude, source, updated_by FROM customer_geo_locations WHERE customer_id = ?",
            ("2610258",),
        ).fetchone()
    assert "فروشگاه ویرایش شده" in saved["update_json"]
    assert dict(saved_location) == {
        "latitude": 35.8, "longitude": 50.9,
        "source": "salesperson_pinned", "updated_by": "A.kamran",
    }


def test_customer_location_fields_are_editable_when_only_location_registration_is_allowed():
    assert _active_customer_update_fields({
        "allow_edit_customer": False,
        "set_customer_location": True,
        "required_customer_fields": [],
    }) == ["latitude", "longitude"]


def test_embedded_customer_profile_shows_all_fields_and_uses_a_map_picker():
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    assert "function openPrevisitLocationPicker" in script
    assert 'id="previsitLocationPickerDialog"' in script
    assert 'id="previsitLocationPickerMap"' in script
    assert "profile.editable_contract?.fields" in script
    assert "const editable = activeFields.has(name)" in script
    assert "is-readonly" in script
    assert "is-required" in script
    assert "data-previsit-location-confirm" in script
    assert "overflow:visible!important" in styles
    assert "z-index:10002!important" in styles


def test_customer_menu_stacking_context_stays_above_its_backdrop():
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    assert ".previsit-visit-rail{overflow:visible!important;z-index:10004!important}" in styles
    assert ".previsit-visit-menu-backdrop{z-index:10001!important}" in styles


def test_seller_workspace_requires_a_named_session(client):
    assert client.get("/seller-workspace/routes").status_code == 401
    assert client.get("/seller-workspace/brands").status_code == 401
    assert client.get("/seller-workspace/open-invoices").status_code == 401
    assert client.get("/seller-workspace/distribution-in-progress").status_code == 401
    assert client.get("/seller-workspace/open-invoices/2610258").status_code == 401
    assert client.get("/seller-workspace/routes/11111111-1111-1111-1111-111111111111/customers").status_code == 401
    assert client.get("/seller-workspace/routes/11111111-1111-1111-1111-111111111111/customers/2610258/profile").status_code == 401
    assert client.get("/seller-workspace/routes/11111111-1111-1111-1111-111111111111/customers/2610258/visit-workspace").status_code == 401
    assert client.get("/seller-workspace/previsit/policy?path_id=11111111-1111-1111-1111-111111111111&customer_id=2610258").status_code == 401


def test_assistant_ui_contains_seller_routes_and_brands(client):
    page = client.get("/assistant").text
    script = client.get("/static/assistant.js?v=55").text
    assert 'id="myRoutesBtn"' in page
    assert 'id="dayRouteBtn"' in page
    assert 'id="myBrandsBtn"' in page
    assert 'id="sellerRecommendationsBtn"' in page
    assert 'id="myOpenInvoicesBtn"' in page
    assert 'id="myDistributionInProgressBtn"' in page
    assert "/seller-workspace/routes" in script
    assert "/seller-workspace/brands" in script
    assert "/seller-workspace/open-invoices" in script
    assert "/seller-workspace/distribution-in-progress" in script
    assert "function openSellerRecommendations()" in script
    assert "sellerCoachingStart: true" in script
    assert "seller_coaching_start: sellerCoachingStart" in script
    assert "function coachingNextSteps()" in script
    assert "تحلیل عملکرد فروش من از ابتدای ماه تا امروز" in script
    assert "const targets =" in script
    assert "/customers`" in script
    assert "customer_count" in script
    assert "data-route-customers" in script
    assert "data-day-route-id" in script
    assert "route.can_start_day_route" in script
    assert "route.can_start_visit" in script
    assert "params.set('start_day_route', 'true')" in script
    assert "provisionalRouteMapPlan" in script
    assert "fetch(`/seller-workspace/routes/${encodeURIComponent(pathId)}/customers`)" in script
    assert "لیست مشتریان آماده است؛ اولویت و مسیر در حال تکمیل است" in script
    assert "ورود به تور ویزیت" in script
    assert 'id="routeMapDayCustomers"' in page
    assert 'id="customerProfilePanel"' in page
    assert 'id="routeMapLocationPolicy"' in page
    assert "data-route-map-previsit-customer" in script
    assert "openPrevisitForRouteCustomer" in script
    assert "openRouteCustomerProfile" in script
    assert "هنگام شروع ویزیت اعمال می‌شود" in script
    assert 'id="routeMapStartBtn"' in page
    assert ".setDOMContent(routeMapCustomerPopupContent(customer, pathId))" not in script
    assert "void openRouteCustomerProfile(pathId, customer.id, 'map')" in script
    assert "$('#routeMapCanvas').addEventListener('click'" not in script
    assert "اعتبار بدهکاری" in script
    assert "مانده اعتبار بدهکاری" in script
    assert "اعتبار اسنادی" in script
    assert "مانده اعتبار اسنادی" in script
    assert "اسناد/چک‌های باز" in script
    assert "void openPrevisitForRouteCustomer(pathId, customer.id);" not in script
    assert "get_my_day_route_analytics" in open("app/chat_service.py", encoding="utf-8").read()
    assert "function startDayRoutePlan" in script
    assert "day_route_mode: dayRouteMode" in script
    assert "day_route_id: dayRouteMode ? dayRouteId : null" in script
    assert "retry-answer" in script
    assert "cardex_balance" in script
    assert "open_invoice_remaining" in script
    assert "oldest_open_invoice_date" in script
    assert "مانده کاردکس مشتری" in script
    assert "چک برگشتی" in script
    assert "data-customer-open-invoices" in script
    assert "/seller-workspace/open-invoices/${encodeURIComponent(customerId)}" in script
    assert "/seller-workspace/previsit/policy?${query}" in script
    assert "currentCoordinates({maximumAge: 0, timeout: 12000})" in script
    assert "کنترل فاصله موقتاً غیرفعال" in script
    assert "const needsPosition = Boolean(policy?.controls?.enforced)" in script
    assert 'id="previsitOutcomeDialog"' in page
    assert 'id="completePrevisitNoVisit"' not in page
    assert "openRouteCustomerNoVisit" in script
    assert "data-route-customer-enter-visit" in script
    assert "data-route-customer-no-visit" in script
    assert "reason_id: reasonId" in script


def test_previsit_is_a_unified_professional_customer_workspace(client):
    page = client.get("/assistant").text
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    assert '/static/previsit-workspace.css?v=50' in page
    assert '/static/assistant.js?v=213' in page
    assert "NGT" not in page
    assert "NGT" not in script
    assert "NGT" not in open("app/static/assistant.css", encoding="utf-8").read()
    assert "NGT" not in open("app/static/planning.html", encoding="utf-8").read()
    assert 'data-previsit-section="order"' in script
    assert 'data-previsit-section="overview"' not in script
    assert 'data-previsit-section="invoices"' in script
    assert 'data-previsit-section="cardex"' in script
    assert 'data-previsit-section="returned-cheques"' in script
    assert 'data-previsit-section="history"' in script
    assert 'data-previsit-section="interests"' in script
    assert 'data-previsit-section="profile"' in script
    assert 'data-previsit-order-mode="list"' in script
    assert 'data-previsit-order-mode="grouped"' in script
    assert 'data-previsit-order-mode="quick"' not in script
    assert 'id="previsitQuickSearch"' in script
    assert "listView.id = 'previsitProductListView'" in script
    assert 'id="previsitListBrands"' in script
    assert 'id="previsitListGroups"' in script
    assert 'data-previsit-list-brand' in script
    assert 'data-previsit-list-group' in script
    assert 'id="previsitListProducts"' in script
    assert 'id="previsitFloatingVoice"' in script
    assert "function syncOrderCommandVoiceButtons" in script
    assert "function updatePrevisitListScrollChrome" in script
    assert "is-filter-rail-collapsed" in script
    assert ".previsit-floating-voice" in styles
    assert ".previsit-list-sticky-controls.is-filter-rail-collapsed" in styles
    assert "function renderPrevisitProductList()" in script
    assert "function renderPrevisitGroupedCatalogs()" in script
    assert "--previsit-group-strip-height" in script
    assert "visibleProductCount" in script
    assert "visibleProductCount * 160" in script
    assert "function renderPrevisitListFilters()" in script
    assert "function setPrevisitProductQuantity" in script
    assert "product.carton_size" in script
    assert "product.catalog_tax_inclusive_price" in script
    assert "product.manufacturer_price" in script
    assert "product.consumer_price" in script
    assert "/visit-workspace`" in script
    assert "loadPrevisitCustomerWorkspace(route_id, customer_id)" in script
    assert "async function completePrevisit(outcome, reasonId = null)" in script
    assert "function previsitBrandCards(brands = [])" in script
    assert "function previsitLinePurchaseCards(lines = [])" in script
    assert "function previsitReturnedChequeCards(cheques = [])" in script
    assert "خرید به تفکیک لاین" in script
    assert "آخرین بازاریاب" in script
    assert "href=\"tel:${esc(callable)}\"" in script
    assert 'class="previsit-customer-code">کد ${esc(customerCode)}' in script
    assert 'id="previsitContextStatus" class="previsit-status" hidden' in script
    assert '#previsitContextStatus{display:none!important}' in styles
    assert '.previsit-customer-summary>.previsit-customer-header-copy' in styles
    assert 'background:transparent!important' in styles
    header_renderer = script[script.index("function renderPrevisitCustomerHeader"):script.index("function setPrevisitReportGate")]
    assert "route?.title" not in header_renderer
    assert "seller?.full_name" not in header_renderer
    conditions = script[script.index('class="previsit-order-conditions previsit-order-conditions-inline"'):script.index('id="previsitCatalogView"')]
    assert conditions.index("نوع درخواست") < conditions.index("انبار") < conditions.index("شرایط پرداخت")
    assert "برندهای سایر لاین‌ها" in script
    assert "فاکتور باز این بازاریاب" in script
    assert "چک‌های وصولی ۱۲ ماه اخیر" in script
    assert "برگشتی سپس مستردشده" in script
    assert "برگشتی کاملاً تسویه‌شده" in script
    assert "history_status_4_then_current_status_5" in open("app/seller_workspace_service.py", encoding="utf-8").read()
    assert "previsit-visit-rail" in styles
    assert "grid-template-columns:minmax(0,1fr) 246px" in styles
    assert "@media(max-width:820px)" in styles
    assert "box-sizing:border-box;min-width:0;max-width:100%" in styles
    assert "grid-template-columns:repeat(2,minmax(0,1fr))" in styles
    assert ".previsit-returned-cheque-list" in styles
    assert ".previsit-seller-contact" in styles
    assert ".previsit-customer-name-row" in styles
    assert "grid-template-columns:repeat(3,minmax(0,1fr))!important" in styles
    assert "display:flex!important;grid-template-columns:none!important" in styles
    assert "grid-auto-rows:max-content" in styles
    assert "grid-template-rows:auto auto" in styles


def test_grouped_catalog_table_keeps_android_controls_safe_and_shows_all_prices():
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    assert "if (!isNeginAndroidApp && !document.fullscreenElement" in script
    assert 'class="previsit-grouped-prices"' in script
    assert "قیمت پایه با احتساب" in script
    assert "قیمت تولیدکننده" in script
    assert "قیمت مصرف‌کننده" in script
    assert ".previsit-grouped-prices" in styles
    assert "--previsit-android-bottom-clearance" in styles
    assert "scroll-padding-bottom" in styles
    assert "previsitOrderMode !== 'grouped'" in script
    assert "is-single-grouped-product" in script
    assert "isAndroid ? '56px' : '0px'" in script
    assert "const singleGroupedProduct = product.catalog_products.length === 1" in script
    assert "const minimumStripHeight = singleGroupedProduct ? 310 + systemClearance : 220" in script
    assert "html.web-road-theme .previsit-grouped-catalog-view .previsit-grouped-card" not in styles
    assert "html.web-road-theme .previsit-table-overlay.is-grouped-catalog .previsit-table-seller{background:#fff" in styles
    assert "html.web-road-theme .previsit-table-overlay.is-grouped-catalog .previsit-list-unit-row button{background:#176b54" in styles


def test_preinvoice_shows_carton_remainder_units_per_carton_and_final_base_quantity():
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    assert "function previsitInvoiceUnitBreakdown" in script
    assert "cartonQuantity" in script
    assert "remainderQuantity" in script
    assert "unitsPerCarton" in script
    assert "تعداد نهایی" in script
    assert "تعداد در کارتن" in script
    assert 'grid-area:carton' in styles
    assert 'grid-area:remainder' in styles
    assert 'grid-area:units-per-carton' in styles
    assert 'data-field="quantity" type="number"' in script
    assert 'readonly aria-readonly="true"' in script
    assert 'data-previsit-invoice-unit-input="carton"' in script
    assert 'data-previsit-invoice-unit-input="remainder"' in script
    assert 'data-previsit-invoice-unit-step' in script
    assert 'data-previsit-invoice-unit-step="carton"' in script
    assert '<svg viewBox="0 0 16 16"' in script
    assert '.previsit-invoice-unit-editor' in styles
    assert 'unit quantity units-per-carton remainder carton product' in styles


def test_visit_tour_has_work_menu_customer_actions_and_no_outcomes_inside_order_page(client):
    page = client.get("/assistant").text
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/assistant.css", encoding="utf-8").read()

    assert '<button id="dayRouteBtn"' in page
    assert "تورهای ویزیت" in page
    assert 'id="routeDayActionRail"' in page
    assert 'id="routeDayMenuToggle"' in page
    assert 'id="routeDayMenuBackdrop"' in page
    rail_start = page.index('id="routeDayActionRail"')
    rail_end = page.index('</nav>', rail_start)
    rail = page[rail_start:rail_end]
    assert 'data-route-day-action="customers"' in rail
    assert 'data-route-day-action="map"' in rail
    assert 'data-route-day-action="requests"' in rail
    assert 'data-route-day-action="catalog"' not in rail
    assert 'data-action-state="planned"' not in rail
    assert 'id="routeDaySavedRequests"' in page
    assert 'data-route-customer-enter-visit' in script
    assert 'data-route-customer-no-visit' in script
    assert "openRouteCustomerNoVisit" in script
    assert "/saved-requests`" in script
    assert 'id="completePrevisitNoOrder"' not in script
    assert 'id="completePrevisitNoVisit"' not in script
    assert ".route-day-saved-requests" in styles
    assert ".route-day-action-rail.is-open" in styles
    assert "function toggleRouteDayMenu" in script
    assert "const customerListOnly = routeMapPanel.dataset.routeDayView === 'customers'" in script
    assert "const action = !customerListOnly && index === session.activeIndex" in script
    assert '[data-route-day-view="customers"] #routeMapLocationPolicy' in styles
    assert "function routeCustomerListIdentity(customer)" in script
    assert "customerListOnly ? routeCustomerListIdentity(customer)" in script
    identity_start = script.index("function routeCustomerListIdentity(customer)")
    identity_end = script.index("function hasRouteMapDebt", identity_start)
    identity = script[identity_start:identity_end]
    assert "customer.store_name" in identity
    assert "customer.name" in identity
    assert "customer.address" in identity
    assert "visit_score" not in identity
    assert "cardex_balance" not in identity
    assert "async function startPrevisitVisit({deferReveal = false} = {})" in script
    assert "await startPrevisitVisit({deferReveal: true});" in script
    enter_start = script.index("async function enterRouteCustomerVisit")
    enter_end = script.index("async function openRouteCustomerNoVisit", enter_start)
    assert "$('#startPrevisit').click()" not in script[enter_start:enter_end]
    assert "deferReveal: true" in script[enter_start:enter_end]
    assert "function revealActivePrevisit" in script
    assert "if (!deferReveal) rememberAppView('previsit'" in script
    assert "previsitPanel.hidden = deferReveal" in script
    assert ".route-customer-address{margin-top:2px;color:#707975;font-size:10px" in styles


def test_visit_tour_customer_list_does_not_read_gps_position_before_initialization(client):
    script = client.get("/static/assistant.js?v=213").text

    assert "plan: provisionalPlan, routeMode: 'sales_priority', position: null" in script
    assert "plan: provisionalPlan, routeMode: 'sales_priority', position," not in script


def test_previsit_order_workspace_keeps_conditions_and_product_filters_directly_editable():
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    assert 'id="previsitVisitMenuToggle"' in script
    assert 'id="previsitVisitMenuBackdrop"' in script
    assert "function togglePrevisitVisitMenu" in script
    assert 'class="previsit-order-control-bar"' not in script
    assert 'data-previsit-order-panel="conditions"' not in script
    assert 'data-previsit-order-panel="assistant"' not in script
    assert 'id="previsitFloatingVoice" class="previsit-floating-voice" type="button" hidden' in script
    assert 'لیست کالا و صوت' not in script
    assert 'class="previsit-order-conditions previsit-order-conditions-inline"' in script
    assert "function togglePrevisitOrderPanel" in script
    assert 'id="previsitCatalogFilterToggle"' in script
    assert 'id="previsitListBrands"' in script
    assert 'id="previsitListGroups"' in script
    assert 'id="previsitListFilterToggle"' not in script
    assert "function togglePrevisitCatalogFilters" in script
    assert ".previsit-visit-rail-panel" in styles
    assert "transform:translateX(110%)" in styles
    assert ".previsit-visit-rail.is-open .previsit-visit-rail-panel" in styles
    assert ".previsit-visit-rail.is-open{z-index:103}" in styles
    assert "z-index:101;display:block" in styles
    assert ".previsit-catalog-quickbar" in styles
    assert ".previsit-list-sticky-controls" in styles
    assert "top:var(--previsit-list-sticky-top" in styles
    assert ".previsit-grouped-toolbar{position:sticky" in styles
    sticky_start = script.index("function updatePrevisitOrderStickyTop")
    sticky_end = script.index("function togglePrevisitVisitMenu", sticky_start)
    sticky_logic = script[sticky_start:sticky_end]
    assert "const listStickyTop = stickyTop + 2" in sticky_logic
    assert "orderCommon?.getBoundingClientRect().height" not in sticky_logic
    assert ".previsit-order-common{position:relative;top:auto" in styles
    assert ".previsit-list-sticky-controls{padding:5px;gap:4px" in styles
    assert ".previsit-list-product-copy>strong{font-size:13px" in styles
    assert ".previsit-product-info strong{font-size:12px" in styles


def test_customer_drawer_uses_compact_dark_gold_surface_on_web_and_android():
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    assert "html.web-road-theme .previsit-visit-rail-panel{" in styles
    assert "background:linear-gradient(180deg,#1c1d19,#11120f)" in styles
    assert "html.web-road-theme .previsit-visit-drawer-head button{" in styles
    assert "html.web-road-theme .previsit-visit-menu-backdrop{" in styles
    assert "grid-auto-rows:max-content!important" in styles
    assert "align-content:start!important" in styles
    assert ".previsit-product-list-view.is-compact .previsit-list-product-copy>strong{font-size:13px" in styles
    assert ".previsit-product-list-view.is-compact .previsit-list-product-copy>div b{padding:4px 6px;font-size:9px" in styles
    assert ".previsit-product-list-view.is-compact .previsit-list-prices b{font-size:10px" in styles
    assert ".previsit-product-list-view.is-compact .previsit-list-prices b{font-size:12px" in styles
    assert ".previsit-grouped-catalog-view .previsit-grouped-product>header strong{font-size:13px" in styles
    assert ".previsit-grouped-catalog-view .previsit-grouped-prices b{font-size:11px" in styles


def test_customer_profile_can_capture_current_location_without_auto_sending():
    script = open("app/static/assistant.js", encoding="utf-8").read()

    assert 'id="captureCustomerLocation"' in script
    assert "async function captureCustomerProfileLocation()" in script
    assert "const position = await currentCoordinates({maximumAge: 0, timeout: 12000});" in script
    assert "latitudeInput.value = position.latitude.toFixed(7);" in script
    assert "longitudeInput.value = position.longitude.toFixed(7);" in script
    assert "برای نگهداری این موقعیت، پیش‌نویس تغییرات را ذخیره کنید" in script
    assert "void captureCustomerProfileLocation();" in script


def test_direct_visit_opens_customer_information_and_locks_other_sections_until_requirements_are_done():
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/assistant.css", encoding="utf-8").read()

    assert "enterVisit.classList.add('is-loading')" in script
    assert "enterVisit.setAttribute('aria-busy', 'true')" in script
    assert ".route-tour-customer-actions>button.is-loading::before" in styles
    assert "let previsitVisitSection = 'profile';" in script
    assert 'data-previsit-section="profile" class="is-active"' in script
    assert "function applyPrevisitRequirementGate" in script
    assert "item.dataset.previsitSection === 'order'" in script
    assert "function renderEmbeddedPrevisitCustomerProfile" in script
    assert "data-previsit-profile-field" in script
    assert "async function saveEmbeddedPrevisitCustomerProfile" in script
    assert "section: 'profile'" in script


def test_visit_request_save_recalculates_and_customer_menu_is_compact_and_outcome_aware():
    script = open("app/static/assistant.js", encoding="utf-8").read()
    styles = open("app/static/previsit-workspace.css", encoding="utf-8").read()

    save_start = script.index("async function savePrevisitRequest()")
    save_end = script.index("function updatePrevisitSaveRequestButton", save_start)
    save_logic = script[save_start:save_end]
    assert "const validation = await previewNgtPrevisit();" in save_logic
    assert "if (!validation.ok)" in save_logic
    assert "previsitSavedRequestPayload()" in save_logic
    assert save_logic.index("await previewNgtPrevisit()") < save_logic.index("previsitSavedRequestPayload()")
    assert 'aria-label="باز کردن منوی مشتری"' in script
    assert 'data-previsit-outcome="no_order"' in script
    assert "openPrevisitOutcome('no_order')" in script
    assert "item.dataset.previsitSection === 'order'" in script
    assert "function startPrevisitVisitTimer" in script
    assert "Boolean(policy?.controls?.enforced)" in script
    assert ".previsit-visit-menu-toggle{position:fixed" in styles
    assert "width:42px;height:42px" in styles
