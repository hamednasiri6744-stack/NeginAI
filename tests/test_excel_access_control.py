import json

from app.auth_service import create_session, provision_users
from app.conversation_service import ensure_conversation
from app.database import sqlite_connection


def test_seller_cannot_export_a_report_created_without_current_access_scope(
    client, settings
):
    provision_users(
        settings,
        [
            {
                "username": "A.kamran",
                "personnel_id": 22,
                "full_name": "عارف کامران",
                "role": "فروشنده",
                "branch": "دفتر فروش البرز",
                "sales_line": "لاین مارکت",
                "phone": "09120000000",
                "phone_status": "معتبر",
                "supervisor_personnel_id": 14,
            }
        ],
    )
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            "UPDATE users SET must_change_password=0 WHERE username='A.kamran'"
        )
    ensure_conversation(settings, "A.kamran", "seller-old-report", "گزارش")
    response_payload = {
        "conversation_id": "seller-old-report",
        "answer": "گزارش قدیمی",
        "columns": ["NetSales"],
        "rows": [[123]],
        "row_count": 1,
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO chat_messages
               (conversation_id, role, content, sources_json, response_json, created_at)
               VALUES (?, 'assistant', ?, '[]', ?, '2026-08-09T12:00:00')""",
            (
                "seller-old-report",
                response_payload["answer"],
                json.dumps(response_payload, ensure_ascii=False),
            ),
        )
    token = create_session(settings, "A.kamran")
    headers = {"Cookie": f"negin_session={token}"}

    blocked = client.get(
        "/chat/conversations/seller-old-report/export.xlsx", headers=headers
    )

    assert blocked.status_code == 403

    response_payload["access_scope"] = {
        "mode": "seller_customer_scope",
        "branch": "دفتر فروش البرز",
        "sales_line": "لاین مارکت",
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            "UPDATE chat_messages SET response_json=? WHERE conversation_id=?",
            (json.dumps(response_payload, ensure_ascii=False), "seller-old-report"),
        )

    allowed = client.get(
        "/chat/conversations/seller-old-report/export.xlsx", headers=headers
    )
    assert allowed.status_code == 200
