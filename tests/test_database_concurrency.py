from concurrent.futures import ThreadPoolExecutor

from app.database import init_sqlite, sqlite_connection


def test_sqlite_connections_wait_for_transient_writers_and_enforce_foreign_keys(settings):
    with sqlite_connection(settings.sqlite_path) as connection:
        assert connection.execute("PRAGMA busy_timeout").fetchone()[0] >= 30_000
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_parallel_application_startup_reuses_the_same_sqlite_database(tmp_path):
    database_path = tmp_path / "parallel-startup.db"

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(init_sqlite, [database_path] * 4))

    with sqlite_connection(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table'"
        ).fetchone()[0] > 0
