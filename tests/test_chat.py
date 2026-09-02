def test_assistant_page_is_public_and_does_not_expose_secrets(client):
    response = client.get("/assistant")
    assert response.status_code == 200
    assert "OPENAI_API_KEY" not in response.text
    assert client.get("/static/manifest.webmanifest").status_code == 200


def test_chat_requires_internal_key(client):
    response = client.post("/chat", json={"message": "سلام"})
    assert response.status_code == 401


def test_local_chat_dependency_allows_loopback(settings):
    from unittest.mock import Mock
    from app.routes.dependencies import require_local_or_api_key

    request = Mock()
    request.client.host = "127.0.0.1"
    request.app.state.settings = settings
    assert require_local_or_api_key(request, None) is None


def test_valid_bearer_identity_takes_priority_over_local_bypass(settings, monkeypatch):
    from unittest.mock import Mock

    from app.routes.dependencies import require_user_or_local

    request = Mock()
    request.client.host = "127.0.0.1"
    request.app.state.settings = settings
    monkeypatch.setattr(
        "app.routes.dependencies.verify_access_token",
        lambda _settings, token: "Admin" if token == "valid-token" else None,
    )

    require_user_or_local(request, authorization="Bearer valid-token")

    assert request.state.username == "Admin"


def test_chat_returns_structured_result(client, auth, monkeypatch):
    captured = {}

    def fake_chat(settings, message, conversation_id, username):
        captured["username"] = username
        return {
            "conversation_id": conversation_id or "conversation-test",
            "answer": "نتیجه آزمایشی",
            "columns": ["مقدار"],
            "rows": [[1]],
            "row_count": 1,
            "execution_time": 0.01,
            "truncated": False,
            "sources": ["dbo.Test"],
            "sql": "SELECT 1 AS TestValue",
            "clarification_required": False,
        }

    monkeypatch.setattr("app.routes.chat.chat", fake_chat)
    response = client.post("/chat", json={"message": "تست"}, headers=auth)
    assert response.status_code == 200
    body = response.json()
    assert body["row_count"] == 1
    assert body["sql"].startswith("SELECT")
    assert body["sources"] == ["dbo.Test"]
    assert captured["username"] == "action-api-key"


def test_chat_response_preserves_detail_presentation_hints(client, auth, monkeypatch):
    def fake_chat(*_args, **_kwargs):
        return {
            "conversation_id": "detail-test",
            "answer": "ریز گزارش",
            "columns": ["تاریخ"],
            "rows": [["1405/01/01"]],
            "row_count": 1,
            "total_available_rows": 572,
            "presentation": {
                "mode": "detailed_rows",
                "expand_result": True,
                "visible_row_limit": 572,
            },
        }

    monkeypatch.setattr("app.routes.chat.chat", fake_chat)
    body = client.post("/chat", json={"message": "خط به خط"}, headers=auth).json()

    assert body["presentation"]["expand_result"] is True
    assert body["presentation"]["visible_row_limit"] == 572
    assert body["total_available_rows"] == 572


def test_chat_failure_is_recorded_in_internal_diagnostics(client, auth, settings, monkeypatch):
    from app.database import sqlite_connection

    def fail_chat(*_args, **_kwargs):
        raise RuntimeError("agent stopped before producing a report")

    monkeypatch.setattr("app.routes.chat.chat", fail_chat)
    response = client.post(
        "/chat",
        json={"message": "گزارش", "conversation_id": "failed-chat"},
        headers=auth,
    )
    assert response.status_code == 502
    with sqlite_connection(settings.sqlite_path) as conn:
        failure = conn.execute(
            "SELECT * FROM chat_failures ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert failure["conversation_id"] == "failed-chat"
    assert failure["error_type"] == "RuntimeError"
    assert failure["error_message"] == "agent stopped before producing a report"


def test_assistant_schema_catalog_lists_tables_and_safe_object_details(client, auth, settings):
    import json
    from app.database import sqlite_connection

    item = {
        "schema": "dbo", "name": "SalesReviewFast", "type": "VIEW",
        "columns": [{"name": "NetSales", "data_type": "decimal", "primary_key": False}],
        "catalog": {"persian_name": "گزارش فروش", "domain": "فروش و مشتری", "aliases": ["فروش"]},
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO schema_objects
               (schema_name, object_name, object_type, details_json, scanned_at)
               VALUES ('dbo', 'SalesReviewFast', 'VIEW', ?, '2026-08-11T00:00:00')""",
            (json.dumps(item, ensure_ascii=False),),
        )

    catalog = client.get("/chat/schema-catalog", headers=auth)
    assert catalog.status_code == 200
    assert catalog.json()["items"][0]["catalog"]["domain"] == "فروش و مشتری"
    detail = client.get("/chat/schema-catalog/object?schema=dbo&name=SalesReviewFast", headers=auth)
    assert detail.status_code == 200
    assert detail.json()["columns"][0]["name"] == "NetSales"


def test_latest_chat_response_can_be_recovered(client, auth, settings):
    import json
    from app.database import sqlite_connection

    payload = {"conversation_id": "recover-me", "answer": "پاسخ ذخیره‌شده", "row_count": 0}
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO chat_messages
               (conversation_id, role, content, sources_json, response_json, created_at)
               VALUES (?, 'assistant', ?, '[]', ?, '2026-08-04T00:00:00')""",
            ("recover-me", payload["answer"], json.dumps(payload, ensure_ascii=False)),
        )
    response = client.get("/chat/latest/recover-me", headers=auth)
    assert response.status_code == 200
    assert response.json()["answer"] == "پاسخ ذخیره‌شده"
