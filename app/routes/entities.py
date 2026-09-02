from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.entity_service import entity_stats, search_entities, sync_entities
from app.routes.dependencies import require_api_key

router = APIRouter(prefix="/entities", tags=["entities"], dependencies=[Depends(require_api_key)])


@router.get("/search", operation_id="resolveBusinessEntity")
def search(request: Request, q: str = Query(min_length=1, max_length=200), limit: int = Query(10, ge=1, le=50)):
    results = search_entities(request.app.state.settings, q, limit)
    return {"query": q, "count": len(results), "results": results}


@router.get("/stats", operation_id="getBusinessEntityStats")
def stats(request: Request):
    return entity_stats(request.app.state.settings)


@router.post("/sync", operation_id="syncBusinessEntities")
def sync(request: Request):
    try:
        return sync_entities(request.app.state.settings)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Entity synchronization failed") from exc
