"""Versioned team-structure settings and administrator change proposals."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal

from app.database import sqlite_connection


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _proposal_from_row(row: Any) -> dict[str, Any]:
    item = dict(row)
    for key in ("current_value_json", "proposed_value_json", "evidence_json"):
        item[key.removesuffix("_json")] = json.loads(item.pop(key) or "{}")
    return item


def _is_admin(settings: Any, username: str) -> bool:
    if username in {"local", "Admin"}:
        return True
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute("SELECT role FROM users WHERE username=?", (username,)).fetchone()
    return bool(row and str(row["role"] or "").casefold() in {"admin", "administrator", "\u0645\u062f\u06cc\u0631"})


def require_admin(settings: Any, username: str) -> None:
    if not _is_admin(settings, username):
        raise PermissionError("Administrator access is required")


def list_structure(settings: Any) -> list[dict[str, Any]]:
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            """SELECT * FROM team_structure_rules
               WHERE status != 'retired'
               ORDER BY branch, sales_line, supervisor_name, supervisor_id"""
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["brand_portfolio"] = json.loads(item.pop("brand_portfolio_json") or "[]")
        result.append(item)
    return result


def update_rule(
    settings: Any, rule_id: int, *, team_split: str, brand_portfolio: list[str], notes: str,
) -> dict[str, Any]:
    """Maintain semantic team metadata; this never changes source-report SQL."""
    if team_split not in {"brand", "region_or_customer", "unspecified"}:
        raise ValueError("Invalid team split")
    portfolio = sorted({str(brand).strip() for brand in brand_portfolio if str(brand).strip()})
    now = _now()
    with sqlite_connection(settings.sqlite_path) as conn:
        updated = conn.execute(
            """UPDATE team_structure_rules
               SET team_split=?, brand_portfolio_json=?, notes=?, updated_at=?
               WHERE id=? AND status != 'retired'""",
            (team_split, json.dumps(portfolio, ensure_ascii=False), notes.strip(), now, rule_id),
        )
        if updated.rowcount != 1:
            raise ValueError("Team rule not found")
    return next(rule for rule in list_structure(settings) if int(rule["id"]) == rule_id)


def list_proposals(settings: Any, status: str = "pending") -> list[dict[str, Any]]:
    sql = "SELECT * FROM team_change_proposals"
    params: list[Any] = []
    if status != "all":
        sql += " WHERE status=?"
        params.append(status)
    sql += " ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, id DESC"
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_proposal_from_row(row) for row in rows]


def create_proposal(
    settings: Any, *, proposal_type: str, branch: str, sales_line: str,
    subject_type: str, subject_id: int | None, current_value: dict[str, Any],
    proposed_value: dict[str, Any], evidence: dict[str, Any], confidence: float,
) -> dict[str, Any]:
    """Create a reviewable suggestion and place it in every administrator inbox."""
    now = _now()
    confidence = max(0.0, min(float(confidence), 1.0))
    encoded_value = json.dumps(proposed_value, ensure_ascii=False, sort_keys=True)
    with sqlite_connection(settings.sqlite_path) as conn:
        existing = conn.execute(
            """SELECT * FROM team_change_proposals
               WHERE status='pending' AND proposal_type=? AND branch=? AND sales_line=?
                 AND subject_type=? AND subject_id IS ? AND proposed_value_json=?""",
            (proposal_type, branch, sales_line, subject_type, subject_id, encoded_value),
        ).fetchone()
        if existing:
            return _proposal_from_row(existing)
        cursor = conn.execute(
            """INSERT INTO team_change_proposals
               (proposal_type, branch, sales_line, subject_type, subject_id,
                current_value_json, proposed_value_json, evidence_json, confidence,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (proposal_type, branch, sales_line, subject_type, subject_id,
             json.dumps(current_value, ensure_ascii=False), encoded_value,
             json.dumps(evidence, ensure_ascii=False), confidence, now, now),
        )
        proposal_id = int(cursor.lastrowid)
        admins = conn.execute(
            "SELECT username FROM users WHERE lower(COALESCE(role,'')) IN ('admin','administrator') OR username='Admin'"
        ).fetchall()
        for admin in admins:
            conn.execute(
                """INSERT INTO notifications (username, title, body, payload_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (str(admin["username"]), "\u067e\u06cc\u0634\u0646\u0647\u0627\u062f \u062a\u063a\u06cc\u06cc\u0631 \u0633\u0627\u062e\u062a\u0627\u0631 \u062a\u06cc\u0645",
                 f"{branch} / {sales_line}: \u06cc\u06a9 \u067e\u06cc\u0634\u0646\u0647\u0627\u062f \u062c\u062f\u06cc\u062f \u0628\u0631\u0627\u06cc \u0628\u0631\u0631\u0633\u06cc \u062f\u0627\u0631\u06cc\u062f.",
                 json.dumps({"kind": "team_structure_proposal", "proposal_id": proposal_id}, ensure_ascii=False), now),
            )
        row = conn.execute("SELECT * FROM team_change_proposals WHERE id=?", (proposal_id,)).fetchone()
    return _proposal_from_row(row)


def review_proposal(
    settings: Any, proposal_id: int, decision: Literal["approved", "rejected"], reviewer: str,
) -> dict[str, Any]:
    now = _now()
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute("SELECT * FROM team_change_proposals WHERE id=?", (proposal_id,)).fetchone()
        if row is None or row["status"] != "pending":
            raise ValueError("Pending proposal not found")
        conn.execute(
            "UPDATE team_change_proposals SET status=?, reviewed_by=?, reviewed_at=?, updated_at=? WHERE id=?",
            (decision, reviewer, now, now, proposal_id),
        )
        if decision == "approved" and row["proposal_type"] == "team_rule":
            value = json.loads(row["proposed_value_json"] or "{}")
            conn.execute(
                """INSERT INTO team_structure_rules
                   (branch, sales_line, supervisor_id, supervisor_name, team_split, brand_portfolio_json, status, valid_from, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?, ?, ?, ?)""",
                (row["branch"], row["sales_line"], value.get("supervisor_id"), value.get("supervisor_name"),
                 value.get("team_split", "unspecified"), json.dumps(value.get("brand_portfolio", []), ensure_ascii=False),
                 value.get("valid_from"), value.get("notes", ""), now, now),
            )
        updated = conn.execute("SELECT * FROM team_change_proposals WHERE id=?", (proposal_id,)).fetchone()
    return _proposal_from_row(updated)


def seed_confirmed_rules(settings: Any) -> None:
    """Seed confirmed branch/line rules; observations never modify them automatically."""
    now = _now()
    rows = [
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u062a\u0647\u0631\u0627\u0646", "\u0644\u0627\u06cc\u0646 \u0645\u0627\u0631\u06a9\u062a", "region_or_customer"),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u062a\u0647\u0631\u0627\u0646", "\u0644\u0627\u06cc\u0646 \u062f\u0627\u0631\u0648\u062e\u0627\u0646\u0647", "region_or_customer"),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u0645\u0627\u0631\u06a9\u062a", "brand"),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u062f\u0627\u0631\u0648\u062e\u0627\u0646\u0647", "brand"),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u06af\u0627\u0644\u0631\u06cc", "region_or_customer"),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u0632\u0646\u062c\u06cc\u0631\u0647 \u0627\u06cc", "region_or_customer"),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u0639\u0645\u062f\u0647 \u0641\u0631\u0648\u0634\u06cc", "region_or_customer"),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0642\u0632\u0648\u06cc\u0646", "\u0644\u0627\u06cc\u0646 \u0645\u0627\u0631\u06a9\u062a", "brand"),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u06af\u06cc\u0644\u0627\u0646", "\u0644\u0627\u06cc\u0646 \u0645\u0627\u0631\u06a9\u062a", "region_or_customer"),
    ]
    confirmed_teams = [
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u0645\u0627\u0631\u06a9\u062a", 14, "\u0646\u0648\u06cc\u062f \u0627\u0633\u0645\u0627\u0639\u06cc\u0644\u200c\u0632\u0627\u062f\u0647", "brand", ["Misswake", "Umbrella", "Dafi", "Wolf", "Confident", "Codex"]),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u0645\u0627\u0631\u06a9\u062a", 17, "\u0645\u0647\u062f\u06cc \u0627\u0633\u0645\u0639\u06cc\u0644\u06cc", "brand", ["Rapido", "Duru", "Fox"]),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u0645\u0627\u0631\u06a9\u062a", 19, "\u0627\u0645\u06cc\u0631\u062d\u0633\u06cc\u0646 \u0634\u0648\u0646\u062f\u06cc", "brand", ["Coman", "Plankton", "Filfil", "Kapoot", "Hero Water", "Shian"]),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u0645\u0627\u0631\u06a9\u062a", 677, "\u0645\u0647\u062f\u06cc \u0646\u0639\u0645\u062a\u06cc", "brand", ["Hani", "Espino", "Zaki", "Teams", "Bartar"]),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u062f\u0627\u0631\u0648\u062e\u0627\u0646\u0647", 419, "\u0622\u0631\u0645\u0627\u0646 \u0631\u0633\u062a\u0645 \u0644\u0648", "brand", ["Codex", "Pixel", "V1"]),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u062f\u0627\u0631\u0648\u062e\u0627\u0646\u0647", 44, "\u0645\u062d\u0645\u062f \u0637\u0647\u0648\u0631\u06cc \u0646\u06cc\u0627", "brand", ["Misswake", "Umbrella", "Dafi"]),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u062f\u0627\u0631\u0648\u062e\u0627\u0646\u0647", 188, "\u067e\u0648\u0631\u06cc\u0627 \u0631\u0636\u0627\u06cc\u06cc \u062d\u0631\u0645 \u0622\u0628\u0627\u062f\u06cc", "brand", ["Coman", "Confident", "Capitano", "Capos", "Kelamin"]),
        ("\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632", "\u0644\u0627\u06cc\u0646 \u062f\u0627\u0631\u0648\u062e\u0627\u0646\u0647", 675, "\u0627\u0645\u06cc\u0631 \u0645\u0633\u0639\u0648\u062f \u0637\u0627\u0648\u0648\u0633\u06cc", "brand", ["Deodrug", "Sivand", "Servina"]),
    ]
    with sqlite_connection(settings.sqlite_path) as conn:
        for branch, line, split in rows:
            existing = conn.execute(
                """SELECT 1 FROM team_structure_rules
                   WHERE branch=? AND sales_line=? AND supervisor_id IS NULL AND status='confirmed'""",
                (branch, line),
            ).fetchone()
            if existing:
                continue
            conn.execute(
                """INSERT INTO team_structure_rules
                   (branch, sales_line, team_split, status, notes, created_at, updated_at)
                   VALUES (?, ?, ?, 'confirmed', ?, ?, ?)""",
                (branch, line, split, "\u0642\u0627\u0639\u062f\u0647 \u062a\u0623\u06cc\u06cc\u062f\u0634\u062f\u0647 \u062a\u0648\u0633\u0637 \u0645\u062f\u06cc\u0631\u06cc\u062a", now, now),
            )
        for branch, line, supervisor_id, supervisor_name, split, brands in confirmed_teams:
            existing = conn.execute(
                """SELECT id, brand_portfolio_json FROM team_structure_rules
                   WHERE branch=? AND sales_line=? AND supervisor_id=? AND status='confirmed'""",
                (branch, line, supervisor_id),
            ).fetchone()
            if existing:
                if not json.loads(existing["brand_portfolio_json"] or "[]"):
                    conn.execute(
                        "UPDATE team_structure_rules SET brand_portfolio_json=?, updated_at=? WHERE id=?",
                        (json.dumps(brands, ensure_ascii=False), now, existing["id"]),
                    )
                continue
            conn.execute(
                """INSERT INTO team_structure_rules
                   (branch, sales_line, supervisor_id, supervisor_name, team_split, brand_portfolio_json, status, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'confirmed', ?, ?, ?)""",
                (branch, line, supervisor_id, supervisor_name, split, json.dumps(brands, ensure_ascii=False),
                 "\u062a\u06cc\u0645 \u0648 \u0633\u0628\u062f \u0628\u0631\u0646\u062f \u062a\u0623\u06cc\u06cc\u062f\u0634\u062f\u0647 \u062a\u0648\u0633\u0637 \u0645\u062f\u06cc\u0631\u06cc\u062a.", now, now),
            )

