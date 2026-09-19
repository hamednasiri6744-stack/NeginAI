import asyncio
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from typing import AsyncIterator, Protocol
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.access_control import filter_schema_item, policy_for_user, response_scope_matches
from app.conversation_service import (
    conversation_messages,
    delete_conversation,
    ensure_conversation,
    get_conversation,
    list_conversations,
    update_conversation,
)
from app.database import record_chat_failure
from app.excel_service import build_report_workbook
from app.schema_service import get_schema_object, list_schema_catalog
from app.user_workspace_service import build_user_workspace
from app.models import (
    ChatRequest,
    ChatResponse,
    ConversationCreateRequest,
    ConversationUpdateRequest,
)
from app.routes.dependencies import require_user_or_local

router = APIRouter(prefix="/chat", tags=["assistant"], dependencies=[Depends(require_user_or_local)])


@dataclass(frozen=True)
class ModelResourcePolicy:
    """Fail-closed limits for calls that consume external model resources."""

    global_concurrency: int
    user_concurrency: int
    user_requests_per_minute: int
    user_daily_budget_units: int
    global_daily_budget_units: int
    max_request_budget_units: int


@dataclass(frozen=True)
class ModelResourceLease:
    identity: str


class ModelResourceLimitExceeded(RuntimeError):
    def __init__(self, detail: str, *, retry_after: int = 60) -> None:
        super().__init__(detail)
        self.detail = detail
        self.retry_after = retry_after


class ModelResourceBackend(Protocol):
    def acquire(
        self,
        identity: str,
        policy: ModelResourcePolicy,
        budget_units: int,
    ) -> ModelResourceLease: ...

    def release(self, lease: ModelResourceLease) -> None: ...


