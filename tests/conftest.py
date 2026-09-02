from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.database import init_sqlite
from app.main import app


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    value = Settings(
        sql_server="", sql_database="NeginPakhsh", sql_username="", sql_password="",
        sql_driver="ODBC Driver 18 for SQL Server", sql_trust_certificate=True,
        sql_query_timeout=30, sql_max_rows=1000, action_api_key="test-internal-key",
        sqlite_path=tmp_path / "test.db",
    )
    init_sqlite(value.sqlite_path)
    return value


@pytest.fixture
def client(settings: Settings):
    with TestClient(app) as test_client:
        app.state.settings = settings
        yield test_client


@pytest.fixture
def auth():
    return {"X-API-Key": "test-internal-key"}
