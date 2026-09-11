from pathlib import Path

from tools.security.release_tree_guard import release_tree_violations


def test_release_guard_accepts_source_only_tree(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("print('safe')\n", encoding="utf-8")
    assert release_tree_violations(tmp_path) == []


def test_release_guard_rejects_runtime_browser_and_key_material(tmp_path: Path) -> None:
    cookie = tmp_path / "data" / "chrome-admin" / "Default" / "Network" / "Cookies"
    cookie.parent.mkdir(parents=True)
    cookie.write_bytes(b"sqlite")
    (tmp_path / "data" / "neginai.db").write_bytes(b"sqlite")
    (tmp_path / "data" / "vapid.pem").write_bytes(b"-----BEGIN PRIVATE KEY-----\nredacted")

    violations = release_tree_violations(tmp_path)
    assert any("Cookies" in item for item in violations)
    assert any("neginai.db" in item for item in violations)
    assert any("vapid.pem" in item for item in violations)
    assert all("redacted" not in item for item in violations)
