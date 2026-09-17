from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.automation_service import (
    AutomationError,
    acknowledge_notifications,
    create_automation,
    delete_automation,
    list_automations,
    list_notifications,
    mark_notifications_read,
    set_automation_active,
)
from app.models import AutomationCreateRequest, NotificationReadRequest
from app.routes.dependencies import require_user_or_local
from app.operational_notification_service import refresh_operational_alerts


router = APIRouter(
    prefix="/automations",
    tags=["automations"],
    dependencies=[Depends(require_user_or_local)],
)


def _username(request: Request) -> str:
    value = str(getattr(request.state, "username", "") or "").strip()
    if not value:
        raise HTTPException(status_code=401, detail="Authenticated user is required")
    return value


@router.get("", operation_id="listMyAutomations")
def list_my_automations(request: Request, include_inactive: bool = True):
    return {"automations": list_automations(
        request.app.state.settings, _username(request), include_inactive
    )}


@router.post("", status_code=201, operation_id="createMyAutomation")
def create_my_automation(payload: AutomationCreateRequest, request: Request):
    try:
        return create_automation(
            request.app.state.settings,
            _username(request),
            payload.title,
            payload.query_text,
            payload.schedule_kind,  # type: ignore[arg-type]
            payload.interval_minutes,
            payload.daily_time,
            payload.condition_text,
        )
    except AutomationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{automation_id}/pause", operation_id="pauseMyAutomation")
def pause_my_automation(automation_id: int, request: Request):
    try:
        return set_automation_active(
            request.app.state.settings, _username(request), automation_id, False
        )
    except AutomationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{automation_id}/resume", operation_id="resumeMyAutomation")
def resume_my_automation(automation_id: int, request: Request):
    try:
        return set_automation_active(
            request.app.state.settings, _username(request), automation_id, True
        )
    except AutomationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{automation_id}", status_code=204, operation_id="deleteMyAutomation")
def delete_my_automation(automation_id: int, request: Request):
    try:
        delete_automation(request.app.state.settings, _username(request), automation_id)
    except AutomationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)


@router.get("/notifications", operation_id="listMyAutomationNotifications")
def list_my_notifications(
    request: Request, unread_only: bool = False, limit: int = 20
):
    username = _username(request)
    try:
        refresh_operational_alerts(request.app.state.settings, username)
    except Exception:
        pass
    return {"notifications": list_notifications(
        request.app.state.settings, username, unread_only, max(1, min(limit, 100))
    )}


@router.post("/notifications/read", operation_id="markMyAutomationNotificationsRead")
def read_my_notifications(payload: NotificationReadRequest, request: Request):
    return {"updated": mark_notifications_read(
        request.app.state.settings, _username(request), payload.notification_ids
    )}


@router.post("/notifications/acknowledge", operation_id="acknowledgeMyOperationalNotifications")
def acknowledge_my_notifications(payload: NotificationReadRequest, request: Request):
    return {"updated": acknowledge_notifications(
        request.app.state.settings, _username(request), payload.notification_ids
    )}
