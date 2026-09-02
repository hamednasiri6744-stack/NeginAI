from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.routes.dependencies import require_api_key
from app.models import SchemaCatalogUpdate
from app.schema_catalog import sync_schema_catalog, translation_review, translation_stats, update_catalog_entry
from app.business_terms import expand_business_query
from app.schema_service import (
    get_schema_object, rebuild_schema_search_index, scan_schema, schema_stats,
    search_schema, summarize_schema_results,
)

router = APIRouter(prefix="/schema", tags=["schema"], dependencies=[Depends(require_api_key)])


@router.get("/stats", operation_id="getDatabaseSchemaStats")
def stats(request: Request) -> dict[str, object]:
    return schema_stats(request.app.state.settings)


@router.post("/scan", operation_id="scanDatabaseSchema")
def scan(request: Request) -> dict[str, object]:
    try:
        return {"status": "completed", **scan_schema(request.app.state.settings)}
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/search", operation_id="searchDatabaseSchema")
def search(request: Request, q: str = Query(min_length=1, max_length=200)) -> dict[str, object]:
    results = summarize_schema_results(search_schema(request.app.state.settings, q, limit=20), q)
    return {"query": q, "expanded_terms": expand_business_query(q), "count": len(results), "results": results}


@router.get("/object", operation_id="getDatabaseObject")
def detail(request: Request, schema: str = Query(min_length=1), name: str = Query(min_length=1)) -> dict[str, object]:
    result = get_schema_object(request.app.state.settings, schema, name)
    if result is None:
        raise HTTPException(status_code=404, detail="Schema object not found; run /schema/scan first")
    return result


@router.post("/catalog/sync", operation_id="syncSchemaCatalog")
def sync_catalog(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    return {**sync_schema_catalog(settings), "indexed_terms": rebuild_schema_search_index(settings)}


@router.get("/translations/stats", operation_id="getSchemaTranslationStats")
def catalog_translation_stats(request: Request) -> dict[str, int]:
    return translation_stats(request.app.state.settings)


@router.get("/translations/review", operation_id="getSchemaTranslationReview")
def catalog_translation_review(request: Request, limit: int = Query(default=200, ge=1, le=1000)) -> dict[str, object]:
    return {"items": translation_review(request.app.state.settings, limit)}


@router.put("/catalog/object", operation_id="updateSchemaCatalogObject")
def update_catalog(
    payload: SchemaCatalogUpdate,
    request: Request,
    schema: str = Query(min_length=1),
    name: str = Query(min_length=1),
) -> dict[str, object]:
    try:
        result = update_catalog_entry(
            request.app.state.settings, schema, name, payload.model_dump(exclude_none=True)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Schema object not found; run /schema/scan first")
    rebuild_schema_search_index(request.app.state.settings)
    return result
