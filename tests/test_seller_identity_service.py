from app.auth_service import provision_users
from app.seller_identity_service import seller_identity_context


def test_signed_in_seller_gets_self_supervisor_and_teammates(settings):
    provision_users(
        settings,
        [
            {"username": "boss", "personnel_id": 14, "full_name": "Navid", "role": "supervisor", "branch": "Alborz", "sales_line": "Market"},
            {"username": "seller", "personnel_id": 22, "full_name": "Kamran", "role": "\u0641\u0631\u0648\u0634\u0646\u062f\u0647", "branch": "Alborz", "sales_line": "Market", "supervisor_personnel_id": 14},
            {"username": "peer", "personnel_id": 23, "full_name": "Sara", "role": "\u0641\u0631\u0648\u0634\u0646\u062f\u0647", "branch": "Alborz", "sales_line": "Market", "supervisor_personnel_id": 14},
        ],
    )

    identity = seller_identity_context(settings, "seller")

    assert identity and identity["full_name"] == "Kamran"
    assert identity["supervisor"] == {"personnel_id": 14, "full_name": "Navid"}
    assert identity["teammates"] == [{"personnel_id": 23, "full_name": "Sara"}]
