import json

from fastapi import APIRouter, Depends, Query, Request

from app.database import sqlite_connection
from app.routes.dependencies import require_api_key

router = APIRouter(tags=["dashboard"], dependencies=[Depends(require_api_key)])


@router.get("/dashboard/stats", operation_id="getDashboardStats")
def stats(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    with sqlite_connection(settings.sqlite_path) as conn:
        schema = conn.execute(
            """SELECT COUNT(*) AS objects,
                      COALESCE(SUM(json_array_length(json_extract(details_json, '$.columns'))), 0) AS columns,
                      MAX(scanned_at) AS last_scan
               FROM schema_objects"""
        ).fetchone()
        definitions = conn.execute("SELECT COUNT(*) AS count FROM definitions").fetchone()
        queries = conn.execute(
            """SELECT COUNT(*) AS total,
                      COALESCE(SUM(CASE WHEN succeeded = 1 THEN 1 ELSE 0 END), 0) AS successful
               FROM query_audit"""
        ).fetchone()
    return {
        "schema_objects": schema["objects"],
        "schema_columns": schema["columns"],
        "last_schema_scan": schema["last_scan"],
        "definitions": definitions["count"],
        "queries": queries["total"],
        "successful_queries": queries["successful"],
        "sql_configured": settings.sql_configured,
    }


@router.get("/history", operation_id="getQueryHistory")
def history(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, object]:
    with sqlite_connection(request.app.state.settings.sqlite_path) as conn:
        total = conn.execute("SELECT COUNT(*) FROM query_audit").fetchone()[0]
        rows = conn.execute(
            """SELECT id, sql_text, succeeded, row_count, execution_time,
                      sources_json, error_text, created_at
               FROM query_audit ORDER BY id DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        ).fetchall()
    items = [
        {
            "id": row["id"], "sql": row["sql_text"], "succeeded": bool(row["succeeded"]),
            "row_count": row["row_count"], "execution_time": row["execution_time"],
            "sources": json.loads(row["sources_json"]), "error": row["error_text"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]
    return {"total": total, "items": items}
