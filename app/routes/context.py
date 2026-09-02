from fastapi import APIRouter, Depends, Request

from app.definition_service import search_definitions
from app.entity_service import ENTITY_GUIDANCE, search_entities
from app.models import ContextSearchRequest
from app.routes.dependencies import require_api_key
from app.schema_service import search_schema, summarize_schema_results

router = APIRouter(prefix="/context", tags=["context"], dependencies=[Depends(require_api_key)])


@router.post("/search", operation_id="searchBusinessAndTechnicalContext")
def search(payload: ContextSearchRequest, request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    schema_results = search_schema(settings, payload.question, min(payload.limit, 20))
    return {
        "question": payload.question,
        "definitions": search_definitions(settings, payload.question, payload.limit),
        "resolved_entities": search_entities(settings, payload.question, min(payload.limit, 10)),
        "entity_rules": ENTITY_GUIDANCE,
        "schema_objects": summarize_schema_results(schema_results, payload.question),
    }
