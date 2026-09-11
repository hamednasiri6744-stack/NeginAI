import json

import pytest

from scripts import provision_sales_users as provisioning


def _review_user() -> dict[str, object]:
    return {
        "personnel_id": 22,
        "full_name": "Test User",
        "first_name": "Test",
        "last_name": "User",
        "role": "seller",
        "username": "test.user",
        "phone": "09120000000",
        "phone_status": "valid",
        "branch": "Alborz",
        "sales_line": "Market",
        "supervisor_personnel_id": 14,
        "supervisor_name": "Supervisor",
    }


def test_review_csv_contains_no_password_or_activation_secret(tmp_path, monkeypatch):
    output = tmp_path / "review.csv"
    monkeypatch.setattr(provisioning, "OUTPUT_CSV", output)
    user = _review_user()
    user["temporary_password"] = "must-not-be-written"
    user["activation_token"] = "must-not-be-written-either"

    provisioning.write_account_list([user], {})

    content = output.read_text(encoding="utf-8-sig")
    assert "must-not-be-written" not in content
    assert "must-not-be-written-either" not in content
    assert "One-time activation required" in content


def test_activation_bundle_is_explicit_json_and_cannot_be_overwritten(tmp_path):
    output = tmp_path / "activations.json"
    result = {
        "activation_expires_at": 12345,
        "activation_tokens": {"test.user": "unique-one-time-secret"},
    }

    provisioning.write_activation_bundle(output, result)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload == {
        "expires_at": 12345,
        "one_time_activation_tokens": {"test.user": "unique-one-time-secret"},
    }
    with pytest.raises(FileExistsError):
        provisioning.write_activation_bundle(output, result)


def test_activation_bundle_rejects_csv_destination(tmp_path):
    with pytest.raises(ValueError, match="must be a .json file"):
        provisioning.write_activation_bundle(
            tmp_path / "activations.csv",
            {"activation_expires_at": 1, "activation_tokens": {}},
        )
