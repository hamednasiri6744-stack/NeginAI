from dataclasses import replace


def test_seller_model_profile_uses_the_fast_configuration(settings):
    from app.access_control import DataAccessPolicy
    from app.chat_service import _max_turns_for_policy, _model_profile

    tuned = replace(
        settings,
        seller_openai_model="gpt-5.6-terra",
        seller_openai_reasoning_effort="low",
        seller_openai_max_turns=6,
    )
    seller = DataAccessPolicy(username="seller", is_restricted_seller=True)

    assert _model_profile(tuned, seller) == ("gpt-5.6-terra", "low")
    assert _model_profile(tuned, DataAccessPolicy(username="manager")) == (
        tuned.openai_model,
        tuned.openai_reasoning_effort,
    )
    assert _max_turns_for_policy(tuned, seller) == 6
    assert _max_turns_for_policy(tuned, DataAccessPolicy(username="manager")) == 14
    assert _max_turns_for_policy(
        tuned, DataAccessPolicy(username="Admin", is_admin=True)
    ) == 40


def test_model_router_selects_luna_terra_and_sol_by_workload(settings):
    from app.access_control import DataAccessPolicy
    from app.chat_service import _model_profile, _recovery_model_profile

    admin = DataAccessPolicy(username="Admin", is_admin=True)
    seller = DataAccessPolicy(username="seller", is_restricted_seller=True)

    assert _model_profile(settings, admin, "سلام") == (
        "gpt-5.6-luna",
        "low",
    )
    assert _model_profile(settings, admin, "فروش امروز چقدر بوده؟") == (
        "gpt-5.6-terra",
        "medium",
    )
    assert _model_profile(
        settings,
        admin,
        "فروش و برگشت و سود همه شعب را کامل تحلیل و مقایسه کن",
    ) == ("gpt-5.6-sol", "high")
    assert _model_profile(
        settings,
        seller,
        "برنامه مسیر امروز من را بده",
        day_route_mode=True,
    ) == ("gpt-5.6-sol", "high")
    assert _recovery_model_profile(settings, "gpt-5.6-luna") == (
        "gpt-5.6-terra",
        "medium",
    )
    assert _recovery_model_profile(settings, "gpt-5.6-terra") == (
        "gpt-5.6-sol",
        "high",
    )


def test_disabled_model_router_preserves_legacy_role_profiles(settings):
    from app.access_control import DataAccessPolicy
    from app.chat_service import _model_profile

    tuned = replace(settings, model_router_enabled=False)
    seller = DataAccessPolicy(username="seller", is_restricted_seller=True)

    assert _model_profile(tuned, seller, "سلام") == (
        tuned.seller_openai_model,
        tuned.seller_openai_reasoning_effort,
    )
    assert _model_profile(tuned, DataAccessPolicy(username="manager"), "سلام") == (
        tuned.openai_model,
        tuned.openai_reasoning_effort,
    )


def test_history_uses_configured_limit(settings):
    from app.chat_service import _history
    from app.database import sqlite_connection

    limited = replace(settings, openai_history_limit=3)
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.executemany(
            """INSERT INTO chat_messages
               (conversation_id, role, content, sources_json, created_at)
               VALUES ('bounded-history', 'user', ?, '[]', ?)""",
            [(f"message-{index}", f"2026-08-08T00:00:{index:02d}") for index in range(8)],
        )

    assert [item["content"] for item in _history(limited, "bounded-history")] == [
        "message-5",
        "message-6",
        "message-7",
    ]


def test_chat_uses_configured_max_turns(settings, monkeypatch):
    from app.chat_service import AgentReply, chat

    captured = {}

    class FakeResult:
        final_output = AgentReply(answer="ok")

    def fake_run_sync(*args, **kwargs):
        captured["max_turns"] = kwargs["max_turns"]
        return FakeResult()

    monkeypatch.setattr("app.chat_service.Runner.run_sync", fake_run_sync)
    tuned = replace(settings, openai_api_key="test-key", openai_max_turns=7)

    response = chat(tuned, "hello", "bounded-turns")

    assert response["answer"] == "ok"
    assert captured["max_turns"] == 7


def test_health_exposes_non_secret_performance_settings(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["openai_reasoning_effort"] == "high"
    assert response.json()["model_router_enabled"] is True
    assert response.json()["router_fast_model"] == "gpt-5.6-luna"
    assert response.json()["router_standard_model"] == "gpt-5.6-terra"
    assert response.json()["openai_max_turns"] == 14
    assert response.json()["admin_openai_max_turns"] == 40
    assert response.json()["admin_openai_history_limit"] == 40
    assert response.json()["automation_configured"] is False
    assert response.json()["automation_enabled"] is True


def test_chat_returns_successful_sql_result_when_max_turns_is_reached(settings, monkeypatch):
    from agents import MaxTurnsExceeded
    from app.chat_service import chat

    def fake_run_sync(*args, **kwargs):
        context = kwargs["context"]
        context.last_result = {
            "columns": ["SalesManName", "NetSales"],
            "rows": [["بازاریاب نمونه", 1234567]],
            "row_count": 1,
            "execution_time": 0.01,
            "truncated": False,
            "sources": ["dbo.SalesReviewFast"],
            "sql": "SELECT 1",
        }
        raise MaxTurnsExceeded("test limit")

    monkeypatch.setattr("app.chat_service.Runner.run_sync", fake_run_sync)
    tuned = replace(settings, openai_api_key="test-key")

    response = chat(tuned, "گزارش آزمایشی", "fallback-result")

    assert response["clarification_required"] is False
    assert "بازاریاب نمونه" in response["answer"]
    assert "1,234,567" in response["answer"]
    assert response["row_count"] == 1
