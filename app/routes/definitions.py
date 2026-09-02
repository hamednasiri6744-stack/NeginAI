from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.definition_service import (
    create_definition, delete_definition, list_definitions, search_definitions, update_definition,
)
from app.models import DefinitionCreate, DefinitionOut, DefinitionUpdate
from app.routes.dependencies import require_api_key
from app.sql_guard import SqlSecurityError, validate_read_only_sql

router = APIRouter(prefix="/definitions", tags=["definitions"], dependencies=[Depends(require_api_key)])


def _validate_approved_sql(sql: str | None) -> None:
    if sql:
        try:
            validate_read_only_sql(sql)
        except SqlSecurityError as exc:
            raise HTTPException(status_code=400, detail=f"approved_sql is unsafe: {exc}") from exc


@router.get("", response_model=list[DefinitionOut], operation_id="listDefinitions")
def all_definitions(request: Request, limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0)):
    return list_definitions(request.app.state.settings, limit, offset)


@router.get("/search", response_model=list[DefinitionOut], operation_id="searchDefinitions")
def search(request: Request, q: str = Query(min_length=1, max_length=200), limit: int = Query(20, ge=1, le=100)):
    return search_definitions(request.app.state.settings, q, limit)


@router.post("", response_model=DefinitionOut, status_code=201, operation_id="createDefinition")
def create(payload: DefinitionCreate, request: Request):
    _validate_approved_sql(payload.approved_sql)
    return create_definition(request.app.state.settings, payload)


@router.put("/{definition_id}", response_model=DefinitionOut, operation_id="updateDefinition")
def update(definition_id: int, payload: DefinitionUpdate, request: Request):
    _validate_approved_sql(payload.approved_sql)
    result = update_definition(request.app.state.settings, definition_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Definition not found")
    return result


@router.delete("/{definition_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteDefinition")
def delete(definition_id: int, request: Request) -> Response:
    if not delete_definition(request.app.state.settings, definition_id):
        raise HTTPException(status_code=404, detail="Definition not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
