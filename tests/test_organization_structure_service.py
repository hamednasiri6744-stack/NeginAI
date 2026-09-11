from app.auth_service import create_session, create_user
from app.database import sqlite_connection
from app.organization_structure_service import (
    create_proposal,
    list_proposals,
    list_structure,
    review_proposal,
    seed_confirmed_rules,
    update_rule,
)


def test_seeded_structure_is_available_and_is_not_duplicated(settings):
    seed_confirmed_rules(settings)
    seed_confirmed_rules(settings)

    rules = list_structure(settings)

    assert any(rule["branch"] == "\u062f\u0641\u062a\u0631 \u0641\u0631\u0648\u0634 \u0627\u0644\u0628\u0631\u0632" and rule["team_split"] == "brand" for rule in rules)
    assert len(rules) == 17
    navid = next(rule for rule in rules if rule["supervisor_id"] == 14)
    assert navid["supervisor_name"] == "\u0646\u0648\u06cc\u062f \u0627\u0633\u0645\u0627\u0639\u06cc\u0644\u200c\u0632\u0627\u062f\u0647"
    assert navid["brand_portfolio"] == ["Misswake", "Umbrella", "Dafi", "Wolf", "Confident", "Codex"]


def test_proposal_notifies_admin_and_only_changes_rule_after_approval(settings):
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, active, role, created_at, updated_at) VALUES (?, ?, 1, 'admin', ?, ?)",
            ("manager", "not-used", "now", "now"),
        )

    proposal = create_proposal(
        settings,
        proposal_type="team_rule",
        branch="branch-x",
        sales_line="line-x",
        subject_type="supervisor",
        subject_id=42,
        current_value={},
        proposed_value={"supervisor_id": 42, "supervisor_name": "Test", "team_split": "brand"},
        evidence={"observation_days": 21},
        confidence=0.91,
    )

    assert proposal["status"] == "pending"
    assert len(list_proposals(settings)) == 1
    with sqlite_connection(settings.sqlite_path) as conn:
        notification = conn.execute("SELECT title FROM notifications WHERE username='manager'").fetchone()
    assert notification is not None
    assert not any(rule["branch"] == "branch-x" for rule in list_structure(settings))

    reviewed = review_proposal(settings, proposal["id"], "approved", "manager")

    assert reviewed["status"] == "approved"
    assert any(rule["branch"] == "branch-x" and rule["supervisor_id"] == 42 for rule in list_structure(settings))


def test_admin_structure_api_lists_rules_and_pending_proposals(client, settings):
    create_user(settings, "Admin", "StrongPass9")
    token = create_session(settings, "Admin")
    headers = {"Cookie": f"negin_session={token}"}
    response = client.get("/organization-structure", headers=headers)
    proposals = client.get("/organization-structure/proposals?status=pending", headers=headers)

    assert response.status_code == 200
    assert response.json()["rules"]
    assert proposals.status_code == 200


def test_admin_can_set_team_type_and_brand_portfolio(settings):
    seed_confirmed_rules(settings)
    rule = next(rule for rule in list_structure(settings) if rule["team_split"] == "brand")

    saved = update_rule(
        settings, rule["id"], team_split="brand", brand_portfolio=["Brand A", "Brand B", "Brand A"], notes="confirmed",
    )

    assert saved["brand_portfolio"] == ["Brand A", "Brand B"]
    assert saved["notes"] == "confirmed"
