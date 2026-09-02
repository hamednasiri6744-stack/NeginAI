def test_health_does_not_require_auth(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["varanegar_order_bridge_enabled"] is False
    assert response.json()["varanegar_order_commit_enabled"] is False
    assert response.json()["varanegar_order_numbering_verified"] is False
    assert response.json()["varanegar_order_registration_ready"] is False


def test_privacy_policy_is_public(client):
    response = client.get("/privacy")

    assert response.status_code == 200
    assert "سیاست حریم خصوصی" in response.text


def test_frontend_is_served_without_exposing_secrets(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "هوش مصنوعی نگین پخش" in response.text
    assert "NEGIN_ACTION_API_KEY=" not in response.text
    assert client.get("/static/app.js").status_code == 200


def test_mobile_app_assets_and_root_service_worker_are_public(client):
    assistant = client.get("/assistant")
    assert assistant.status_code == 200
    assert assistant.headers["cache-control"] == "no-store, must-revalidate"
    assert 'rel="manifest"' in assistant.text
    assert 'rel="apple-touch-icon"' in assistant.text

    manifest = client.get("/static/manifest.webmanifest")
    assert manifest.status_code == 200
    assert manifest.json()["display"] == "standalone"
    assert manifest.json()["scope"] == "/"

    worker = client.get("/service-worker.js")
    assert worker.status_code == 200
    assert worker.headers["cache-control"] == "no-cache"
    assert client.get("/static/neginai-icon-192.png").status_code == 200
    assert client.get("/static/neginai-icon-512.png").status_code == 200


def test_protected_endpoint_requires_key(client):
    assert client.get("/definitions").status_code == 401
    assert client.get("/definitions", headers={"X-API-Key": "wrong"}).status_code == 401


def test_definition_crud_and_search(client, auth):
    payload = {
        "term": "فروش خالص", "definition": "فروش پس از کسورات", "rules": "برگشتی کم شود",
        "approved_sql": "SELECT SUM(Amount) FROM sales.Invoices", "related_objects": ["sales.Invoices.Amount"],
    }
    created = client.post("/definitions", json=payload, headers=auth)
    assert created.status_code == 201
    definition_id = created.json()["id"]

    found = client.get("/definitions/search", params={"q": "فروش"}, headers=auth)
    assert found.status_code == 200
    assert found.json()[0]["term"] == "فروش خالص"

    sentence_match = client.get("/definitions/search", params={"q": "فروش امروز چقدر است"}, headers=auth)
    assert sentence_match.status_code == 200
    assert sentence_match.json()[0]["term"] == "فروش خالص"

    payload["definition"] = "تعریف اصلاح‌شده"
    updated = client.put(f"/definitions/{definition_id}", json=payload, headers=auth)
    assert updated.status_code == 200
    assert updated.json()["definition"] == "تعریف اصلاح‌شده"

    assert client.delete(f"/definitions/{definition_id}", headers=auth).status_code == 204
    assert client.delete(f"/definitions/{definition_id}", headers=auth).status_code == 404


def test_unsafe_approved_sql_is_rejected(client, auth):
    payload = {"term": "bad", "definition": "bad", "approved_sql": "DELETE FROM dbo.Users"}
    response = client.post("/definitions", json=payload, headers=auth)
    assert response.status_code == 400


def test_unsafe_query_is_rejected_and_audited(client, auth, settings):
    response = client.post("/sql/query", json={"sql": "DROP TABLE dbo.Users"}, headers=auth)
    assert response.status_code == 400

    import sqlite3
    with sqlite3.connect(settings.sqlite_path) as conn:
        row = conn.execute("SELECT succeeded, error_text FROM query_audit ORDER BY id DESC LIMIT 1").fetchone()
    assert row[0] == 0
    assert "allowed" in row[1] or "forbidden" in row[1]


def test_dashboard_stats_and_history_are_protected(client, auth):
    assert client.get("/dashboard/stats").status_code == 401
    stats = client.get("/dashboard/stats", headers=auth)
    assert stats.status_code == 200
    assert stats.json()["schema_objects"] == 0

    history = client.get("/history", headers=auth)
    assert history.status_code == 200
    assert set(history.json()) == {"total", "items"}
