from app.auth_service import create_session, create_user
from app.database import sqlite_connection


def _cookie(settings, username: str) -> dict[str, str]:
    create_user(settings, username, "test-password")
    return {"negin_session": create_session(settings, username)}


def test_conversations_are_recent_pinnable_and_user_scoped(client, settings):
    admin = _cookie(settings, "Admin")
    other = _cookie(settings, "m.etemadi")

    created = client.post(
        "/chat/conversations",
        json={"conversation_id": "admin-conversation"},
        cookies=admin,
    )
    assert created.status_code == 200
    assert created.json()["title"] == "گفت‌وگوی جدید"

    updated = client.patch(
        "/chat/conversations/admin-conversation",
        json={"title": "گزارش فروش امروز", "pinned": True},
        cookies=admin,
    )
    assert updated.status_code == 200
    assert updated.json()["pinned"] is True

    listed = client.get("/chat/conversations", cookies=admin).json()["conversations"]
    assert listed[0]["id"] == "admin-conversation"
    assert listed[0]["title"] == "گزارش فروش امروز"
    assert client.get("/chat/conversations", cookies=other).json()["conversations"] == []
    assert client.get(
        "/chat/conversations/admin-conversation/messages", cookies=other
    ).status_code == 404


def test_conversation_history_returns_saved_chat_response(client, settings):
    cookies = _cookie(settings, "Admin")
    client.post(
        "/chat/conversations",
        json={"conversation_id": "history-test"},
        cookies=cookies,
    )
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO chat_messages
               (conversation_id, role, content, sources_json, response_json, created_at)
               VALUES (?, 'user', ?, '[]', NULL, ?)""",
            ("history-test", "فروش امروز", "2026-08-09T10:00:00"),
        )
        conn.execute(
            """INSERT INTO chat_messages
               (conversation_id, role, content, sources_json, response_json, created_at)
               VALUES (?, 'assistant', ?, '[]', ?, ?)""",
            (
                "history-test",
                "پاسخ گزارش",
                '{"conversation_id":"history-test","answer":"پاسخ گزارش","row_count":0}',
                "2026-08-09T10:00:01",
            ),
        )

    response = client.get(
        "/chat/conversations/history-test/messages",
        cookies=cookies,
    )
    assert response.status_code == 200
    assert [item["role"] for item in response.json()["messages"]] == ["user", "assistant"]
    assert response.json()["messages"][1]["response"]["answer"] == "پاسخ گزارش"


def test_assistant_shell_has_chatgpt_style_conversation_controls(client):
    html = client.get("/assistant").text
    script = client.get("/static/assistant.js?v=31").text

    assert 'id="sidebar"' in html
    assert 'id="pinnedList"' in html
    assert 'id="recentList"' in html
    assert 'id="voiceBtn"' in html
    assert 'id="recordingBar"' in html
    assert "/chat/conversations" in script
    assert "data-pin-conversation" in script
    assert "/audio/transcriptions" in script
