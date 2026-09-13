import json
from datetime import datetime, timezone

from app.database import sqlite_connection
from app.schema_service import search_schema


def test_persian_business_term_expands_to_technical_schema_names(client, auth, settings):
    factor = {
        "schema": "dbo", "name": "tblFactor", "type": "TABLE",
        "columns": [{"name": "FactorDate"}, {"name": "TotalAmount"}],
        "foreign_keys": [], "referenced_by": [],
    }
    unrelated = {
        "schema": "dbo", "name": "Users", "type": "TABLE",
        "columns": [{"name": "UserName"}], "foreign_keys": [], "referenced_by": [],
    }
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.executemany(
            """INSERT INTO schema_objects
               (schema_name, object_name, object_type, details_json, scanned_at)
               VALUES (?, ?, ?, ?, ?)""",
            [
                ("dbo", "tblFactor", "TABLE", json.dumps(factor), datetime.now(timezone.utc).replace(tzinfo=None).isoformat()),
                ("dbo", "Users", "TABLE", json.dumps(unrelated), datetime.now(timezone.utc).replace(tzinfo=None).isoformat()),
            ],
        )

    response = client.get("/schema/search", params={"q": "فروش امروز"}, headers=auth)

    assert response.status_code == 200
    payload = response.json()
    assert {"sale", "sales", "invoice", "factor", "order"} <= set(payload["expanded_terms"])
    assert payload["results"][0]["name"] == "tblFactor"
    assert payload["results"][0]["column_count"] == 2
    assert "columns" not in payload["results"][0]
    assert all(item["name"] != "Users" for item in payload["results"])

    with sqlite_connection(settings.sqlite_path) as conn:
        indexed = conn.execute(
            "SELECT COUNT(*) FROM schema_search_terms WHERE term = 'factor'"
        ).fetchone()[0]
    assert indexed == 1

    stats = client.get("/schema/stats", headers=auth)
    assert stats.status_code == 200
    assert stats.json()["tables"] == 2
    assert stats.json()["views"] == 0


def test_schema_search_ranks_all_matching_objects_before_limiting(settings):
    with sqlite_connection(settings.sqlite_path) as conn:
        for index in range(350):
            item = {
                "schema": "dbo",
                "name": f"SalesEvidence{index:03d}",
                "type": "TABLE",
                "columns": [{"name": "SalesAmount"}],
                "foreign_keys": [],
                "referenced_by": [],
            }
            conn.execute(
                """INSERT INTO schema_objects
                   (schema_name, object_name, object_type, details_json, scanned_at)
                   VALUES (?, ?, ?, ?, ?)""",
                ("dbo", item["name"], "TABLE", json.dumps(item), datetime.now(timezone.utc).replace(tzinfo=None).isoformat()),
            )

    results = search_schema(settings, "sales", 400)

    assert len(results) == 350
