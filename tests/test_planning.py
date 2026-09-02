from __future__ import annotations

from pathlib import Path

import pytest

from app.auth_service import create_session, create_user
from app.database import sqlite_connection
from app.planning_service import (
    PlanningError,
    compare_scenarios,
    create_scenario,
    get_scenario,
    list_scenarios,
    list_values,
    transition_scenario,
    upsert_values,
)


def _scenario(settings, code: str, name: str = "بودجه فروش"):
    return create_scenario(
        settings,
        "Admin",
        code=code,
        name=name,
        scenario_type="budget",
        fiscal_year=1405,
        start_period="1405-01",
        end_period="1405-12",
        assumptions={"price_growth_percent": 12},
    )


def _value(period: str, amount: float, brand: str = "Misswake"):
    return {
        "period": period,
        "metric": "sales_amount",
        "amount": amount,
        "unit": "rial",
        "branch": "البرز",
        "sales_line": "مارکت",
        "brand": brand,
    }


def test_scenario_is_versioned_separately_from_erp(settings):
    created = _scenario(settings, "BUD-1405")

    assert created["status"] == "draft"
    assert created["assumptions"] == {"price_growth_percent": 12}
    assert [item["code"] for item in list_scenarios(settings)] == ["BUD-1405"]
    detail = get_scenario(settings, created["id"])
    assert detail["audit"][0]["action"] == "scenario_created"


def test_duplicate_code_and_invalid_period_are_rejected(settings):
    _scenario(settings, "BUD-1405")
    with pytest.raises(PlanningError, match="قبلاً"):
        _scenario(settings, "bud-1405")

    with pytest.raises(PlanningError, match="سال دوره"):
        create_scenario(
            settings,
            "Admin",
            code="BAD-PERIOD",
            name="سناریوی نامعتبر",
            scenario_type="budget",
            fiscal_year=1405,
            start_period="1404-01",
            end_period="1405-12",
        )


def test_values_upsert_instead_of_duplicating_and_are_audited(settings):
    scenario = _scenario(settings, "BUD-VALUES")

    assert upsert_values(
        settings, scenario["id"], "Admin", [_value("1405-01", 100)]
    )["upserted"] == 1
    upsert_values(
        settings, scenario["id"], "Admin", [_value("1405-01", 125)]
    )

    values = list_values(settings, scenario["id"])
    assert values["total"] == 1
    assert values["items"][0]["amount"] == 125
    detail = get_scenario(settings, scenario["id"])
    assert detail["totals"][0]["total"] == 125
    assert detail["audit"][0]["details"] == {"count": 1}


def test_submitted_and_locked_scenarios_cannot_be_edited(settings):
    scenario = _scenario(settings, "BUD-WORKFLOW")
    upsert_values(settings, scenario["id"], "Admin", [_value("1405-01", 100)])

    submitted = transition_scenario(
        settings, scenario["id"], "Admin", "submit", "برای تأیید"
    )
    assert submitted["status"] == "submitted"
    with pytest.raises(PlanningError, match="پیش‌نویس"):
        upsert_values(
            settings, scenario["id"], "Admin", [_value("1405-02", 200)]
        )

    approved = transition_scenario(settings, scenario["id"], "finance", "approve")
    locked = transition_scenario(settings, scenario["id"], "finance", "lock")
    assert approved["approved_by"] == "finance"
    assert locked["status"] == "locked"
    assert locked["locked_at"]


def test_comparison_returns_period_variance_and_percent(settings):
    budget = _scenario(settings, "BUD-COMPARE")
    forecast = create_scenario(
        settings,
        "Admin",
        code="FC-1405",
        name="پیش‌بینی فروش",
        scenario_type="forecast",
        fiscal_year=1405,
        start_period="1405-01",
        end_period="1405-12",
        base_scenario_id=budget["id"],
    )
    upsert_values(settings, budget["id"], "Admin", [_value("1405-01", 120)])
    upsert_values(settings, forecast["id"], "Admin", [_value("1405-01", 100)])

    comparison = compare_scenarios(
        settings, forecast["id"], budget["id"], "sales_amount"
    )

    assert comparison["periods"] == [
        {
            "period": "1405-01",
            "left": 100.0,
            "right": 120.0,
            "variance": -20.0,
            "variance_percent": -16.67,
        }
    ]


def test_planning_api_exposes_metadata_scenarios_values_and_comparison(client, auth):
    metadata = client.get("/planning/metadata", headers=auth)
    created = client.post(
        "/planning/scenarios",
        headers=auth,
        json={
            "code": "API-BUD-1405",
            "name": "بودجه API",
            "scenario_type": "budget",
            "fiscal_year": 1405,
            "start_period": "1405-01",
            "end_period": "1405-12",
            "assumptions": {},
        },
    )

    assert metadata.status_code == 200
    assert any(item["code"] == "sales_amount" for item in metadata.json()["metrics"])
    assert created.status_code == 201
    scenario_id = created.json()["id"]

    saved = client.put(
        f"/planning/scenarios/{scenario_id}/values",
        headers=auth,
        json={"values": [_value("1405-01", 500)]},
    )
    listed = client.get("/planning/scenarios", headers=auth)
    compared = client.get(
        "/planning/compare",
        headers=auth,
        params={
            "left_id": scenario_id,
            "right_id": scenario_id,
            "metric": "sales_amount",
        },
    )

    assert saved.status_code == 200
    assert listed.json()["scenarios"][0]["value_count"] == 1
    assert compared.json()["periods"][0]["variance"] == 0


def test_planning_page_and_static_assets_are_available(client):
    page = client.get("/planning")
    script = client.get("/static/planning.js?v=1")
    stylesheet = client.get("/static/planning.css?v=1")

    assert page.status_code == 200
    assert "Negin Planning" in page.text
    assert 'id="scenarioList"' in page.text
    assert script.status_code == 200
    assert "DOMContentLoaded" in script.text
    assert stylesheet.status_code == 200


def test_non_admin_session_cannot_use_planning_api(client, settings):
    create_user(settings, "seller.user", "StrongPass9")
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            "UPDATE users SET role=? WHERE username=?",
            ("فروشنده", "seller.user"),
        )
    token = create_session(settings, "seller.user")

    denied = client.get(
        "/planning/metadata",
        headers={"Cookie": f"negin_session={token}"},
    )

    assert denied.status_code == 403
    assert "فقط برای مدیران" in denied.json()["detail"]


def test_assistant_exposes_planning_only_through_admin_navigation():
    assistant = Path("app/static/assistant.html").read_text(encoding="utf-8")
    assistant_js = Path("app/static/assistant.js").read_text(encoding="utf-8")
    service_worker = Path("app/static/service-worker.js").read_text(encoding="utf-8")

    assert 'id="planningBtn"' in assistant
    assert "/static/assistant.js?v=213" in assistant
    assert "permissions.includes('planning.manage')" in assistant_js
    assert "window.location.href = '/planning'" in assistant_js
    assert r"\u0645\u062f\u06cc\u0631 \u0633\u06cc\u0633\u062a\u0645" in assistant_js
    assert r"\u0645\u062f\u06cc\u0631 \u0633\u0627\u0645\u0627\u0646\u0647" in assistant_js
    assert "neginai-shell-v214" in service_worker
    assert "'/planning'" in service_worker
