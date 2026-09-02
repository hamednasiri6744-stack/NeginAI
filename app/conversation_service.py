from __future__ import annotations

import json
import re
from datetime import datetime
from uuid import uuid4

from app.config import Settings
from app.database import sqlite_connection


DEFAULT_TITLE = "گفت‌وگوی جدید"


def _now() -> str:
    return datetime.utcnow().isoformat()


def title_from_message(message: str, limit: int = 54) -> str:
    title = re.sub(r"\s+", " ", message).strip()
    if not title:
        return DEFAULT_TITLE
    return title if len(title) <= limit else f"{title[: limit - 1].rstrip()}…"


def ensure_conversation(
    settings: Settings,
    username: str,
    conversation_id: str | None,
    first_message: str = "",
) -> str:
    """Create or touch a user-owned conversation and prevent id cross-ownership."""
    requested = (conversation_id or "").strip() or str(uuid4())
    timestamp = _now()
    with sqlite_connection(settings.sqlite_path) as conn:
        existing = conn.execute(
            "SELECT username, title FROM chat_conversations WHERE id=?",
            (requested,),
        ).fetchone()
        if existing and str(existing["username"]).casefold() != username.casefold():
            requested = str(uuid4())
            existing = None
        if existing:
            title = str(existing["title"])
            if title == DEFAULT_TITLE and first_message.strip():
                title = title_from_message(first_message)
            conn.execute(
                "UPDATE chat_conversations SET title=?, updated_at=? WHERE id=?",
                (title, timestamp, requested),
            )
        else:
            conn.execute(
                """INSERT INTO chat_conversations
                   (id, username, title, pinned, created_at, updated_at)
                   VALUES (?, ?, ?, 0, ?, ?)""",
                (
                    requested,
                    username,
                    title_from_message(first_message),
                    timestamp,
                    timestamp,
                ),
            )
    return requested


def touch_conversation(settings: Settings, username: str, conversation_id: str) -> None:
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """UPDATE chat_conversations SET updated_at=?
               WHERE id=? AND username=? COLLATE NOCASE""",
            (_now(), conversation_id, username),
        )


def list_conversations(settings: Settings, username: str, limit: int = 100) -> list[dict[str, object]]:
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            """SELECT id, title, pinned, created_at, updated_at
               FROM chat_conversations
               WHERE username=? COLLATE NOCASE
               ORDER BY pinned DESC, updated_at DESC
               LIMIT ?""",
            (username, limit),
        ).fetchall()
    return [
        {
            "id": str(row["id"]),
            "title": str(row["title"]),
            "pinned": bool(row["pinned"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }
        for row in rows
    ]


def get_conversation(settings: Settings, username: str, conversation_id: str) -> dict[str, object] | None:
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            """SELECT id, title, pinned, created_at, updated_at
               FROM chat_conversations
               WHERE id=? AND username=? COLLATE NOCASE""",
            (conversation_id, username),
        ).fetchone()
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "title": str(row["title"]),
        "pinned": bool(row["pinned"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
    }


def conversation_messages(
    settings: Settings,
    username: str,
    conversation_id: str,
    limit: int = 200,
) -> list[dict[str, object]] | None:
    if get_conversation(settings, username, conversation_id) is None:
        return None
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            """SELECT id, role, content, response_json, created_at
               FROM chat_messages
               WHERE conversation_id=?
               ORDER BY id DESC LIMIT ?""",
            (conversation_id, limit),
        ).fetchall()
    result: list[dict[str, object]] = []
    for row in reversed(rows):
        response = None
        if row["response_json"]:
            try:
                response = json.loads(str(row["response_json"]))
            except (TypeError, ValueError):
                response = None
        result.append(
            {
                "id": int(row["id"]),
                "role": str(row["role"]),
                "content": str(row["content"]),
                "response": response,
                "created_at": str(row["created_at"]),
            }
        )
    return result


def update_conversation(
    settings: Settings,
    username: str,
    conversation_id: str,
    *,
    title: str | None = None,
    pinned: bool | None = None,
) -> dict[str, object] | None:
    current = get_conversation(settings, username, conversation_id)
    if current is None:
        return None
    next_title = title_from_message(title, 80) if title is not None else str(current["title"])
    next_pinned = int(pinned if pinned is not None else bool(current["pinned"]))
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """UPDATE chat_conversations
               SET title=?, pinned=?, updated_at=?
               WHERE id=? AND username=? COLLATE NOCASE""",
            (next_title, next_pinned, _now(), conversation_id, username),
        )
    return get_conversation(settings, username, conversation_id)


def delete_conversation(settings: Settings, username: str, conversation_id: str) -> bool:
    if get_conversation(settings, username, conversation_id) is None:
        return False
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute("DELETE FROM chat_messages WHERE conversation_id=?", (conversation_id,))
        conn.execute(
            "DELETE FROM chat_conversations WHERE id=? AND username=? COLLATE NOCASE",
            (conversation_id, username),
        )
        conn.execute(
            "DELETE FROM chat_sessions WHERE username=? COLLATE NOCASE AND conversation_id=?",
            (username, conversation_id),
        )
    return True
