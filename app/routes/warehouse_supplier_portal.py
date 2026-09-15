from __future__ import annotations

import threading
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.config import RESOURCE_DIR
from app.routes.dependencies import require_session_user
from app.warehouse_assistant_service import WarehouseAssistantError
from app import warehouse_supplier_portal as portal

staff_router = APIRouter(
    prefix="/warehouse-assistant/api/supplier-portal",
    tags=["warehouse-supplier-portal-admin"],
    dependencies=[Depends(require_session_user)],
)
public_router = APIRouter(prefix="/supplier-portal/api", tags=["warehouse-supplier-portal"])
STATIC_DIR = RESOURCE_DIR / "app" / "static"
COOKIE = "negin_supplier_session"
_attempts: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class PasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=10, max_length=200)


class AccountRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    temporary_password: str = Field(default='1', min_length=1, max_length=200)
    supplier_name: str = Field(min_length=1, max_length=200)
    mobile: str = Field(default="", max_length=30)


class AssignmentRequest(BaseModel):
    expected_token: str | None = Field(default=None, min_length=64, max_length=64)
    document_kind: str = Field(pattern=r"^(supplier_order|automatic_preorder)$")
    document_id: int = Field(gt=0)
    requested_delivery_date: str = Field(min_length=8, max_length=10)
    portal_username: str = Field(default='',max_length=30)


class CartableRequest(BaseModel):
    name: str = Field(min_length=1,max_length=200)
    supplier_names: list[str] = Field(min_length=1,max_length=100)
    manager_account_id: int = Field(gt=0)


class AccessScope(BaseModel):
    supplier_name: str = Field(min_length=1,max_length=200)
    warehouse_code: str = Field(min_length=1,max_length=100)


class AccountAccessRequest(BaseModel):
    cartable_id: int = Field(gt=0)
    all_orders: bool = False
    scopes: list[AccessScope] = Field(default_factory=list,max_length=500)
    expected_revision: int = Field(ge=0)


class WithdrawRequest(BaseModel):
    expected_revision: int = Field(ge=0)
    confirmed: bool = False


class ResponseLine(BaseModel):
    product_code: str = Field(min_length=1, max_length=80)
    proposed_cartons: int = Field(ge=0, le=1_000_000)
    line_status: str = Field(pattern=r"^(confirmed|changed|unavailable)$")
    supplier_note: str = Field(default="", max_length=500)


class SupplierResponseRequest(BaseModel):
    expected_revision: int = Field(ge=0)
    proposed_delivery_date: str = Field(default="", max_length=10)
    supplier_comment: str = Field(default="", max_length=1000)
    submit: bool = False
    confirmation_mode: str = Field(default="auto", pattern=r"^(auto|confirm|request_change)$")
    lines: list[ResponseLine] = Field(min_length=1, max_length=500)


class DecisionRequest(BaseModel):
    decision: str = Field(pattern=r"^(accept|changes_requested|reject)$")
    expected_revision: int = Field(ge=0)
    manager_comment: str = Field(default="", max_length=1000)


class CommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)


class InvitationRequest(BaseModel):
    expected_token: str | None = Field(default=None, min_length=64, max_length=64)
    expected_revision: int | None = Field(default=None, ge=0)
    mobile: str = Field(default="", max_length=30)
    confirmed: bool = False


class EmailInvitationRequest(BaseModel):
    expected_token: str | None = Field(default=None, min_length=64, max_length=64)
    expected_revision: int | None = Field(default=None, ge=0)
    email: str = Field(default="", max_length=254)
    confirmed: bool = False


def _error(exc: WarehouseAssistantError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


def _staff(request: Request) -> str:
    username = str(getattr(request.state, "username", "") or "").strip()
    from app.routes.warehouse_assistant import _capabilities
    if "warehouse.order.draft" not in _capabilities(request, username):
        raise HTTPException(status_code=403, detail="مجوز مدیریت سفارش تأمین‌کننده لازم است.")
    return username


def _supplier(request: Request) -> dict:
    profile = portal.session_profile(request.app.state.settings, request.cookies.get(COOKIE, ""))
    if profile is None:
        raise HTTPException(status_code=401, detail="برای مشاهده کارتابل وارد شوید.")
    return profile


def _same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=403, detail="درخواست از مبدأ معتبر نیست.")


@public_router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response):
    _same_origin(request)
    client = request.client.host if request.client else "unknown"
    cutoff = time.time() - 300
    with _lock:
        _attempts[client] = [stamp for stamp in _attempts[client] if stamp > cutoff]
        if len(_attempts[client]) >= 8:
            raise HTTPException(status_code=429, detail="تعداد تلاش‌ها زیاد است؛ پنج دقیقه بعد امتحان کنید.")
    result = portal.authenticate(request.app.state.settings, payload.username, payload.password)
    if result is None:
        with _lock:
            _attempts[client].append(time.time())
        raise HTTPException(status_code=401, detail="نام کاربری یا رمز عبور اشتباه است.")
    token, profile = result
    with _lock:
        _attempts.pop(client, None)
    is_local = client in {"127.0.0.1", "::1", "testclient"}
    response.set_cookie(COOKIE, token, max_age=portal.SESSION_SECONDS, httponly=True,
                        secure=not is_local, samesite="strict", path="/supplier-portal")
    response.headers["Cache-Control"] = "no-store"
    return {"authenticated": True, **profile}


