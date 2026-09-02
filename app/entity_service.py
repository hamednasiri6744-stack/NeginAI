from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from app.config import Settings
from app.database import sql_connection, sqlite_connection


ENTITY_SOURCES = {
    "brand": {
        "sql": "SELECT id, BrandName FROM GNR.tblBrand WHERE BrandName IS NOT NULL",
        "object": "GNR.tblBrand",
    },
    "manufacturer": {
        "sql": "SELECT Id, ManufacturerName FROM GNR.tblManufacturer WHERE ManufacturerName IS NOT NULL",
        "object": "GNR.tblManufacturer",
    },
}

ENTITY_GUIDANCE = {
    "brand": {
        "label_fa": "برند",
        "canonical_object": "GNR.tblBrand",
        "goods_join": "GNR.tblGoods.BrandRef = GNR.tblBrand.id",
        "sales_join": "dbo.SalesReviewFast.GoodsId = GNR.tblGoods.ID",
        "rule": "برای برند هرگز ManufacturerName را فیلتر نکن؛ BrandRef را به GNR.tblBrand وصل کن.",
    },
    "manufacturer": {
        "label_fa": "تولیدکننده",
        "canonical_object": "GNR.tblManufacturer",
        "goods_join": "GNR.tblGoods.ManufacturerRef = GNR.tblManufacturer.Id",
        "sales_fields": "dbo.SalesReviewFast.ManufacturerId, dbo.SalesReviewFast.ManufacturerName",
        "rule": "تولیدکننده با برند متفاوت است؛ فقط ManufacturerRef/ManufacturerId را به‌کار ببر.",
    },
}


def normalize_entity_name(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    value = value.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه"}))
    value = re.sub(r"[\u064b-\u065f\u0670\u200c\u200d\u0640]", "", value)
    return re.sub(r"[^0-9a-zآ-ی]+", "", value)


def _set_status(settings: Settings, *, success: bool, error: str | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite_connection(settings.sqlite_path) as conn:
        conn.execute(
            """INSERT INTO entity_sync_status(singleton,last_attempt,last_success,last_error)
               VALUES(1,?,?,?) ON CONFLICT(singleton) DO UPDATE SET
               last_attempt=excluded.last_attempt,
               last_success=CASE WHEN excluded.last_error IS NULL THEN excluded.last_attempt ELSE last_success END,
               last_error=excluded.last_error""",
            (now, now if success else None, error),
        )


def sync_entities(settings: Settings) -> dict[str, Any]:
    if not settings.sql_configured:
        return {"status": "skipped", "reason": "sql_not_configured"}
    now = datetime.now(timezone.utc).isoformat()
    try:
        fetched: dict[str, list[tuple[int, str]]] = {}
        with sql_connection(settings) as conn:
            cursor = conn.cursor()
            for entity_type, source in ENTITY_SOURCES.items():
                fetched[entity_type] = [
                    (int(row[0]), str(row[1]).strip())
                    for row in cursor.execute(source["sql"]).fetchall()
                    if str(row[1]).strip()
                ]
        with sqlite_connection(settings.sqlite_path) as conn:
            for entity_type, rows in fetched.items():
                conn.execute("DELETE FROM entity_catalog WHERE entity_type = ?", (entity_type,))
                conn.executemany(
                    """INSERT INTO entity_catalog
                       (entity_type,source_id,display_name,normalized_name,source_object,synced_at)
                       VALUES(?,?,?,?,?,?)""",
                    [(entity_type, source_id, name, normalize_entity_name(name),
                      ENTITY_SOURCES[entity_type]["object"], now) for source_id, name in rows],
                )
        _set_status(settings, success=True)
        return {"status": "completed", "synced_at": now,
                "brands": len(fetched["brand"]), "manufacturers": len(fetched["manufacturer"])}
    except Exception as exc:
        _set_status(settings, success=False, error=str(exc)[:1000])
        raise


def search_entities(settings: Settings, query: str, limit: int = 10) -> list[dict[str, Any]]:
    needle = normalize_entity_name(query)
    if not needle:
        return []
    normalized_query = normalize_entity_name(query)
    requested_type = None
    if "تولیدکننده" in query or "توليدكننده" in query or "توليد کننده" in query:
        requested_type = "manufacturer"
    elif "برند" in query or "نام تجاری" in query or "نام تجاري" in query:
        requested_type = "brand"
    search_needle = normalized_query
    for cue in ("تولیدکننده", "توليدکننده", "توليدكننده", "برند", "نامتجاری", "نامتجاري"):
        search_needle = search_needle.replace(normalize_entity_name(cue), "")
    if search_needle:
        needle = search_needle
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute("SELECT * FROM entity_catalog").fetchall()
    ranked = []
    for row in rows:
        if requested_type and row["entity_type"] != requested_type:
            continue
        name = row["normalized_name"]
        score = SequenceMatcher(None, needle, name).ratio()
        if needle == name:
            score = 2.0
        elif needle in name or name in needle:
            score = max(score, 1.25)
        elif name in normalized_query:
            score = max(score, 1.2)
        if score >= 0.55:
            ranked.append((score, row))
    ranked.sort(key=lambda item: (-item[0], len(item[1]["display_name"]), item[1]["display_name"]))
    return [{
        "entity_type": row["entity_type"], "entity_type_fa": ENTITY_GUIDANCE[row["entity_type"]]["label_fa"],
        "source_id": row["source_id"], "name": row["display_name"],
        "match_score": round(min(score, 1.0), 3), "source_object": row["source_object"],
        "technical_guidance": ENTITY_GUIDANCE[row["entity_type"]],
    } for score, row in ranked[:limit]]


def entity_stats(settings: Settings) -> dict[str, Any]:
    with sqlite_connection(settings.sqlite_path) as conn:
        counts = {row[0]: row[1] for row in conn.execute(
            "SELECT entity_type, COUNT(*) FROM entity_catalog GROUP BY entity_type"
        ).fetchall()}
        status = conn.execute("SELECT * FROM entity_sync_status WHERE singleton=1").fetchone()
    return {"brands": counts.get("brand", 0), "manufacturers": counts.get("manufacturer", 0),
            "last_attempt": status["last_attempt"] if status else None,
            "last_success": status["last_success"] if status else None,
            "last_error": status["last_error"] if status else None}
