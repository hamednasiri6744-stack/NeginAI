from fastapi import APIRouter, Depends, HTTPException, Request

from app.access_control import (
    DataAccessDenied,
    authorize_catalogued_sql,
    policy_for_user,
)
from app.database import execute_query, record_audit
from app.models import SqlQueryRequest, SqlQueryResponse
from app.routes.dependencies import require_api_key
from app.sql_guard import SqlSecurityError, validate_read_only_sql

router = APIRouter(prefix="/sql", tags=["sql"], dependencies=[Depends(require_api_key)])


@router.post("/query", response_model=SqlQueryResponse, operation_id="executeReadOnlyQuery")
def query(payload: SqlQueryRequest, request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    try:
        validated = validate_read_only_sql(payload.sql)
        validated = authorize_catalogued_sql(
            settings,
            policy_for_user(settings, getattr(request.state, "username", None)),
            validated,
        )
    except SqlSecurityError as exc:
        record_audit(settings, payload.sql, False, [], error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DataAccessDenied as exc:
        record_audit(settings, payload.sql, False, [], error=str(exc))
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    try:
        return execute_query(settings, validated)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="SQL execution failed; see server audit log") from exc