@public_router.get("/me")
def me(request: Request, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return _supplier(request)


@public_router.post("/change-password")
def change_password(payload: PasswordRequest, request: Request):
    _same_origin(request)
    account = _supplier(request)
    try:
        portal.change_password(request.app.state.settings, account["id"], payload.current_password, payload.new_password)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return {"changed": True}


@public_router.post("/logout")
def logout(request: Request, response: Response):
    _same_origin(request)
    portal.logout(request.app.state.settings, request.cookies.get(COOKIE, ""))
    response.delete_cookie(COOKIE, path="/supplier-portal")
    return {"authenticated": False}


@public_router.get("/orders")
def supplier_orders(request: Request, response: Response):
    account = _supplier(request)
    response.headers['Cache-Control']='no-store'
    # Do not hydrate full inventory snapshots just to show the order sidebar.
    return {'orders':portal.list_assignment_summaries(request.app.state.settings,account_id=account['id'])}


@public_router.get("/orders/{assignment_id}")
def supplier_order(assignment_id: int, request: Request, response: Response):
    account = _supplier(request)
    try:
        from app.warehouse_portal_publication import mark_viewed
        mark_viewed(request.app.state.settings,assignment_id,account_id=account['id'])
        response.headers['Cache-Control']='no-store'
        return portal.get_assignment(request.app.state.settings, assignment_id, account_id=account['id'], supplier_view=True)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@public_router.put("/orders/{assignment_id}/response")
def supplier_response(assignment_id: int, payload: SupplierResponseRequest, request: Request):
    _same_origin(request)
    account = _supplier(request)
    try:
        from app.warehouse_portal_publication import mark_viewed
        mark_viewed(request.app.state.settings,assignment_id,account_id=account['id'])
        return portal.save_response(request.app.state.settings, account, assignment_id,
            expected_revision=payload.expected_revision,
            proposed_delivery_date=payload.proposed_delivery_date,
            supplier_comment=payload.supplier_comment,
            lines=[line.model_dump() for line in payload.lines], submit=payload.submit,
            confirmation_mode=payload.confirmation_mode)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@public_router.post("/orders/{assignment_id}/comments")
def supplier_comment(assignment_id: int, payload: CommentRequest, request: Request):
    _same_origin(request)
    account = _supplier(request)
    try:
        from app.warehouse_portal_publication import mark_viewed
        mark_viewed(request.app.state.settings,assignment_id,account_id=account['id'])
        return portal.add_comment(request.app.state.settings, assignment_id, author_kind="supplier",
                                  author_name=account["supplier_name"], body=payload.body,
                                  account_id=account['id'])
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@public_router.get("/orders/{assignment_id}/document.xlsx")
def supplier_excel(assignment_id: int, request: Request):
    account = _supplier(request)
    try:
        from app.warehouse_portal_publication import mark_viewed
        mark_viewed(request.app.state.settings,assignment_id,account_id=account['id'])
        content = portal.response_workbook(request.app.state.settings, assignment_id,
                                           account_id=account['id'])
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return StreamingResponse(iter([content]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Cache-Control":"no-store", "Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'supplier-order-{assignment_id}.xlsx')}"})


@staff_router.get("/accounts")
def accounts(request: Request):
    _staff(request)
    return {"accounts": portal.list_accounts(request.app.state.settings)}


@staff_router.get('/cartables')
def cartables(request: Request):
    _staff(request)
    from app.warehouse_portal_access import list_cartables
    return list_cartables(request.app.state.settings)


@staff_router.get('/order-recipient')
def order_recipient(request: Request,document_kind: str,document_id: int):
    _staff(request)
    from app.warehouse_portal_access import default_login
    from app.warehouse_assistant_service import warehouse_connection
    try:
        portal._init(request.app.state.settings)
        doc=portal._document(request.app.state.settings,document_kind,document_id)
        with warehouse_connection(request.app.state.settings) as conn:
            login=default_login(conn,portal._supplier_key(doc['supplier']),doc['warehouse_code'])
            contact=conn.execute('SELECT contact_mobile FROM warehouse_supplier_auto_order_settings WHERE warehouse_code=? AND supplier=? COLLATE NOCASE',(doc['warehouse_code'],doc['supplier'])).fetchone()
            return {'username':login,'mobile':(contact['contact_mobile'] if contact else '') or login or doc.get('contact_mobile','')}
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.post('/cartables',status_code=201)
def cartable_create(payload: CartableRequest,request: Request):
    actor=_staff(request)
    from app.warehouse_portal_access import create_cartable
    try:
        return create_cartable(request.app.state.settings,actor,payload.name,payload.supplier_names,payload.manager_account_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.put('/accounts/{account_id}/access')
def account_access_update(account_id: int,payload: AccountAccessRequest,request: Request):
    actor=_staff(request)
    from app.warehouse_portal_access import set_account_access
    try:
        return set_account_access(request.app.state.settings,actor,account_id,payload.cartable_id,payload.all_orders,
                                  [s.model_dump() for s in payload.scopes],payload.expected_revision)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.post("/accounts", status_code=201)
def account_create(payload: AccountRequest, request: Request):
    username = _staff(request)
    try:
        from app.warehouse_order_sms import normalize_mobile
        login_mobile=normalize_mobile(payload.mobile or payload.username)
        return portal.create_account(request.app.state.settings, username, username=login_mobile,
                                     password=payload.temporary_password, supplier_name=payload.supplier_name,
                                     mobile=login_mobile)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.get("/orders")
def admin_orders(request: Request):
    _staff(request)
    return {"orders": portal.list_assignments(request.app.state.settings, staff=True)}


@staff_router.post("/orders/publish", status_code=201)
@staff_router.post("/orders", status_code=201)
def admin_order_create(payload: AssignmentRequest, request: Request):
    username = _staff(request)
    try:
        return portal.create_assignment(request.app.state.settings, username,
                                        document_kind=payload.document_kind, document_id=payload.document_id,
                                        requested_delivery_date=payload.requested_delivery_date, expected_token=payload.expected_token,
                                        publish=True,portal_username=payload.portal_username)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.post('/orders/{assignment_id}/withdraw')
def withdraw_order(assignment_id: int, payload: WithdrawRequest, request: Request):
    username=_staff(request)
    if not payload.confirmed:
        raise HTTPException(status_code=400,detail='تأیید برداشتن سفارش لازم است.')
    from app.warehouse_portal_publication import withdraw
    try:
        return withdraw(request.app.state.settings,username,assignment_id,payload.expected_revision)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.post("/orders/{assignment_id}/decision")
def admin_decision(assignment_id: int, payload: DecisionRequest, request: Request):
    username = _staff(request)
    try:
        return portal.decide(request.app.state.settings, username, assignment_id,
                             decision=payload.decision, expected_revision=payload.expected_revision,
                             manager_comment=payload.manager_comment)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.get('/orders/{assignment_id}')
def warehouse_order_review(assignment_id: int, request: Request, response: Response):
    _staff(request)
    response.headers['Cache-Control'] = 'no-store'
    try:
        # Staff review is not a supplier first-view event.
        return portal.get_assignment(request.app.state.settings, assignment_id, staff=True)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.post("/orders/{assignment_id}/comments")
def admin_comment(assignment_id: int, payload: CommentRequest, request: Request):
    username = _staff(request)
    try:
        return portal.add_comment(request.app.state.settings, assignment_id, author_kind="staff",
                                  author_name=username, body=payload.body)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.post("/orders/{assignment_id}/send-sms")
def admin_send_sms(assignment_id: int, payload: InvitationRequest, request: Request):
    username = _staff(request)
    if not payload.confirmed or request.headers.get("X-Warehouse-Supplier-Portal-Sms") != "1":
        raise HTTPException(status_code=400, detail="تأیید صریح ارسال پیامک لازم است.")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=403, detail="مبدأ درخواست معتبر نیست.")
    try:
        return portal.send_invitation(request.app.state.settings, username, assignment_id, payload.mobile,
                                      expected_token=payload.expected_token, expected_revision=payload.expected_revision)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.post("/orders/{assignment_id}/send-email")
def admin_send_email(assignment_id: int, payload: EmailInvitationRequest, request: Request):
    username = _staff(request)
    if not payload.confirmed or request.headers.get("X-Warehouse-Supplier-Portal-Email") != "1":
        raise HTTPException(status_code=400, detail="تأیید صریح ارسال ایمیل لازم است.")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=403, detail="مبدأ درخواست معتبر نیست.")
    try:
        return portal.send_email_invitation(
            request.app.state.settings, username, assignment_id, payload.email,
            expected_token=payload.expected_token, expected_revision=payload.expected_revision
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@staff_router.get("/orders/{assignment_id}/document.xlsx")
def admin_excel(assignment_id: int, request: Request):
    _staff(request)
    try:
        content = portal.response_workbook(request.app.state.settings, assignment_id, staff=True)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return StreamingResponse(iter([content]), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(f'supplier-response-{assignment_id}.xlsx')}"})


page_router = APIRouter(tags=["warehouse-supplier-portal-pages"])


@page_router.get("/supplier-portal", include_in_schema=False)
def portal_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "supplier-portal.html", headers={"Cache-Control": "no-store"})


@page_router.get("/supplier-portal-admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "supplier-portal-admin.html", headers={"Cache-Control": "no-store"})
