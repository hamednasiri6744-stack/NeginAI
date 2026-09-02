from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models import PushSubscriptionRequest, PushUnsubscribeRequest
from app.push_service import (
    delete_push_subscription,
    list_push_subscriptions,
    save_push_subscription,
    send_user_push,
    private_key_path,
    vapid_public_key,
)
from app.routes.dependencies import require_session_user


router = APIRouter(
    prefix="/push",
    tags=["push-notifications"],
    dependencies=[Depends(require_session_user)],
)


def _username(request: Request) -> str:
    return str(request.state.username)


@router.get("/status", operation_id="getPushStatus")
def push_status(request: Request):
    settings = request.app.state.settings
    subscriptions = list_push_subscriptions(settings, _username(request))
    return {
        "available": True,
        "public_key": vapid_public_key(private_key_path(settings)),
        "subscription_count": len(subscriptions),
    }


@router.post("/subscriptions", status_code=201, operation_id="subscribeToPush")
def subscribe(payload: PushSubscriptionRequest, request: Request):
    try:
        save_push_subscription(
            request.app.state.settings,
            _username(request),
            payload.model_dump(),
            request.headers.get("user-agent"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"subscribed": True}


@router.delete("/subscriptions", operation_id="unsubscribeFromPush")
def unsubscribe(payload: PushUnsubscribeRequest, request: Request):
    removed = delete_push_subscription(
        request.app.state.settings, _username(request), payload.endpoint
    )
    return {"subscribed": False, "removed": removed}


@router.post("/test", operation_id="testPushNotification")
def test_push(request: Request):
    result = send_user_push(
        request.app.state.settings,
        _username(request),
        "اعلان نگین پخش فعال شد",
        "از این پس گزارش‌های خودکار بدون نیاز به ارسال پیام نمایش داده می‌شوند.",
    )
    if result["delivered"] < 1:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The test notification could not be delivered",
        )
    return result