class InMemoryModelResourceBackend:
    """Single-process backend; replicas can inject a Redis implementation."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._global_in_flight = 0
        self._user_in_flight: dict[str, int] = defaultdict(int)
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._budget_day = ""
        self._global_budget = 0
        self._user_budget: dict[str, int] = defaultdict(int)

    def acquire(
        self,
        identity: str,
        policy: ModelResourcePolicy,
        budget_units: int,
    ) -> ModelResourceLease:
        now = time.time()
        today = datetime.now(timezone.utc).date().isoformat()
        with self._lock:
            if self._budget_day != today:
                self._budget_day = today
                self._global_budget = 0
                self._user_budget.clear()
            recent = self._requests[identity]
            while recent and recent[0] <= now - 60:
                recent.popleft()
            if budget_units <= 0 or budget_units > policy.max_request_budget_units:
                raise ModelResourceLimitExceeded("model request budget is outside the allowed range")
            if self._global_in_flight >= policy.global_concurrency:
                raise ModelResourceLimitExceeded("model service concurrency limit reached", retry_after=1)
            if self._user_in_flight[identity] >= policy.user_concurrency:
                raise ModelResourceLimitExceeded("user model concurrency limit reached", retry_after=1)
            if len(recent) >= policy.user_requests_per_minute:
                retry_after = max(1, int(60 - (now - recent[0])))
                raise ModelResourceLimitExceeded("user model request quota exceeded", retry_after=retry_after)
            if self._user_budget[identity] + budget_units > policy.user_daily_budget_units:
                raise ModelResourceLimitExceeded("user model daily budget exceeded", retry_after=3600)
            if self._global_budget + budget_units > policy.global_daily_budget_units:
                raise ModelResourceLimitExceeded("global model daily budget exceeded", retry_after=3600)
            recent.append(now)
            self._global_in_flight += 1
            self._user_in_flight[identity] += 1
            self._global_budget += budget_units
            self._user_budget[identity] += budget_units
        return ModelResourceLease(identity=identity)

    def release(self, lease: ModelResourceLease) -> None:
        with self._lock:
            self._global_in_flight = max(0, self._global_in_flight - 1)
            self._user_in_flight[lease.identity] = max(
                0, self._user_in_flight[lease.identity] - 1
            )


def _positive_environment_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"invalid model resource limit: {name}") from exc
    if value <= 0:
        raise RuntimeError(f"invalid model resource limit: {name}")
    return value


def model_resource_policy() -> ModelResourcePolicy:
    policy = ModelResourcePolicy(
        global_concurrency=_positive_environment_int("NEGIN_MODEL_GLOBAL_CONCURRENCY", 8),
        user_concurrency=_positive_environment_int("NEGIN_MODEL_USER_CONCURRENCY", 2),
        user_requests_per_minute=_positive_environment_int("NEGIN_MODEL_USER_RPM", 12),
        user_daily_budget_units=_positive_environment_int(
            "NEGIN_MODEL_USER_DAILY_BUDGET_UNITS", 500_000
        ),
        global_daily_budget_units=_positive_environment_int(
            "NEGIN_MODEL_GLOBAL_DAILY_BUDGET_UNITS", 20_000_000
        ),
        max_request_budget_units=_positive_environment_int(
            "NEGIN_MODEL_MAX_REQUEST_BUDGET_UNITS", 100_000
        ),
    )
    if policy.user_concurrency > policy.global_concurrency:
        raise RuntimeError("invalid model resource limits: user concurrency exceeds global concurrency")
    if policy.user_daily_budget_units > policy.global_daily_budget_units:
        raise RuntimeError("invalid model resource limits: user budget exceeds global budget")
    return policy


def estimate_model_budget_units(*, text_characters: int = 0, binary_bytes: int = 0) -> int:
    return max(
        1,
        1_000
        + (max(0, text_characters) + 3) // 4
        + (max(0, binary_bytes) + 511) // 512,
    )


def _model_resource_backend(request: Request) -> ModelResourceBackend:
    state = request.app.state
    if getattr(state, "_model_resource_backend_failed", False):
        raise RuntimeError("model resource backend requires operator recovery")
    externally_configured = getattr(state, "model_resource_backend", ...)
    if externally_configured is not ...:
        if externally_configured is None:
            raise RuntimeError("model resource backend is unavailable")
        return externally_configured
    backend = getattr(state, "_local_model_resource_backend", None)
    settings_identity = id(state.settings)
    if backend is None or getattr(state, "_local_model_resource_settings_identity", None) != settings_identity:
        backend = InMemoryModelResourceBackend()
        state._local_model_resource_backend = backend
        state._local_model_resource_settings_identity = settings_identity
    return backend


@asynccontextmanager
async def model_resource_lease(
    request: Request,
    budget_units: int,
) -> AsyncIterator[None]:
    try:
        policy = model_resource_policy()
        backend = _model_resource_backend(request)
        identity = str(getattr(request.state, "username", None) or "action-api-key")
        lease = backend.acquire(identity, policy, budget_units)
    except ModelResourceLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail=exc.detail,
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="model resource controls are unavailable",
        ) from exc
    renewal = getattr(backend, "renew", None)
    renewal_interval = getattr(backend, "renewal_interval_seconds", None)
    renewal_task: asyncio.Task[None] | None = None

    async def keep_lease_alive() -> None:
        while True:
            await asyncio.sleep(float(renewal_interval))
            try:
                await asyncio.to_thread(renewal, lease)
            except Exception:
                # Stop every subsequent admission immediately.  The current
                # provider call cannot always be cancelled safely from here,
                # but no new work may rely on a lost distributed lease.
                request.app.state._model_resource_backend_failed = True
                return

    if callable(renewal) and renewal_interval is not None:
        renewal_task = asyncio.create_task(keep_lease_alive())
    try:
        yield
    finally:
        if renewal_task is not None:
            renewal_task.cancel()
            try:
                await renewal_task
            except asyncio.CancelledError:
                pass
        try:
            backend.release(lease)
        except Exception:
            # A lost distributed lease can invalidate concurrency accounting.
            # Stop admitting model work until an operator repairs/resets it.
            request.app.state._model_resource_backend_failed = True


def _username(request: Request) -> str:
    return str(getattr(request.state, "username", None) or "action-api-key")


@router.get("/workspace", operation_id="getChatUserWorkspace")
def user_workspace(request: Request) -> dict[str, object]:
    """Return the trusted identity and access workspace for the signed-in chat user."""
    username = _username(request)
    policy = policy_for_user(request.app.state.settings, username)
    return build_user_workspace(request.app.state.settings, username, policy)


@router.get("/conversations", operation_id="listChatConversations")
def conversation_list(request: Request) -> dict[str, object]:
    return {
        "conversations": list_conversations(
            request.app.state.settings,
            _username(request),
        )
    }


@router.post("/conversations", operation_id="createChatConversation")
def conversation_create(
    payload: ConversationCreateRequest,
    request: Request,
) -> dict[str, object]:
    conversation_id = ensure_conversation(
        request.app.state.settings,
        _username(request),
        payload.conversation_id,
    )
    return get_conversation(request.app.state.settings, _username(request), conversation_id) or {}


@router.get("/conversations/{conversation_id}/messages", operation_id="getChatConversation")
def conversation_history(conversation_id: str, request: Request) -> dict[str, object]:
    items = conversation_messages(
        request.app.state.settings,
        _username(request),
        conversation_id,
    )
    if items is None:
        raise HTTPException(status_code=404, detail="گفت‌وگو پیدا نشد.")
    return {"conversation_id": conversation_id, "messages": items}


@router.patch("/conversations/{conversation_id}", operation_id="updateChatConversation")
def conversation_update(
    conversation_id: str,
    payload: ConversationUpdateRequest,
    request: Request,
) -> dict[str, object]:
    result = update_conversation(
        request.app.state.settings,
        _username(request),
        conversation_id,
        title=payload.title,
        pinned=payload.pinned,
    )
    if result is None:
        raise HTTPException(status_code=404, detail="گفت‌وگو پیدا نشد.")
    return result


@router.delete("/conversations/{conversation_id}", operation_id="deleteChatConversation")
def conversation_delete(conversation_id: str, request: Request) -> dict[str, bool]:
    removed = delete_conversation(
        request.app.state.settings,
        _username(request),
        conversation_id,
    )
    if not removed:
        raise HTTPException(status_code=404, detail="گفت‌وگو پیدا نشد.")
    return {"deleted": True}


@router.get("/schema-catalog", operation_id="listAssistantSchemaCatalog")
def schema_catalog(request: Request) -> dict[str, object]:
    """Expose the reviewed table inventory in the signed-in assistant UI."""
    policy = policy_for_user(request.app.state.settings, _username(request))
    items = []
    for item in list_schema_catalog(request.app.state.settings):
        visible = filter_schema_item(policy, item)
        if visible is None:
            continue
        catalog = dict(visible.get("catalog") or {})
        items.append({
            "schema": visible.get("schema"),
            "name": visible.get("name"),
            "type": visible.get("type"),
            "column_count": len(visible.get("columns") or []),
            "catalog": catalog,
        })
    return {"count": len(items), "items": items}


@router.get("/schema-catalog/object", operation_id="getAssistantSchemaCatalogObject")
def schema_catalog_object(
    request: Request,
    schema: str,
    name: str,
) -> dict[str, object]:
    policy = policy_for_user(request.app.state.settings, _username(request))
    item = get_schema_object(request.app.state.settings, schema, name)
    visible = filter_schema_item(policy, item) if item else None
    if visible is None:
        raise HTTPException(status_code=404, detail="جدول موردنظر در دسترس نیست.")
    return visible


@router.post("", response_model=ChatResponse, operation_id="chatWithNeginAI")
async def chat_endpoint(payload: ChatRequest, request: Request) -> dict[str, object]:
    from app.chat_service import chat

    resource_context = model_resource_lease(
        request,
        estimate_model_budget_units(
            text_characters=len(payload.message or "") + len(payload.attachment_context or "")
        ),
    )
    await resource_context.__aenter__()
    try:
        attachment_kwargs = {}
        if payload.attachment_context is not None:
            attachment_kwargs["attachment_context"] = payload.attachment_context
        if payload.attachment_name is not None:
            attachment_kwargs["attachment_name"] = payload.attachment_name
        if payload.seller_coaching_start:
            attachment_kwargs["seller_coaching_start"] = True
        if payload.seller_coaching_mode:
            attachment_kwargs["seller_coaching_mode"] = True
        if payload.day_route_mode:
            attachment_kwargs["day_route_mode"] = True
        if payload.day_route_id:
            attachment_kwargs["day_route_id"] = payload.day_route_id
        return await asyncio.to_thread(
            chat,
            request.app.state.settings,
            payload.message,
            payload.conversation_id,
            getattr(request.state, "username", None),
            **attachment_kwargs,
        )
    except Exception as exc:
        try:
            record_chat_failure(
                request.app.state.settings,
                payload.conversation_id,
                type(exc).__name__,
                str(exc),
            )
        except Exception:
            pass
        raise HTTPException(
            status_code=502,
            detail="پردازش درخواست ناموفق بود. جزئیات فنی در گزارش داخلی ثبت شد.",
        ) from exc
    finally:
        await resource_context.__aexit__(None, None, None)


@router.get("/latest/{conversation_id}", response_model=ChatResponse, operation_id="getLatestChatResponse")
def latest_chat_response(conversation_id: str, request: Request) -> dict[str, object]:
    from app.chat_service import latest_response

    username = _username(request)
    if username not in {"local", "action-api-key"} and get_conversation(
        request.app.state.settings,
        username,
        conversation_id,
    ) is None:
        raise HTTPException(status_code=404, detail="گفت‌وگو پیدا نشد.")
    result = latest_response(request.app.state.settings, conversation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="پاسخ هنوز آماده نشده است.")
    return result


@router.get("/conversations/{conversation_id}/export.xlsx", operation_id="exportChatReportExcel")
def export_chat_report_excel(conversation_id: str, request: Request) -> StreamingResponse:
    from app.chat_service import latest_response

    username = _username(request)
    conversation = get_conversation(
        request.app.state.settings,
        username,
        conversation_id,
    )
    if conversation is None and username not in {"local", "action-api-key"}:
        raise HTTPException(status_code=404, detail="گفت‌وگو پیدا نشد.")
    result = latest_response(request.app.state.settings, conversation_id)
    if result is None:
        raise HTTPException(status_code=404, detail="پاسخی برای ساخت فایل پیدا نشد.")
    policy = policy_for_user(request.app.state.settings, username)
    if not response_scope_matches(policy, result):
        raise HTTPException(
            status_code=403,
            detail="این گزارش با سطح دسترسی فعلی شما قابل دریافت نیست.",
        )
    columns = list(result.get("columns") or [])
    rows = list(result.get("rows") or [])
    if not columns:
        answer_lines = [
            line.strip()
            for line in str(result.get("answer") or "").splitlines()
            if line.strip()
        ]
        columns = ["گزارش"]
        rows = [[line] for line in answer_lines] or [["گزارش آماده شد."]]
    title = str((conversation or {}).get("title") or "گزارش نگین AI")
    content = build_report_workbook(
        columns,
        rows,
        title,
    )
    filename = quote(f"{title[:60]}.xlsx")
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )
