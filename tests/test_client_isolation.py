"""The shared HTTP client must isolate lifespan, not just request handlers."""
from pathlib import Path


def test_client_startup_uses_temporary_database_and_disables_workers(settings, tmp_path, monkeypatch, request):
    import app.main as main

    database_paths = []
    key_paths = []
    initialize = main.init_sqlite

    def isolated_database(path):
        assert Path(path) == settings.sqlite_path
        database_paths.append(path)
        initialize(path)

    def isolated_key(path):
        assert Path(path).parent == tmp_path
        key_paths.append(path)

    # Fail before any database access if the shared fixture ever regresses.
    monkeypatch.setattr(main, "ensure_action_api_key", lambda: None)
    monkeypatch.setattr(main, "init_sqlite", isolated_database)
    monkeypatch.setattr(main, "ensure_vapid_private_key", isolated_key)
    request.getfixturevalue("client")
    assert database_paths == [settings.sqlite_path]
    assert len(key_paths) == 1
    startup = main.get_settings()
    assert not startup.sql_configured
    assert not startup.metadata_sync_enabled
    assert not startup.automation_enabled
