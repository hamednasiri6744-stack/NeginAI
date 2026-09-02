"""Authenticated seller identity and team context for the assistant."""

from __future__ import annotations

from typing import Any

from app.auth_service import user_profile
from app.database import sqlite_connection
from app.organization_structure_service import list_structure


def seller_identity_context(settings: Any, username: str | None) -> dict[str, Any] | None:
    """Return trusted organizational meaning, never sales figures or report filters."""
    profile = user_profile(settings, str(username or ""))
    if not profile or str(profile.get("role") or "").casefold() != "\u0641\u0631\u0648\u0634\u0646\u062f\u0647":
        return None
    supervisor_id = profile.get("supervisor_personnel_id")
    with sqlite_connection(settings.sqlite_path) as conn:
        supervisor = conn.execute(
            "SELECT personnel_id, full_name FROM users WHERE personnel_id=?", (supervisor_id,)
        ).fetchone() if supervisor_id is not None else None
        peers = conn.execute(
            """SELECT personnel_id, full_name FROM users
               WHERE active=1 AND supervisor_personnel_id IS ? AND personnel_id != ?
               ORDER BY full_name, personnel_id""",
            (supervisor_id, profile.get("personnel_id")),
        ).fetchall()
    rules = [
        rule for rule in list_structure(settings)
        if rule["branch"] == profile["branch"] and rule["sales_line"] == profile["sales_line"]
        and (rule["supervisor_id"] is None or rule["supervisor_id"] == supervisor_id)
    ]
    return {
        "personnel_id": profile["personnel_id"],
        "full_name": profile["full_name"],
        "branch": profile["branch"],
        "sales_line": profile["sales_line"],
        "supervisor": (
            {"personnel_id": supervisor["personnel_id"], "full_name": supervisor["full_name"]}
            if supervisor else {"personnel_id": supervisor_id, "full_name": None}
            if supervisor_id is not None else None
        ),
        "teammates": [
            {"personnel_id": row["personnel_id"], "full_name": row["full_name"]}
            for row in peers
        ],
        "team_rules": rules,
        "meaning": (
            "Authenticated organization context only. 'my sales' means this seller's own sales; "
            "'my team' means users with the same direct supervisor. Customer financial reports "
            "cover customers in the seller's saved branch and sales line, including teammates "
            "and other teams in that same line."
        ),
    }
