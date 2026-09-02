from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.config import Settings
from app.business_terms import expand_business_query
from app.database import sqlite_connection
from app.models import DefinitionCreate, DefinitionUpdate


_DEFINITION_STOP_TERMS = frozenset({
    "امروز", "دیروز", "فردا", "روز", "ماه", "سال", "هفته", "جاری", "قبل",
    "بگو", "بده", "نشان", "گزارش", "کدام", "چقدر", "چه", "این", "آن",
    "today", "yesterday", "report", "show", "give",
})


def _row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"], "term": row["term"], "definition": row["definition"], "rules": row["rules"],
        "approved_sql": row["approved_sql"], "related_objects": json.loads(row["related_objects_json"]),
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def create_definition(settings: Settings, payload: DefinitionCreate) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with sqlite_connection(settings.sqlite_path) as conn:
        cursor = conn.execute(
            """INSERT INTO definitions
               (term, definition, rules, approved_sql, related_objects_json, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (payload.term, payload.definition, payload.rules, payload.approved_sql,
             json.dumps(payload.related_objects, ensure_ascii=False), now, now),
        )
        row = conn.execute("SELECT * FROM definitions WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _row(row)


def update_definition(settings: Settings, definition_id: int, payload: DefinitionUpdate) -> dict[str, Any] | None:
    now = datetime.utcnow().isoformat()
    with sqlite_connection(settings.sqlite_path) as conn:
        cursor = conn.execute(
            """UPDATE definitions SET term=?, definition=?, rules=?, approved_sql=?,
               related_objects_json=?, updated_at=? WHERE id=?""",
            (payload.term, payload.definition, payload.rules, payload.approved_sql,
             json.dumps(payload.related_objects, ensure_ascii=False), now, definition_id),
        )
        if cursor.rowcount == 0:
            return None
        row = conn.execute("SELECT * FROM definitions WHERE id = ?", (definition_id,)).fetchone()
    return _row(row)


def delete_definition(settings: Settings, definition_id: int) -> bool:
    with sqlite_connection(settings.sqlite_path) as conn:
        return conn.execute("DELETE FROM definitions WHERE id = ?", (definition_id,)).rowcount > 0


def list_definitions(settings: Settings, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute("SELECT * FROM definitions ORDER BY updated_at DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
    return [_row(row) for row in rows]


def search_definitions(settings: Settings, query: str, limit: int = 20) -> list[dict[str, Any]]:
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute("SELECT * FROM definitions ORDER BY updated_at DESC").fetchall()
    terms = [term for term in expand_business_query(query) if term not in _DEFINITION_STOP_TERMS]
    normalized_query = query.strip().casefold()
    matches = []
    for row in rows:
        text = " ".join((row["term"], row["definition"], row["rules"], row["related_objects_json"])).casefold()
        definition_term = str(row["term"] or "").strip().casefold()
        score = sum(2 if term in definition_term else 1 for term in terms if term in text)
        if definition_term and definition_term in normalized_query:
            score += 12
        if score:
            matches.append((score, row["updated_at"], row))
    matches.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [_row(item[2]) for item in matches[:limit]]
