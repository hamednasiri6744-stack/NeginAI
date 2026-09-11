from app.access_control import policy_for_user
from app.auth_service import provision_users
from app.user_workspace_service import build_user_workspace


def test_workspace_contains_authenticated_identity_org_and_access(settings):
    provision_users(
        settings,
        [
            {
                "username": "boss",
                "personnel_id": 14,
                "full_name": "سرپرست",
                "role": "سرپرست",
                "branch": "البرز",
                "sales_line": "مارکت",
            },
            {
                "username": "seller",
                "personnel_id": 22,
                "full_name": "فروشنده تست",
                "role": "فروشنده",
                "branch": "البرز",
                "sales_line": "مارکت",
                "supervisor_personnel_id": 14,
            },
        ],
    )
    policy = policy_for_user(settings, "seller")

    workspace = build_user_workspace(settings, "seller", policy)

    assert workspace["identity"]["full_name"] == "فروشنده تست"
    assert workspace["organization"]["supervisor"]["personnel_id"] == 14
    assert workspace["access"]["mode"] == "seller_customer_scope"
    assert workspace["live_workspace"]["available"] is True
    assert workspace["live_workspace"]["lazy"] is True
