from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.automation_service import list_notifications
from app.routes.dependencies import require_user_or_local


router = APIRouter(
    prefix="/seller-workspace/live-events",
    tags=["seller-workspace"],
    dependencies=[Depends(require_user_or_local)],
)


def _sse(event: str, payload: dict[str, object], event_id: int | None = None) -> str:
    lines: list[str] = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append("data: " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(lines) + "\n\n"
def _notification_signature(items: list[dict[str, object]]) -> tuple[tuple[object, ...], ...]:
    return tuple(
        (
            item.get("id"),
            item.get("read"),
            item.get("acknowledged"),
            item.get("severity"),
        )
        for item in items
    )


@router.get("", operation_id="streamSellerLiveEvents")
async def stream_live_events(request: Request) -> StreamingResponse:
    username = str(getattr(request.state, "username", "") or "").strip()
    settings = request.app.state.settings

    async def event_stream():
        sequence = 0
        last_signature: tuple[tuple[object, ...], ...] | None = None
        heartbeat = 0
        yield "retry: 5000\n\n"
        yield _sse(
            "connected",
            {
                "kind": "connected",
                "server_time": datetime.now(timezone.utc).isoformat(),
            },
        )
        while not await request.is_disconnected():
            try:
                notifications = await asyncio.to_thread(
                    list_notifications,
                    settings,
                    username,
                    False,
                    100,
                )
                signature = _notification_signature(notifications)
                if signature != last_signature:
                    sequence += 1
                    unread_count = sum(1 for item in notifications if not bool(item.get("read")))
                    attention_count = sum(
                        1
                        for item in notifications
                        if not bool(item.get("read"))
                        or (
                            bool(item.get("requires_ack"))
                            and not bool(item.get("acknowledged"))
                        )
                    )
                    yield _sse(
                        "notifications",
                        {
                            "kind": "notifications",
                            "count": len(notifications),
                            "unread_count": unread_count,
                            "attention_count": attention_count,
                            "latest_id": notifications[0].get("id") if notifications else None,
                            "server_time": datetime.now(timezone.utc).isoformat(),
                        },
                        event_id=sequence,
                    )
                    last_signature = signature
                heartbeat += 1
                if heartbeat >= 3:
                    yield ": keepalive\n\n"
                    heartbeat = 0
            except asyncio.CancelledError:
                raise
            except Exception:
                yield _sse(
                    "degraded",
                    {
                        "kind": "degraded",
                        "server_time": datetime.now(timezone.utc).isoformat(),
                    },
                )
            await asyncio.sleep(5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
