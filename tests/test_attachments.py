from dataclasses import replace


def test_attachment_analysis_requires_authentication(client):
    response = client.post(
        "/attachments/analyze",
        files={"file": ("invoice.jpg", b"image", "image/jpeg")},
        data={"question": "این چیست؟"},
    )
    assert response.status_code == 401


def test_image_attachment_is_analyzed_with_user_question(client, auth, settings, monkeypatch):
    client.app.state.settings = replace(settings, openai_api_key="test-key")
    captured = {}

    def fake_analyze(api_key, model, filename, media_type, content, question):
        captured.update(
            api_key=api_key,
            model=model,
            filename=filename,
            media_type=media_type,
            content=content,
            question=question,
        )
        return "تصویر یک فاکتور با شماره ۱۲۳ است."

    monkeypatch.setattr("app.routes.attachments.analyze_attachment", fake_analyze)
    response = client.post(
        "/attachments/analyze",
        headers=auth,
        files={"file": ("invoice.jpg", b"image bytes", "image/jpeg")},
        data={"question": "شماره فاکتور را بخوان"},
    )

    assert response.status_code == 200
    assert response.json()["kind"] == "image"
    assert response.json()["analysis"] == "تصویر یک فاکتور با شماره ۱۲۳ است."
    assert captured == {
        "api_key": "test-key",
            "model": "gpt-5.6-sol",
        "filename": "invoice.jpg",
        "media_type": "image/jpeg",
        "content": b"image bytes",
        "question": "شماره فاکتور را بخوان",
    }


def test_attachment_rejects_unsupported_or_oversized_files(client, auth, settings):
    client.app.state.settings = replace(settings, openai_api_key="test-key")
    unsupported = client.post(
        "/attachments/analyze",
        headers=auth,
        files={"file": ("program.exe", b"binary", "application/octet-stream")},
    )
    oversized = client.post(
        "/attachments/analyze",
        headers=auth,
        files={"file": ("large.pdf", b"x" * (20 * 1024 * 1024 + 1), "application/pdf")},
    )
    assert unsupported.status_code == 415
    assert oversized.status_code == 413


def test_attachment_answer_is_not_replaced_by_database_history(settings, monkeypatch):
    from app.chat_service import chat
    from app.database import sqlite_connection

    tuned = replace(settings, openai_api_key="test-key")

    def database_agent_must_not_run(*_args, **_kwargs):
        raise AssertionError("attachment answers must not be sent through the database agent")

    monkeypatch.setattr("app.chat_service._run_agent_once", database_agent_must_not_run)
    response = chat(
        tuned,
        "این تصویر را دقیق بررسی کن.",
        "chair-photo",
        "Admin",
        attachment_context="در تصویر، نشیمن و تکیه‌گاه یک صندلی چرمی کرم‌رنگ دیده می‌شود.",
        attachment_name="image.jpg",
    )

    assert response["answer"] == "در تصویر، نشیمن و تکیه‌گاه یک صندلی چرمی کرم‌رنگ دیده می‌شود."
    assert "sql" not in response
    with sqlite_connection(tuned.sqlite_path) as conn:
        messages = conn.execute(
            "SELECT role, content FROM chat_messages WHERE conversation_id=? ORDER BY id",
            ("chair-photo",),
        ).fetchall()
    assert [row["role"] for row in messages] == ["user", "assistant"]
    assert "image.jpg" in messages[0]["content"]
    assert "فروش" not in messages[1]["content"]
