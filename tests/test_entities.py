from app.database import sqlite_connection
from app.entity_service import normalize_entity_name, search_entities


def test_normalizes_arabic_and_persian_letters():
    assert normalize_entity_name("ويسـنالند") == normalize_entity_name("ویسنالند")
    assert normalize_entity_name("کاله") == normalize_entity_name("كاله")


def test_brand_and_manufacturer_remain_distinct(settings):
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.executemany(
            """INSERT INTO entity_catalog
               (entity_type,source_id,display_name,normalized_name,source_object,synced_at)
               VALUES(?,?,?,?,?,?)""",
            [
                ("brand", 42, "ويسنالند", normalize_entity_name("ويسنالند"), "GNR.tblBrand", "now"),
                ("manufacturer", 7, "ویسنالند تولید", normalize_entity_name("ویسنالند تولید"),
                 "GNR.tblManufacturer", "now"),
            ],
        )

    results = search_entities(settings, "ویسنالند", 10)
    assert results[0]["entity_type"] == "brand"
    assert results[0]["source_id"] == 42
    assert "BrandRef" in results[0]["technical_guidance"]["goods_join"]
    assert any(item["entity_type"] == "manufacturer" for item in results)

    brand_only = search_entities(settings, "فروش برند ویسنالند امروز", 10)
    assert brand_only
    assert {item["entity_type"] for item in brand_only} == {"brand"}

    manufacturer_only = search_entities(settings, "تولیدکننده ویسنالند", 10)
    assert manufacturer_only
    assert {item["entity_type"] for item in manufacturer_only} == {"manufacturer"}


def test_entity_endpoints_require_auth(client, auth, settings):
    response = client.get("/entities/stats", headers=auth)
    assert response.status_code == 200
    assert response.json()["brands"] == 0
    assert client.get("/entities/stats").status_code == 401
