from app.username_service import assign_unique_usernames, base_username


def test_expected_personnel_username_format():
    assert base_username("عارف", "کامران") == "A.kamran"
    assert base_username("محمود", "اعتمادی") == "M.etemadi"
    assert base_username("ایمان", "شریف پور") == "I.sharifpour"


def test_duplicate_base_usernames_receive_deterministic_suffix():
    values = assign_unique_usernames(
        [
            {"personnel_id": 20, "first_name": "حسن", "last_name": "احمدی"},
            {"personnel_id": 10, "first_name": "حامد", "last_name": "احمدی"},
        ]
    )
    assert values == {10: "H.ahmadi", 20: "H.ahmadi2"}
