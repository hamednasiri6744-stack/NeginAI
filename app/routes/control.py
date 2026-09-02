from __future__ import annotations

from io import BytesIO
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from starlette.responses import StreamingResponse

from app.control_service import (
    ControlError,
    can_manage_control,
    control_snapshot,
    personnel_directory,
    sync_control_operations,
)
from app.excel_service import build_report_workbook
from app.routes.dependencies import require_session_user


class ControlOperation(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    entity: str = Field(min_length=1, max_length=50)
    action: str = Field(min_length=1, max_length=30)
    entity_id: str = Field(min_length=1, max_length=100)
    base_revision: int = Field(default=0, ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)


class ControlSyncRequest(BaseModel):
    operations: list[ControlOperation] = Field(min_length=1, max_length=100)


class ControlPersonnelExportRequest(BaseModel):
    column_keys: list[str] = Field(min_length=1, max_length=8)
    personnel_ids: list[int] = Field(default_factory=list, max_length=100_000)


router = APIRouter(
    prefix="/control/api",
    tags=["control"],
    dependencies=[Depends(require_session_user)],
)


def _manager(request: Request) -> str:
    username = str(getattr(request.state, "username", "") or "").strip()
    if not username or not can_manage_control(request.app.state.settings, username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="این بخش فقط برای مدیران دارای دسترسی کنترل مجاز است.",
        )
    return username


@router.get("/bootstrap", operation_id="getControlBootstrap")
def bootstrap(request: Request, response: Response) -> dict[str, Any]:
    username = _manager(request)
    response.headers["Cache-Control"] = "no-store"
    return control_snapshot(request.app.state.settings, username)


@router.get("/personnel-directory", operation_id="getControlPersonnelDirectory")
def directory(request: Request, response: Response) -> dict[str, Any]:
    _manager(request)
    response.headers["Cache-Control"] = "no-store"
    return personnel_directory(request.app.state.settings)


@router.post(
    "/personnel-directory/export.xlsx",
    operation_id="exportControlPersonnelDirectoryExcel",
)
def export_directory(
    payload: ControlPersonnelExportRequest, request: Request
) -> StreamingResponse:
    _manager(request)
    directory_data = personnel_directory(request.app.state.settings)
    metadata = {column["key"]: column for column in directory_data["columns"]}
    column_keys = list(dict.fromkeys(payload.column_keys))
    unknown = [key for key in column_keys if key not in metadata]
    if unknown:
        raise HTTPException(status_code=400, detail=f"ستون ناشناخته است: {unknown[0]}")
    selected_ids = set(payload.personnel_ids)
    selected_rows = [
        row
        for row in directory_data["rows"]
        if int(row["personnel_id"]) in selected_ids
    ]
    content = build_report_workbook(
        [str(metadata[key]["title"]) for key in column_keys],
        [[row.get(key) for key in column_keys] for row in selected_rows],
        "فهرست پرسنل ورانگر",
    )
    filename = quote("فهرست-پرسنل-ورانگر.xlsx")
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store",
        },
    )


@router.post("/sync", operation_id="syncControlOperations")
def sync(payload: ControlSyncRequest, request: Request, response: Response) -> dict[str, Any]:
    username = _manager(request)
    response.headers["Cache-Control"] = "no-store"
    try:
        return sync_control_operations(
            request.app.state.settings,
            username,
            [operation.model_dump() for operation in payload.operations],
        )
    except ControlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
