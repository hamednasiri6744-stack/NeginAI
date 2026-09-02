import asyncio
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.access_control import filter_schema_item, policy_for_user, response_scope_matches
from app.chat_service import chat, latest_response
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


@router.get("/latest/{conversation_id}", response_model=ChatResponse, operation_id="getLatestChatResponse")
def latest_chat_response(conversation_id: str, request: Request) -> dict[str, object]:
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
