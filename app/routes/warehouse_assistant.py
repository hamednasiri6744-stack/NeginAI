from __future__ import annotations

import asyncio
import json
from html import escape
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field, StrictInt

from app.control_service import permission_keys_for_user
from app.excel_service import build_report_workbook
from app.organization_structure_service import require_admin
from app.routes.dependencies import require_session_user
from app.warehouse_table_layouts import list_layouts, save_layout, delete_layout
from app.warehouse_email import preorder_workbook, send_preorder_email, send_supplier_order_email
from app.warehouse_fulfillment import list_fulfillment_orders, receive_fulfillment
from app import warehouse_checkbar as checkbar
from app import warehouse_checkbar_image as checkbar_image
from app import warehouse_receipt_bridge as receipt_bridge
from app import warehouse_sms_settings as sms_settings
from app import warehouse_order_sms as order_sms
from app import warehouse_purchase_contracts as purchase_contracts
from app import warehouse_purchase_contract_discovery as purchase_contract_discovery
from app import warehouse_sale_price_contracts as sale_price_contracts
from app import warehouse_unbilled_receipts as unbilled_receipts
from app import warehouse_purchase_invoice_bridge as purchase_invoice_bridge
from app.warehouse_assistant_service import (
    INVENTORY_COLUMN_KEYS,
    TABLE_PREFERENCE_COLUMNS,
    WAREHOUSES,
    WarehouseAssistantError,
    automatic_preorder_text,
    automatic_refresh_status,
    build_suggestions,
    create_supplier_orders,
    delete_inventory_view,
    get_automatic_preorder,
    get_supplier_order,
    import_inventory_snapshot,
    latest_snapshot,
    list_auto_order_settings,
    list_automatic_preorders,
    list_inventory_information,
    list_inventory_views,
    list_ordering_catalog,
    list_supply_scope,
    list_supplier_orders,
    list_table_preferences,
    save_inventory_view,
    save_order_cycle_override,
    save_table_preference,
    save_auto_order_setting,
    save_supplier_supply_scope,
    save_supply_scope_item,
    supplier_order_text,
    sync_varanegar_snapshot,
    refresh_supply_scope_from_varanegar,
    preview_auto_orders,
    run_automatic_order_cycle,
    transition_automatic_preorder,
    transition_supplier_order,
    update_automatic_preorder_lines,
)


MAX_UPLOAD_BYTES = 120 * 1024 * 1024
ALLOWED_EXTENSIONS = {".xlsx", ".xlsm"}


class SupplierOrderLineRequest(BaseModel):
    product_code: str = Field(min_length=1, max_length=80)
    quantity: float = Field(gt=0, le=1_000_000_000)
    note: str = Field(default="", max_length=500)


class SupplierOrderCreateRequest(BaseModel):
    snapshot_id: int = Field(gt=0)
    warehouse: str = Field(pattern=r"^(karaj|tehran|gilan)$")
    lines: list[SupplierOrderLineRequest] = Field(min_length=1, max_length=500)
    note: str = Field(default="", max_length=1000)
    delivery_date: str = Field(default="", max_length=10)


class VaranegarSyncRequest(BaseModel):
    period_days: int = Field(default=60, ge=7, le=365)


class PreorderEmailRequest(BaseModel):
    expected_token: str = Field(pattern=r'^[a-f0-9]{64}$')


class OrderSmsLinkRequest(BaseModel):
    mobile: str = Field(min_length=10, max_length=30)
    confirmed: bool = False


class TableExcelRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    columns: list[str] = Field(min_length=1, max_length=100)
    rows: list[list[str | int | float | bool | None]] = Field(max_length=5000)


class FulfillmentLineRequest(BaseModel):
    product_code: str = Field(min_length=1, max_length=80)
    received_qty: float = Field(ge=0, le=1_000_000_000, allow_inf_nan=False)


class FulfillmentReceiptRequest(BaseModel):
    expected_revision: int = Field(ge=0)
    snapshot_id: int = Field(gt=0)
    inventory_reflected: bool
    reference: str = Field(min_length=1, max_length=200)
    lines: list[FulfillmentLineRequest] = Field(min_length=1, max_length=500)


class BalanceLineRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    product_code: str = Field(min_length=1, max_length=80)
    quantity: float = Field(gt=0, le=1_000_000_000, allow_inf_nan=False)


class BalanceRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    expected_revision: int = Field(ge=0)
    request_id: str = Field(min_length=8, max_length=100)
    reason: str = Field(default='', max_length=500)
    reopen: bool = False
    confirmed: bool = False
    lines: list[BalanceLineRequest] = Field(min_length=1, max_length=500)


class FinishDeliveryRequest(BaseModel):
    model_config = {'extra': 'forbid'}
    expected_revision: int = Field(ge=0)
    request_id: str = Field(min_length=8, max_length=100)
    confirmed: bool = False


class InventoryViewRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_default: bool = False
    visible_columns: list[str] = Field(min_length=1, max_length=len(INVENTORY_COLUMN_KEYS))
    filters: dict[str, str] = Field(default_factory=dict)


class InventoryOrderCycleRequest(BaseModel):
    warehouse: str = Field(pattern=r"^(karaj|tehran|gilan)$")
    product_code: str = Field(min_length=1, max_length=80)
    mode: str = Field(pattern=r"^(system|force_active|force_inactive)$")


class AutoOrderSettingRequest(BaseModel):
    enabled: bool = True
    reorder_coverage_days: int = Field(default=10, ge=0, le=180)
    target_days: int = Field(default=20, ge=1, le=180)
    minimum_cartons: int = Field(default=0, ge=0, le=1_000_000)
    contact_first_name: str = Field(default="", max_length=80)
    contact_last_name: str = Field(default="", max_length=100)
    contact_email: str = Field(default="", max_length=254)
    contact_mobile: str = Field(default="", max_length=30)


class TablePreferenceRequest(BaseModel):
    visible_columns: list[str] = Field(min_length=1, max_length=40)


class TableLayoutRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    is_default: bool = False
    column_order: list[str] = Field(min_length=1, max_length=50)
    visible_columns: list[str] = Field(min_length=1, max_length=50)
    filters: dict[str, str] = Field(default_factory=dict)
    widths: dict[str, int] = Field(default_factory=dict)


class AutomaticPreorderLineRequest(BaseModel):
    product_code: str = Field(min_length=1, max_length=80)
    cartons: int = Field(ge=0, le=1_000_000)


class AutomaticPreorderLinesRequest(BaseModel):
    lines: list[AutomaticPreorderLineRequest] = Field(min_length=1, max_length=500)
    expected_token: str | None = Field(default=None, max_length=64)
    delivery_date: str | None = Field(default=None, max_length=10)


class SupplyScopeRequest(BaseModel):
    enabled: bool


class SupplierSupplyScopeRequest(BaseModel):
    warehouse: str = Field(pattern=r"^(karaj|tehran|gilan)$")
    supplier: str = Field(min_length=1, max_length=200)
    enabled: bool

router = APIRouter(
    prefix="/warehouse-assistant/api",
    tags=["warehouse-assistant"],
    dependencies=[Depends(require_session_user)],
)

public_router = APIRouter(tags=["warehouse-order-download"])


def _username(request: Request) -> str:
    return str(getattr(request.state, "username", "") or "").strip()


def _is_admin(request: Request, username: str) -> bool:
    try:
        require_admin(request.app.state.settings, username)
        return True
    except PermissionError:
        return False


def _capabilities(request: Request, username: str) -> set[str]:
    if _is_admin(request, username):
        return {
            "warehouse.assistant.view",
            "warehouse.order.suggest",
            "warehouse.order.draft",
            "warehouse.receipt.transfer",
            "warehouse.data.refresh",
        }
    return set(permission_keys_for_user(request.app.state.settings, username))


def _require(request: Request, permission: str) -> str:
    username = _username(request)
    if permission not in _capabilities(request, username):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="برای استفاده از این بخش، مجوز مستقل دستیار انبار لازم است.",
        )
    return username


def _error(exc: WarehouseAssistantError) -> HTTPException:
    message = str(exc)
    if message.startswith(("اتصال", "خواندن")):
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif message.startswith("ابتدا"):
        code = status.HTTP_409_CONFLICT
    else:
        code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return HTTPException(status_code=code, detail=message)


def _require_sms_confirmation(request: Request, confirmed: bool) -> None:
    if not confirmed or request.headers.get("X-Warehouse-Sms") != "1":
        raise HTTPException(status_code=403, detail="ارسال پیامک را در فرم سفارش تأیید کنید.")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=403, detail="درخواست ارسال پیامک معتبر نیست.")


def _require_export_request(request: Request) -> None:
    if request.headers.get("X-Warehouse-Export") != "1":
        raise HTTPException(status_code=403, detail="درخواست خروجی اکسل معتبر نیست.")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(status_code=403, detail="درخواست خروجی اکسل معتبر نیست.")


@router.get("/bootstrap", operation_id="getWarehouseAssistantBootstrap")
def bootstrap(request: Request) -> dict[str, object]:
    username = _require(request, "warehouse.assistant.view")
    capabilities = _capabilities(request, username)
    return {
        "username": username,
        "sms_settings_admin": _is_admin(request, username),
        "capabilities": sorted(capabilities),
        "warehouses": [
            {
                "code": code,
                "name": config["name"],
                "varanegar_stock_code": config["stock_dc_code"],
            }
            for code, config in WAREHOUSES.items()
        ],
        "latest_snapshot": latest_snapshot(request.app.state.settings),
        "separated_from_assistant": True,
        "commit_enabled": False,
        "output_mode": "supplier_documents",
        "varanegar_integration": "not_applicable",
        "mode": "isolated_pilot",
        "inventory_source": "varanegar_read_only",
        "inventory_prices_supported": True,
        "purchase_contracts_supported": True,
        "sale_price_contracts_supported": True,
        "inventory_cycle_override_supported": True,
        "inventory_cycle_manual_exclusion_supported": True,
        "order_workflow_api_version": 1,
        "order_delivery_date_supported": True,
        "draft_editor_atomic_supported": True,
        "supplier_portal_publication_supported": True,
        "supplier_portal_shared_access_supported": True,
        "inventory_in_transit_supported": True,
        "preorder_catalog_supported": True,
        "checkbar_supported": True,
        "standalone_checkbar_supported": True,
        "checkbar_worksheet_workflow_supported": True,
        "delivery_completion_supported": True,
        "checkbar_receipt_bridge_supported": True,
    }


@router.post("/table-export.xlsx", operation_id="exportWarehouseVisibleTable")
async def export_visible_table(request: Request) -> StreamingResponse:
    _require(request, "warehouse.assistant.view")
    _require_export_request(request)
    raw = await request.body()
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="حجم جدول برای خروجی اکسل بیش از حد مجاز است.")
    try:
        payload = TableExcelRequest.model_validate_json(raw)
    except (ValueError, UnicodeError):
        raise HTTPException(status_code=422, detail="داده‌های جدول برای خروجی اکسل معتبر نیست.") from None
    columns = [str(value).strip()[:200] for value in payload.columns]
    if any(not value for value in columns):
        raise HTTPException(status_code=422, detail="عنوان ستون‌های خروجی باید مشخص باشد.")
    rows: list[list[object]] = []
    for row in payload.rows:
        if len(row) != len(columns):
            raise HTTPException(status_code=422, detail="تعداد ستون‌های ردیف خروجی یکسان نیست.")
        clean: list[object] = []
        for value in row:
            if isinstance(value, str):
                clean.append(value[:5000])
            else:
                clean.append(value)
        rows.append(clean)
    content = build_report_workbook(columns, rows, payload.title.strip())
    filename = quote(f"warehouse-{payload.title.strip()[:80]}.xlsx")
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


def _require_sms_admin(request: Request) -> None:
    _require(request, 'warehouse.assistant.view')
    if not _is_admin(request, _username(request)):
        raise HTTPException(status_code=403, detail='تنظیمات پیامک فقط در دسترس مدیر است.')


async def _purchase_payload(request):
    if request.headers.get('X-Warehouse-Settings') != '1':
        raise HTTPException(403, 'درخواست تغییر قرارداد معتبر نیست.')
    if request.headers.get('origin') and request.headers['origin'].rstrip('/') != str(request.base_url).rstrip('/'):
        raise HTTPException(403, 'درخواست تغییر قرارداد معتبر نیست.')
    raw=await request.body()
    if len(raw)>1000000:raise HTTPException(413,'حجم اطلاعات قرارداد بیش از حد مجاز است.')
    try:
        result=json.loads(raw)
        if not isinstance(result,dict):raise ValueError()
        return result
    except (ValueError,UnicodeError):raise HTTPException(422,'اطلاعات قرارداد معتبر نیست.') from None


@router.get('/unbilled-receipts', operation_id='listWarehouseUnbilledReceipts')
def get_unbilled_receipts(request: Request, year: int | None = Query(default=None, ge=1300, le=1500)):
    _require(request, 'warehouse.assistant.view')
    try:
        return unbilled_receipts.list_receipts(request.app.state.settings, year)
    except unbilled_receipts.ReceiptListError as exc:
        raise HTTPException(502, str(exc)) from None


@router.get('/purchase-contracts',operation_id='listWarehousePurchaseContracts')
def get_purchase_contracts(request: Request,stock_id: int=Query(default=1,gt=0)):
    _require(request,'warehouse.assistant.view')
    settings=request.app.state.settings
    purchase_contracts.seed_item_defaults(settings)
    try:return {'contracts':purchase_contracts.list_contracts(settings),'catalog':purchase_contracts.catalog(settings,stock_id)}
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/purchase-invoices/preview',operation_id='previewWarehouseMultiReceiptPurchaseInvoice')
async def purchase_invoice_multi_preview(request: Request):
    _require(request,'warehouse.assistant.view');payload=await _purchase_payload(request)
    try:return await asyncio.to_thread(purchase_invoice_bridge.prepare,request.app.state.settings,payload.get('receipt_ids'),payload)
    except purchase_invoice_bridge.InvoiceError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/purchase-invoices/transfer',operation_id='submitWarehouseMultiReceiptPurchaseInvoice')
async def purchase_invoice_multi_transfer(request: Request):
    _require(request,'warehouse.order.draft');actor=_require(request,'warehouse.receipt.transfer')
    payload=await _purchase_payload(request)
    try:return await asyncio.to_thread(purchase_invoice_bridge.commit,request.app.state.settings,actor,payload.get('receipt_ids'),payload)
    except purchase_invoice_bridge.InvoiceError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/purchase-invoices/{receipt_id}/preview',operation_id='previewWarehousePurchaseInvoice')
async def purchase_invoice_preview(receipt_id: int,request: Request):
    _require(request,'warehouse.assistant.view');payload=await _purchase_payload(request)
    try:return await asyncio.to_thread(purchase_invoice_bridge.prepare,request.app.state.settings,receipt_id,payload)
    except purchase_invoice_bridge.InvoiceError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/purchase-invoices/{receipt_id}/transfer',operation_id='submitWarehousePurchaseInvoice')
async def purchase_invoice_transfer(receipt_id: int,request: Request):
    _require(request,'warehouse.order.draft');actor=_require(request,'warehouse.receipt.transfer')
    payload=await _purchase_payload(request)
    try:return await asyncio.to_thread(purchase_invoice_bridge.commit,request.app.state.settings,actor,receipt_id,payload)
    except purchase_invoice_bridge.InvoiceError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/purchase-contracts/catalog/refresh',operation_id='refreshWarehousePurchaseCatalog')
async def refresh_purchase_catalog(request: Request):
    _require(request,'warehouse.data.refresh')
    await _purchase_payload(request)
    try:return await asyncio.to_thread(purchase_contracts.refresh_catalog,request.app.state.settings)
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.get('/purchase-contracts/selection',operation_id='selectWarehousePurchaseProducts')
def purchase_selection(request: Request,manufacturer_id: int|None=Query(default=None,gt=0),brand_id: int|None=Query(default=None,gt=0),group_id: int|None=Query(default=None,gt=0),supplier_id: int|None=Query(default=None,gt=0)):
    _require(request,'warehouse.assistant.view')
    try:return purchase_contracts.selection(request.app.state.settings,manufacturer_id,brand_id,group_id,supplier_id)
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/purchase-contracts/batch',operation_id='createWarehousePurchaseItemContracts')
async def purchase_batch(request: Request):
    actor=_require(request,'warehouse.order.draft');payload=await _purchase_payload(request)
    try:return purchase_contracts.save_batch(request.app.state.settings,actor,payload)
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/purchase-contracts/batch-edit',operation_id='editWarehousePurchaseItemContracts')
async def purchase_batch_edit(request: Request):
    actor=_require(request,'warehouse.order.draft');payload=await _purchase_payload(request)
    try:return purchase_contracts.update_item_batch(request.app.state.settings,actor,payload)
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.get('/purchase-contracts/products',operation_id='resolveWarehousePurchaseRules')
def get_purchase_products(request: Request,supplier_id: int=Query(gt=0),on_date: str=Query(min_length=10,max_length=10),search: str=Query(default='',max_length=200),offset: int=Query(default=0,ge=0),limit: int=Query(default=200,ge=1,le=500),stock_id: int|None=Query(default=None,gt=0),without_contract: bool=Query(default=False),supply_only: bool=Query(default=False),coverage: str=Query(default="all",pattern=r"^(all|covered|uncovered)$")):
    _require(request,'warehouse.assistant.view')
    try:
        if without_contract or supply_only:
            on_date=purchase_contracts.jalali_business_date()
            stock_id=stock_id or 1
        result=purchase_contracts.resolve_products(request.app.state.settings,supplier_id,on_date,stock_id=stock_id,include_prices=not (without_contract or supply_only),supply_only=supply_only)
        if supply_only:
            result['coverage_counts']={'all':len(result['items']),'covered':sum(r['contract'] is not None for r in result['items']),'uncovered':sum(r['contract'] is None for r in result['items'])}
        if without_contract or coverage=='uncovered':
            result['items']=[r for r in result['items'] if r['contract'] is None]
            result['uncovered_product_count']=len(result['items'])
        if coverage=='covered' and not without_contract:result['items']=[r for r in result['items'] if r['contract'] is not None]
        needle=purchase_contracts.text(search).casefold()
        rows=[r for r in result['items'] if not needle or needle in purchase_contracts.text(' '.join([r['product_code'],r['product_name'],r['brand']])).casefold()]
        return dict(result,items=rows[offset:offset+limit],total=len(rows),offset=offset)
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/purchase-contracts',operation_id='createWarehousePurchaseContract')
async def post_purchase_contract(request: Request):
    actor=_require(request,'warehouse.order.draft');payload=await _purchase_payload(request)
    try:return purchase_contracts.save_contract(request.app.state.settings,actor,payload)
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.put('/purchase-contracts/{contract_id}',operation_id='editWarehousePurchaseContract')
async def put_purchase_contract(contract_id: str,request: Request):
    actor=_require(request,'warehouse.order.draft');payload=await _purchase_payload(request)
    revision=payload.get('expected_revision')
    if type(revision) is not int or revision<1:raise HTTPException(422,'نسخهٔ قرارداد لازم است.')
    try:return purchase_contracts.save_contract(request.app.state.settings,actor,payload,contract_id,revision)
    except purchase_contracts.ContractError as exc:raise HTTPException(409 if 'هم‌زمان' in str(exc) else 422,str(exc)) from None


@router.put('/purchase-contracts/{contract_id}/members',operation_id='editWarehousePurchaseContractMembers')
async def put_purchase_members(contract_id: str,request: Request):
    actor=_require(request,'warehouse.order.draft');payload=await _purchase_payload(request)
    revision=payload.get('expected_revision')
    if type(revision) is not int or revision<1:raise HTTPException(422,'نسخهٔ قرارداد لازم است.')
    if set(payload)-{'expected_revision','product_codes','product_end_dates'}:raise HTTPException(422,'این مسیر فقط برای تغییر کالاهای قرارداد است.')
    try:return purchase_contracts.update_members(request.app.state.settings,actor,contract_id,revision,payload.get('product_codes'),payload.get('product_end_dates'))
    except purchase_contracts.ContractError as exc:raise HTTPException(409 if 'هم‌زمان' in str(exc) else 422,str(exc)) from None


@router.get('/purchase-contracts/{contract_id}/members/{product_code}/history',operation_id='warehousePurchaseMemberHistory')
def purchase_member_history(contract_id: str,product_code: str,request: Request):
    _require(request,'warehouse.assistant.view')
    from app.warehouse_purchase_membership import member_history
    return {'history':member_history(request.app.state.settings,contract_id,product_code)}


@router.put('/purchase-contracts/{contract_id}/end',operation_id='endWarehousePurchaseContract')
async def end_purchase_contract(contract_id: str,request: Request):
    actor=_require(request,'warehouse.order.draft');payload=await _purchase_payload(request)
    revision=payload.get('expected_revision')
    if type(revision) is not int or revision<1:raise HTTPException(422,'نسخهٔ قرارداد لازم است.')
    if set(payload)-{'expected_revision','end_date'}:raise HTTPException(422,'این مسیر فقط برای پایان قرارداد است.')
    try:return purchase_contracts.end_contract(request.app.state.settings,actor,contract_id,revision,payload.get('end_date'))
    except purchase_contracts.ContractError as exc:raise HTTPException(409 if 'هم‌زمان' in str(exc) else 422,str(exc)) from None


@router.post('/purchase-contracts/{contract_id}/archive',operation_id='archiveWarehousePurchaseContract')
async def archive_purchase_contract(contract_id: str,request: Request):
    actor=_require(request,'warehouse.order.draft');payload=await _purchase_payload(request)
    revision=payload.get('expected_revision')
    if type(revision) is not int or revision<1:raise HTTPException(422,'نسخهٔ قرارداد لازم است.')
    try:return purchase_contracts.archive(request.app.state.settings,actor,contract_id,revision,payload.get('confirmed'))
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.get('/purchase-contracts/{contract_id}/history',operation_id='warehousePurchaseContractHistory')
def purchase_history(contract_id: str,request: Request):
    _require(request,'warehouse.assistant.view')
    return {'history':purchase_contracts.history(request.app.state.settings,contract_id)}


@router.post('/purchase-contracts/preview',operation_id='previewWarehousePurchaseContract')
async def purchase_preview(request: Request):
    _require(request,'warehouse.assistant.view');payload=await _purchase_payload(request)
    try:
        settings=request.app.state.settings
        purchase_contracts.initialize(settings)
        with purchase_contracts.connect(settings) as c:
            rule=purchase_contracts._validate(payload.get('contract'),c)
            code=purchase_contracts.text(payload.get('product_code'))
            row=c.execute('SELECT payload FROM warehouse_purchase_catalog WHERE supplier_id=? AND product_code=?',(rule['supplier_id'],code)).fetchone()
            if not row:raise purchase_contracts.ContractError('کالای نمونه را از همین تأمین‌کننده انتخاب کنید.')
            item=json.loads(row[0])
            if (rule['scope']=='brand' and rule['brand_id']!=item['brand_id']) or (rule['scope']=='item' and rule['product_code']!=code) or (rule['scope']=='collection' and code not in rule['product_codes']):
                raise purchase_contracts.ContractError('کالای نمونه خارج از دامنهٔ این قرارداد است.')
            if item['tax_status']!='known':raise purchase_contracts.ContractError('گروه مالیاتی کالا نامشخص یا ناسازگار است؛ ابتدا اصلاح و به‌روزرسانی کنید.')
            if rule.get('stock_id') is not None and rule['stock_id']!=payload.get('stock_id'):
                raise purchase_contracts.ContractError('انبار محاسبهٔ نمونه باید با انبار قرارداد یکسان باشد.')
            price=payload.get('price')
            if rule['basis'] in ('manufacturer','consumer'):
                from app.warehouse_purchase_prices import resolve_source_prices,require_source_price
                on_date=purchase_contracts.clean_date(payload.get('on_date'))
                source=resolve_source_prices(settings,[item['goods_id']],on_date,payload.get('stock_id'))
                price=require_source_price(rule,item,source.get(item['goods_id']))
            result=purchase_contracts.calculate(rule,price=price,quantity=payload.get('quantity'),tax_rate=item['tax_rate'])
            return dict(result,tax_rate=item['tax_rate'],currency='IRR',rounding='ROUND_HALF_UP',preview_only=True)
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.post('/purchase-contracts/discovery',operation_id='discoverWarehousePurchaseContract')
async def discover_purchase_contract(request: Request):
    _require(request,'warehouse.data.refresh');payload=await _purchase_payload(request)
    try:
        supplier_id=int(payload.get('supplier_id',0))
        return await asyncio.to_thread(purchase_contract_discovery.discover,request.app.state.settings,
            supplier_id,payload.get('from_year'),payload.get('to_year'))
    except (TypeError,ValueError):raise HTTPException(422,'تأمین‌کننده برای کشف قرارداد معتبر نیست.') from None
    except purchase_contracts.ContractError as exc:raise HTTPException(422,str(exc)) from None


@router.get('/purchase-contracts/discovery/latest',operation_id='latestWarehousePurchaseContractDiscovery')
def latest_purchase_contract_discovery(request: Request,supplier_id: int=Query(gt=0)):
    _require(request,'warehouse.assistant.view')
    return {'discovery':purchase_contract_discovery.latest(request.app.state.settings,supplier_id)}


@router.get('/sale-price-contracts', operation_id='listWarehouseSalePriceContracts')
def get_sale_price_contracts(request: Request):
    _require(request, 'warehouse.assistant.view')
    return {'contracts': sale_price_contracts.list_contracts(request.app.state.settings),
            'catalog': sale_price_contracts.metadata(request.app.state.settings)}


@router.get('/sale-price-contracts/selection', operation_id='selectWarehouseSalePriceProducts')
def sale_price_selection(request: Request, manufacturer_id: int = Query(gt=0),
                         brand_id: int | None = Query(default=None, gt=0),
                         group_id: int | None = Query(default=None, gt=0)):
    _require(request, 'warehouse.assistant.view')
    try:
        return sale_price_contracts.selection(request.app.state.settings, manufacturer_id, brand_id, group_id)
    except sale_price_contracts.SalePriceError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get('/sale-price-contracts/products', operation_id='resolveWarehouseSalePriceRules')
def get_sale_price_products(request: Request, manufacturer_id: int = Query(gt=0),
                            warehouse_code: str = Query(min_length=1, max_length=20),
                            on_date: str = Query(min_length=10, max_length=10)):
    _require(request, 'warehouse.assistant.view')
    try:
        return sale_price_contracts.resolve_products(
            request.app.state.settings, manufacturer_id, warehouse_code, on_date
        )
    except sale_price_contracts.SalePriceError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post('/sale-price-contracts', operation_id='createWarehouseSalePriceContract')
async def post_sale_price_contract(request: Request):
    actor = _require(request, 'warehouse.order.draft')
    payload = await _purchase_payload(request)
    try:
        return sale_price_contracts.save_contract(request.app.state.settings, actor, payload)
    except sale_price_contracts.SalePriceError as exc:
        raise HTTPException(422, str(exc)) from None


@router.post('/sale-price-contracts/batch', operation_id='createWarehouseSalePriceItemContracts')
async def post_sale_price_contract_batch(request: Request):
    actor = _require(request, 'warehouse.order.draft')
    payload = await _purchase_payload(request)
    try:
        return sale_price_contracts.save_batch(request.app.state.settings, actor, payload)
    except sale_price_contracts.SalePriceError as exc:
        raise HTTPException(422, str(exc)) from None


@router.put('/sale-price-contracts/{contract_id}', operation_id='editWarehouseSalePriceContract')
async def put_sale_price_contract(contract_id: str, request: Request):
    actor = _require(request, 'warehouse.order.draft')
    payload = await _purchase_payload(request)
    revision = payload.get('expected_revision')
    if type(revision) is not int or revision < 1:
        raise HTTPException(422, 'نسخهٔ قرارداد لازم است.')
    try:
        return sale_price_contracts.save_contract(
            request.app.state.settings, actor, payload, contract_id, revision
        )
    except sale_price_contracts.SalePriceError as exc:
        raise HTTPException(409 if 'هم‌زمان' in str(exc) else 422, str(exc)) from None


@router.post('/sale-price-contracts/{contract_id}/archive', operation_id='archiveWarehouseSalePriceContract')
async def archive_sale_price_contract(contract_id: str, request: Request):
    actor = _require(request, 'warehouse.order.draft')
    payload = await _purchase_payload(request)
    revision = payload.get('expected_revision')
    if type(revision) is not int or revision < 1:
        raise HTTPException(422, 'نسخهٔ قرارداد لازم است.')
    try:
        return sale_price_contracts.archive(
            request.app.state.settings, actor, contract_id, revision, payload.get('confirmed')
        )
    except sale_price_contracts.SalePriceError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get('/sale-price-contracts/{contract_id}/history', operation_id='warehouseSalePriceContractHistory')
def sale_price_history(contract_id: str, request: Request):
    _require(request, 'warehouse.assistant.view')
    return {'history': sale_price_contracts.history(request.app.state.settings, contract_id)}


@router.post('/sale-price-contracts/preview', operation_id='previewWarehouseSalePriceContract')
async def sale_price_preview(request: Request):
    _require(request, 'warehouse.assistant.view')
    payload = await _purchase_payload(request)
    try:
        settings = request.app.state.settings
        sale_price_contracts.initialize(settings)
        with sale_price_contracts.connect(settings) as connection:
            rule = sale_price_contracts._validate(payload.get('contract'), connection)
            products = sale_price_contracts._catalog_products(connection, rule['manufacturer_id'])
            code = purchase_contracts.text(payload.get('product_code'))
            item = products.get(code)
            if not item:
                raise sale_price_contracts.SalePriceError('کالای نمونه متعلق به این تولیدکننده نیست.')
            if rule['scope'] == 'item' and rule['product_code'] != code:
                raise sale_price_contracts.SalePriceError('کالای نمونه خارج از دامنهٔ قرارداد است.')
            if item.get('tax_status') != 'known':
                raise sale_price_contracts.SalePriceError('نرخ مالیات کالا نامشخص یا ناسازگار است.')
            on_date = purchase_contracts.clean_date(payload.get('on_date'))
            if rule['start_date'] > on_date or (rule['end_date'] and rule['end_date'] < on_date):
                raise sale_price_contracts.SalePriceError('تاریخ نمونه خارج از بازهٔ اعتبار قرارداد است.')
            manufacturer_price = payload.get('manufacturer_price')
            source = 'manual_preview'
            if manufacturer_price in (None, ''):
                from app.warehouse_purchase_prices import resolve_source_prices, require_source_price
                prices = resolve_source_prices(settings, [item['goods_id']], on_date, rule['stock_id'])
                manufacturer_price = require_source_price(
                    {'basis': 'manufacturer', 'start_date': rule['start_date'], 'end_date': rule['end_date']},
                    item, prices.get(item['goods_id'])
                )
                source = 'erp_read_only'
            result = sale_price_contracts.calculate(rule, manufacturer_price, item['tax_rate'])
            return dict(result, tax_rate=item['tax_rate'], price_source=source,
                        order_type_id=rule['order_type_id'], order_type_name=rule['order_type_name'],
                        currency='IRR', rounding='ROUND_HALF_UP', preview_only=True, erp_write=False)
    except sale_price_contracts.SalePriceError as exc:
        raise HTTPException(422, str(exc)) from None


@router.get('/sms-settings', operation_id='getWarehouseSmsSettings')
def get_sms_settings(request: Request):
    _require_sms_admin(request)
    try:
        return JSONResponse(sms_settings.read_settings(), headers={'Cache-Control': 'no-store'})
    except sms_settings.SmsSettingsError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None


@router.put('/sms-settings', operation_id='saveWarehouseSmsSettings')
async def put_sms_settings(request: Request):
    _require_sms_admin(request)
    if request.headers.get('X-Warehouse-Settings') != '1':
        raise HTTPException(status_code=403, detail='درخواست ذخیرهٔ تنظیمات معتبر نیست.')
    if request.headers.get('origin') and request.headers['origin'].rstrip('/') != str(request.base_url).rstrip('/'):
        raise HTTPException(status_code=403, detail='درخواست ذخیرهٔ تنظیمات معتبر نیست.')
    raw = await request.body()
    if len(raw) > 4096:
        raise HTTPException(status_code=413, detail='حجم تنظیمات پیامک بیش از حد مجاز است.')
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise HTTPException(status_code=422, detail='تنظیمات پیامک معتبر نیست.') from None
    try:
        result = await asyncio.to_thread(sms_settings.save_settings, payload)
        return JSONResponse(result, headers={'Cache-Control': 'no-store'})
    except sms_settings.SmsSettingsError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


@router.post("/sync/varanegar", operation_id="syncWarehouseDataFromVaranegar")
async def sync_varanegar(
    payload: VaranegarSyncRequest, request: Request
) -> JSONResponse:
    username = _require(request, "warehouse.data.refresh")
    try:
        result = await asyncio.to_thread(
            sync_varanegar_snapshot,
            request.app.state.settings,
            username,
            period_days=payload.period_days,
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    result["varanegar_write"] = False
    result["sources"] = [
        "FRU.StockGoodsModel",
        "GNR.tblStockGoods",
        "SLE.tblOrderHdr",
        "SLE.tblFreeInvoiceHdr",
        "SLE.tblSaleHdr",
        "dbo.POrder2",
        "dbo.SalesReviewFast",
        "inv.vwGoodsCardex",
        "Inv.tblVocherHdr",
        "Inv.tblVocherItm",
        "GNR.tblSupplier",
    ]
    return JSONResponse(
        result,
        status_code=200 if result["duplicate"] else 201,
        headers={"Cache-Control": "no-store"},
    )


@router.get("/inventory", operation_id="getWarehouseInventoryInformation")
def inventory_information(
    request: Request,
    warehouse: str = Query(default="", pattern=r"^(|karaj|tehran|gilan)$"),
    search: str = Query(default="", max_length=200),
    filters: str = Query(default="", max_length=5000),
    limit: int = Query(default=250, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default='', max_length=80),
    sort_direction: str = Query(default='desc', pattern=r'^(asc|desc)$'),
) -> dict[str, object]:
    _require(request, "warehouse.assistant.view")
    try:
        column_filters = json.loads(filters) if filters else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="ساختار فیلترهای ستون‌ها معتبر نیست.") from exc
    if not isinstance(column_filters, dict):
        raise HTTPException(status_code=422, detail="ساختار فیلترهای ستون‌ها معتبر نیست.")
    try:
        return list_inventory_information(
            request.app.state.settings,
            warehouse=warehouse,
            search=search,
            column_filters=column_filters,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_direction=sort_direction,
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.put(
    "/inventory/order-cycle", operation_id="updateWarehouseInventoryOrderCycle"
)
def update_inventory_order_cycle(
    payload: InventoryOrderCycleRequest, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        return save_order_cycle_override(
            request.app.state.settings,
            username,
            **payload.model_dump(),
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get("/inventory/views", operation_id="listWarehouseInventoryViews")
def inventory_views(request: Request) -> dict[str, object]:
    username = _require(request, "warehouse.assistant.view")
    return {"views": list_inventory_views(request.app.state.settings, username)}


@router.get("/table-preferences", operation_id="listWarehouseTablePreferences")
def table_preferences(request: Request) -> dict[str, object]:
    username = _require(request, "warehouse.assistant.view")
    return {
        "preferences": list_table_preferences(request.app.state.settings, username),
        "available_columns": {
            key: list(columns) for key, columns in TABLE_PREFERENCE_COLUMNS.items()
        },
    }


@router.get("/table-layouts", operation_id="listWarehouseTableLayouts")
def table_layouts(request: Request):
    username = _require(request, "warehouse.assistant.view")
    return {"layouts": list_layouts(request.app.state.settings, username)}


@router.post("/table-layouts/{table_key}", operation_id="saveWarehouseTableLayout")
def store_table_layout(table_key: str, payload: TableLayoutRequest, request: Request):
    username = _require(request, "warehouse.assistant.view")
    try:
        layout, created = save_layout(request.app.state.settings, username, table_key,
                                      **payload.model_dump())
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return JSONResponse(layout, status_code=201 if created else 200)


@router.delete("/table-layouts/{table_key}/{identifier}", operation_id="deleteWarehouseTableLayout")
def remove_table_layout(table_key: str, identifier: str, request: Request):
    username = _require(request, "warehouse.assistant.view")
    if not delete_layout(request.app.state.settings, username, table_key, identifier):
        raise HTTPException(status_code=404, detail="طرح نمایش پیدا نشد.")
    return {"deleted": True}


@router.put(
    "/table-preferences/{table_key}",
    operation_id="saveWarehouseTablePreference",
)
def update_table_preference(
    table_key: str, payload: TablePreferenceRequest, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.assistant.view")
    try:
        return save_table_preference(
            request.app.state.settings, username, table_key, payload.visible_columns
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get("/catalog", operation_id="getWarehouseOrderingCatalog")
def ordering_catalog(
    request: Request,
    warehouse: str = Query(default="", pattern=r"^(|karaj|tehran|gilan)$"),
) -> dict[str, object]:
    _require(request, "warehouse.assistant.view")
    try:
        return list_ordering_catalog(request.app.state.settings, warehouse)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get("/supply-scope", operation_id="listWarehouseSupplyScope")
def supply_scope(request: Request) -> dict[str, object]:
    username = _require(request, "warehouse.assistant.view")
    try:
        return list_supply_scope(request.app.state.settings, username)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post(
    "/supply-scope/refresh", operation_id="refreshWarehouseSupplyScope"
)
async def refresh_supply_scope(request: Request) -> dict[str, object]:
    username = _require(request, "warehouse.data.refresh")
    try:
        return await asyncio.to_thread(
            refresh_supply_scope_from_varanegar,
            request.app.state.settings,
            username,
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.put(
    "/supply-scope/supplier", operation_id="updateWarehouseSupplierSupplyScope"
)
def update_supplier_supply_scope(
    payload: SupplierSupplyScopeRequest, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        return save_supplier_supply_scope(
            request.app.state.settings, username, **payload.model_dump()
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.put(
    "/supply-scope/{scope_id}", operation_id="updateWarehouseSupplyScopeItem"
)
def update_supply_scope_item(
    scope_id: int, payload: SupplyScopeRequest, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        return save_supply_scope_item(
            request.app.state.settings,
            username,
            scope_id,
            enabled=payload.enabled,
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get(
    "/automatic-settings", operation_id="listWarehouseAutomaticOrderSettings"
)
def automatic_order_settings(request: Request) -> dict[str, object]:
    username = _require(request, "warehouse.assistant.view")
    try:
        return list_auto_order_settings(request.app.state.settings, username)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.put(
    "/automatic-settings/{setting_id}",
    operation_id="updateWarehouseAutomaticOrderSetting",
)
def update_automatic_order_setting(
    setting_id: int, payload: AutoOrderSettingRequest, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        return save_auto_order_setting(
            request.app.state.settings,
            username,
            setting_id,
            **payload.model_dump(),
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get(
    "/automatic-settings/preview/{warehouse}",
    operation_id="previewWarehouseAutomaticOrders",
)
def automatic_order_preview(
    warehouse: str, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.suggest")
    try:
        return preview_auto_orders(request.app.state.settings, username, warehouse)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post(
    "/automatic-preorders/run",
    operation_id="prepareWarehouseAutomaticPreorders",
)
def run_automatic_preorders(request: Request) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        return run_automatic_order_cycle(
            request.app.state.settings,
            username,
            trigger="manual",
            refresh_inventory=True,
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get(
    "/automatic-preorders/refresh-status",
    operation_id="getWarehouseAutomaticRefreshStatus",
)
def automatic_preorder_refresh_status(request: Request) -> dict[str, object]:
    _require(request, "warehouse.assistant.view")
    return automatic_refresh_status(request.app.state.settings)


@router.get(
    "/automatic-preorders",
    operation_id="listWarehouseAutomaticPreorders",
)
def automatic_preorders(
    request: Request, limit: int = Query(default=200, ge=1, le=500)
) -> dict[str, object]:
    _require(request, "warehouse.order.draft")
    return {
        "preorders": list_automatic_preorders(
            request.app.state.settings, limit=limit
        ),
        "external_delivery_performed": False,
    }


@router.put(
    "/automatic-preorders/{preorder_id}/lines",
    operation_id="updateWarehouseAutomaticPreorderLines",
)
def update_automatic_preorder_lines_route(
    preorder_id: int, payload: AutomaticPreorderLinesRequest, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        preorder = update_automatic_preorder_lines(
            request.app.state.settings,
            username,
            preorder_id,
            [line.model_dump() for line in payload.lines],
            expected_token=payload.expected_token,
            delivery_date=payload.delivery_date,
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return {"preorder": preorder, "external_delivery_performed": False}


@router.get('/automatic-preorders/{preorder_id}/catalog', operation_id='getWarehousePreorderSupplierCatalog')
def preorder_supplier_catalog(preorder_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    from app.warehouse_preorder_catalog import get_preorder_catalog
    try:
        return get_preorder_catalog(request.app.state.settings, preorder_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get('/checkbars/context', operation_id='getWarehouseCheckbarContext')
def checkbar_context(request: Request, warehouse: str, supplier: str = ''):
    _require(request, 'warehouse.order.draft')
    try:
        return checkbar.context(request.app.state.settings, warehouse, supplier)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/checkbars/preview', operation_id='previewWarehouseCheckbar')
def checkbar_preview(payload: checkbar.Selection, request: Request):
    _require(request, 'warehouse.order.draft')
    try:
        return checkbar.prepare(request.app.state.settings, payload.warehouse, payload.supplier, payload.order_ids, payload.remaining_order_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/checkbars/image-draft', operation_id='extractWarehouseCheckbarImage')
async def checkbar_image_draft(request: Request, file: list[UploadFile] = File(...),
                               selection: str = Form(..., max_length=20000),
                               expected_token: str = Form(..., min_length=64, max_length=64)):
    _require(request, 'warehouse.order.draft')
    try:
        scope = checkbar.Selection.model_validate_json(selection)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail='انبار و تأمین‌کنندهٔ حواله را انتخاب کنید.') from exc
    try:
        try:
            from app.warehouse_checkbar_files import file_kind
            if not 1 <= len(file) <= checkbar_image.MAX_IMAGE_PAGES:
                raise WarehouseAssistantError('برای هر حواله از ۱ تا ۱۰ فایل انتخاب کنید.')
            contents = []
            total = 0
            for upload in file:
                content = await upload.read(checkbar_image.MAX_IMAGE_BYTES + 1)
                file_kind(content)
                total += len(content)
                if total > checkbar_image.MAX_TOTAL_IMAGE_BYTES:
                    raise WarehouseAssistantError('حجم مجموع فایل‌های حواله باید حداکثر ۳۰ مگابایت باشد.')
                contents.append(content)
        finally:
            for upload in file:
                await upload.close()
        source = await asyncio.to_thread(checkbar.prepare, request.app.state.settings,
                                         scope.warehouse, scope.supplier, scope.order_ids)
        if source['expected_token'] != expected_token:
            raise WarehouseAssistantError('اطلاعات کالا تغییر کرده است؛ فرم چک‌بار را دوباره باز کنید.')
        extraction = await asyncio.to_thread(checkbar_image.extract, request.app.state.settings, contents,
                                             filenames=[upload.filename for upload in file], supplier=scope.supplier)
        return checkbar_image.match_rows(extraction, source)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/checkbars', status_code=201, operation_id='issueWarehouseCheckbar')
def issue_checkbar(payload: checkbar.InspectionRequest, request: Request):
    username = _require(request, 'warehouse.order.draft')
    try:
        document=checkbar.issue(request.app.state.settings, username, payload.model_dump())
        return {'document':document,'varanegar_write':False,'receipt_recorded':bool(document.get('receipt_confirmed'))}
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get('/checkbars', operation_id='listWarehouseCheckbars')
def checkbar_documents(request: Request, include_deleted: bool = False):
    _require(request, 'warehouse.order.draft')
    return {'documents': checkbar.documents(request.app.state.settings, include_deleted)}


@router.get('/checkbars/{document_id}/edit-context', operation_id='getWarehouseCheckbarEditContext')
def checkbar_edit_context(document_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    try:
        return checkbar.edit_context(request.app.state.settings, document_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get('/checkbars/{document_id}/receipt-transfer', operation_id='getCheckbarReceiptTransfer')
def checkbar_receipt_status(document_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    try:
        return receipt_bridge.transfer_status(request.app.state.settings, document_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/checkbars/matching-preview', operation_id='previewCheckbarDraftMatching')
def checkbar_matching_preview(payload: checkbar.MatchingPreviewRequest, request: Request):
    _require(request,'warehouse.order.draft')
    try:
        return checkbar.matching_preview(request.app.state.settings,payload.model_dump())
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get('/checkbars/{document_id}/order-matching', operation_id='getCheckbarOrderMatching')
def checkbar_order_matching(document_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    try:
        return receipt_bridge.order_matching(request.app.state.settings, document_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/checkbars/{document_id}/receipt-preview', operation_id='previewCheckbarReceipt')
def checkbar_receipt_preview(document_id: int, payload: receipt_bridge.ReceiptRequest, request: Request):
    _require(request, 'warehouse.order.draft')
    username = _require(request, 'warehouse.receipt.transfer')
    try:
        return receipt_bridge.preview(request.app.state.settings, username, document_id, payload)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/checkbars/{document_id}/receipt-transfer', operation_id='submitCheckbarReceipt')
def checkbar_receipt_submit(document_id: int, payload: receipt_bridge.ReceiptRequest, request: Request):
    _require(request, 'warehouse.order.draft')
    username = _require(request, 'warehouse.receipt.transfer')
    try:
        return receipt_bridge.submit(request.app.state.settings, username, document_id, payload)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/checkbars/{document_id}/receipt-reconcile', operation_id='reconcileCheckbarReceipt')
def checkbar_receipt_reconcile(document_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    username = _require(request, 'warehouse.receipt.transfer')
    try:
        return receipt_bridge.submit(request.app.state.settings, username, document_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.put('/checkbars/{document_id}', operation_id='editWarehouseCheckbar')
def edit_checkbar(document_id: int, payload: checkbar.EditRequest, request: Request):
    username = _require(request, 'warehouse.order.draft')
    try:
        document=checkbar.edit_document(request.app.state.settings, username, document_id, payload.model_dump())
        return {'document':document,'varanegar_write':False,'receipt_recorded':bool(document.get('receipt_confirmed'))}
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.delete('/checkbars/{document_id}', operation_id='deleteWarehouseCheckbar')
def delete_checkbar(document_id: int, payload: checkbar.MutationRequest, request: Request):
    username = _require(request, 'warehouse.order.draft')
    try:
        return {'document': checkbar.delete_document(request.app.state.settings, username, document_id, payload.model_dump()),
                'varanegar_write': False, 'receipt_recorded': False}
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get('/checkbars/{document_id}/history', operation_id='getWarehouseCheckbarHistory')
def checkbar_history(document_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    try:
        return checkbar.document_history(request.app.state.settings, document_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get('/checkbars/{document_id}/revisions/{revision}/document.xlsx', operation_id='downloadWarehouseCheckbarRevision')
def checkbar_revision_excel(document_id: int, revision: int, request: Request):
    _require(request, 'warehouse.order.draft')
    try:
        content = checkbar.workbook(checkbar.historical_document(request.app.state.settings, document_id, revision))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return StreamingResponse(BytesIO(content), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="checkbar-{document_id}-v{revision}.xlsx"', 'Cache-Control': 'no-store'})


@router.get('/checkbars/{document_id}', operation_id='getWarehouseCheckbar')
def read_checkbar(document_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    try:
        return checkbar.get_document(request.app.state.settings, document_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get('/checkbars/{document_id}/document.xlsx', operation_id='downloadWarehouseCheckbar')
def checkbar_excel(document_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    try:
        content = checkbar.workbook(checkbar.get_document(request.app.state.settings, document_id))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return StreamingResponse(BytesIO(content), media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="checkbar-{document_id}.xlsx"', 'Cache-Control': 'no-store'})


@router.get('/checkbars/{document_id}/print', operation_id='printWarehouseCheckbar')
def print_checkbar(document_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    from app import warehouse_checkbar_print
    try:
        document = warehouse_checkbar_print.print_document(request.app.state.settings, document_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return HTMLResponse(warehouse_checkbar_print.render(document), headers={'Cache-Control': 'no-store'})


@router.post('/checkbars/{document_id}/approve-worksheet', operation_id='approveWarehouseCheckbarWorksheet')
def approve_checkbar_worksheet(document_id: int, payload: checkbar.MutationRequest, request: Request):
    username = _require(request, 'warehouse.order.draft')
    try:
        return {'document': checkbar.approve_worksheet(request.app.state.settings, username, document_id, payload.model_dump())}
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get('/fulfillment-orders', operation_id='listWarehouseFulfillmentOrders')
def fulfillment_orders(request: Request, include_completed: bool = False):
    _require(request, 'warehouse.order.draft')
    return {'orders': list_fulfillment_orders(request.app.state.settings, include_completed),
            'snapshot': latest_snapshot(request.app.state.settings)}


@router.post('/fulfillment-orders/{preorder_id}/receive', operation_id='receiveWarehouseFulfillmentOrder')
def receive_fulfillment_order(preorder_id: int, payload: FulfillmentReceiptRequest, request: Request):
    username = _require(request, 'warehouse.order.draft')
    try:
        result = receive_fulfillment(request.app.state.settings, username, preorder_id,
            **payload.model_dump())
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return {'fulfillment': result, 'varanegar_write': False, 'external_delivery_performed': False}


@router.post('/fulfillment-orders/{preorder_id}/balance', operation_id='adjustWarehouseOrderBalance')
def adjust_order_balance(preorder_id: int, payload: BalanceRequest, request: Request):
    username = _require(request, 'warehouse.order.draft')
    if not payload.confirmed:
        raise _error(WarehouseAssistantError('تأیید بستن یا بازگشایی مانده لازم است.'))
    from app.warehouse_order_receipts import adjust_balance
    try:
        result = adjust_balance(request.app.state.settings, username, preorder_id,
                                **payload.model_dump(exclude={'confirmed'}))
        return {'fulfillment': result, 'varanegar_write': False}
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/automatic-preorders/{preorder_id}/delete', operation_id='deleteWarehouseReadyOrder')
def delete_ready_order(preorder_id: int, request: Request):
    username = _require(request, 'warehouse.order.draft')
    try:
        preorder = transition_automatic_preorder(request.app.state.settings, username, preorder_id, 'delete')
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return {'preorder': preorder, 'external_delivery_performed': False}


def _automatic_preorder_for_document(
    request: Request, preorder_id: int
) -> dict[str, object]:
    _require(request, "warehouse.order.draft")
    try:
        return get_automatic_preorder(request.app.state.settings, preorder_id)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post(
    "/automatic-preorders/{preorder_id}/approve",
    operation_id="approveWarehouseAutomaticPreorder",
)
def approve_automatic_preorder(
    preorder_id: int, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        preorder = transition_automatic_preorder(
            request.app.state.settings, username, preorder_id, "approve"
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return {"preorder": preorder, "external_delivery_performed": False}


@router.post(
    "/automatic-preorders/{preorder_id}/revoke-approval",
    operation_id="revokeWarehouseAutomaticPreorderApproval",
)
def revoke_automatic_preorder_approval(preorder_id: int, request: Request) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        preorder = transition_automatic_preorder(
            request.app.state.settings, username, preorder_id, "revoke_approval"
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return {"preorder": preorder, "external_delivery_performed": False}


@router.get(
    "/automatic-preorders/{preorder_id}",
    operation_id="getWarehouseAutomaticPreorder",
)
def get_automatic_preorder_route(preorder_id: int, request: Request) -> dict[str, object]:
    return {"preorder": _automatic_preorder_for_document(request, preorder_id)}


@router.post(
    "/automatic-preorders/{preorder_id}/request-send",
    operation_id="requestSendWarehouseAutomaticPreorder",
)
def request_send_automatic_preorder(
    preorder_id: int, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        preorder = transition_automatic_preorder(
            request.app.state.settings, username, preorder_id, "request_send"
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return {
        "preorder": preorder,
        "send_status": "requested",
        "external_delivery_performed": False,
    }


@router.post('/automatic-preorders/{preorder_id}/send-email',
             operation_id='sendWarehouseAutomaticPreorderEmail')
def send_automatic_preorder_email(
    preorder_id: int, payload: PreorderEmailRequest, request: Request
) -> dict[str, object]:
    username = _require(request, 'warehouse.order.draft')
    try:
        return send_preorder_email(request.app.state.settings, username, preorder_id,
                                   payload.expected_token)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/fulfillment-orders/{preorder_id}/finish', operation_id='finishWarehouseDelivery')
def finish_order_delivery(preorder_id: int, payload: FinishDeliveryRequest, request: Request):
    username = _require(request, 'warehouse.order.draft')
    if not payload.confirmed:
        raise _error(WarehouseAssistantError('تأیید پایان تحویل لازم است.'))
    from app.warehouse_order_receipts import finish_delivery
    try:
        result = finish_delivery(request.app.state.settings, username, preorder_id,
                                 **payload.model_dump(exclude={'confirmed'}))
        return {'fulfillment': result, 'varanegar_write': False, 'external_delivery_performed': False}
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post(
    "/automatic-preorders/{preorder_id}/send-sms-link",
    operation_id="sendWarehouseAutomaticPreorderSmsLink",
)
def send_automatic_preorder_sms_link(
    preorder_id: int, payload: OrderSmsLinkRequest, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    _require_sms_confirmation(request, payload.confirmed)
    preorder = _automatic_preorder_for_document(request, preorder_id)
    if preorder["status"] not in ("approved", "send_requested") or not preorder.get("approved_at"):
        raise HTTPException(status_code=409, detail="ابتدا پیش‌سفارش را تأیید کنید.")
    try:
        return order_sms.send_document_link(
            request.app.state.settings, username,
            document_kind="automatic_preorder", document_id=preorder_id,
            order_number=str(preorder["preorder_number"]), supplier=str(preorder["supplier"]),
            mobile=payload.mobile,
            filename=f"automatic-preorder-{preorder['preorder_number']}.xlsx",
            content=preorder_workbook(preorder),
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get(
    "/automatic-preorders/{preorder_id}/document.txt",
    operation_id="downloadWarehouseAutomaticPreorderText",
)
def automatic_preorder_text_document(
    preorder_id: int, request: Request
) -> PlainTextResponse:
    preorder = _automatic_preorder_for_document(request, preorder_id)
    return PlainTextResponse(
        automatic_preorder_text(preorder),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="automatic-preorder-{preorder_id}.txt"'
            ),
            "Cache-Control": "no-store",
        },
    )


@router.get(
    "/automatic-preorders/{preorder_id}/document.xlsx",
    operation_id="downloadWarehouseAutomaticPreorderExcel",
)
def automatic_preorder_excel_document(
    preorder_id: int, request: Request
) -> StreamingResponse:
    preorder = _automatic_preorder_for_document(request, preorder_id)
    content = preorder_workbook(preorder)
    filename = quote(f"automatic-preorder-{preorder['preorder_number']}.xlsx")
    return StreamingResponse(
        BytesIO(content),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store",
        },
    )


@router.post("/inventory/views", operation_id="saveWarehouseInventoryView")
def save_inventory_view_route(
    payload: InventoryViewRequest, request: Request
) -> JSONResponse:
    username = _require(request, "warehouse.assistant.view")
    try:
        view, created = save_inventory_view(
            request.app.state.settings,
            username,
            name=payload.name,
            is_default=payload.is_default,
            visible_columns=payload.visible_columns,
            filters=payload.filters,
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return JSONResponse(view, status_code=201 if created else 200)


@router.delete(
    "/inventory/views/{view_id}", operation_id="deleteWarehouseInventoryView"
)
def delete_inventory_view_route(view_id: str, request: Request) -> dict[str, bool]:
    username = _require(request, "warehouse.assistant.view")
    if not delete_inventory_view(request.app.state.settings, username, view_id):
        raise HTTPException(status_code=404, detail="طرح نمایش مورد نظر پیدا نشد.")
    return {"deleted": True}


@router.post("/snapshots/import", operation_id="importWarehouseInventorySnapshot")
async def import_snapshot(
    request: Request, file: UploadFile = File(...)
) -> JSONResponse:
    username = _require(request, "warehouse.data.refresh")
    filename = Path(file.filename or "inventory.xlsx").name[:180]
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="فقط فایل XLSX یا XLSM پذیرفته می‌شود.")

    temp_path: Path | None = None
    try:
        size = 0
        with NamedTemporaryFile(delete=False, suffix=suffix) as handle:
            temp_path = Path(handle.name)
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="حجم فایل انبار باید حداکثر ۱۲۰ مگابایت باشد.",
                    )
                handle.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="فایل خالی است.")
        try:
            result = await asyncio.to_thread(
                import_inventory_snapshot,
                request.app.state.settings,
                temp_path,
                filename,
                username,
            )
        except WarehouseAssistantError as exc:
            raise _error(exc) from exc
        return JSONResponse(
            result,
            status_code=200 if result["duplicate"] else 201,
            headers={"Cache-Control": "no-store"},
        )
    finally:
        await file.close()
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


@router.get("/suggestions", operation_id="getWarehouseOrderSuggestions")
def suggestions(
    request: Request,
    warehouse: str = Query(pattern=r"^(karaj|tehran|gilan)$"),
    manufacturer: str = Query(default="", max_length=200),
    brand: str = Query(default="", max_length=200),
    search: str = Query(default="", max_length=200),
    reorder_coverage_days: int = Query(default=15, ge=0, le=180),
    target_days: int = Query(default=30, ge=1, le=180),
    safety_days: int = Query(default=0, ge=0, le=90),
    period_days: int = Query(default=60, ge=7, le=365),
    only_needed: bool = True,
    limit: int = Query(default=200, ge=1, le=500),
) -> dict[str, object]:
    _require(request, "warehouse.order.suggest")
    try:
        return build_suggestions(
            request.app.state.settings,
            warehouse=warehouse,
            manufacturer=manufacturer,
            brand=brand,
            search=search,
            reorder_coverage_days=reorder_coverage_days,
            target_days=target_days,
            safety_days=safety_days,
            period_days=period_days,
            only_needed=only_needed,
            limit=limit,
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post(
    "/supplier-orders", status_code=201, operation_id="createWarehouseSupplierOrders"
)
def create_orders(
    payload: SupplierOrderCreateRequest, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        orders = create_supplier_orders(
            request.app.state.settings,
            username,
            snapshot_id=payload.snapshot_id,
            warehouse=payload.warehouse,
            lines=[line.model_dump() for line in payload.lines],
            note=payload.note,
            delivery_date=payload.delivery_date,
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return {
        "orders": orders,
        "delivery_mode": "supplier_documents",
        "varanegar_write": False,
    }


@router.get("/supplier-orders", operation_id="listWarehouseSupplierOrders")
def orders(request: Request, limit: int = Query(default=50, ge=1, le=200), include_deleted: bool = False, stage: str = Query(default='', pattern=r'^(draft|sent|delivery)?$')) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    return {
        "orders": list_supplier_orders(
            request.app.state.settings,
            username,
            include_all=_is_admin(request, username),
            limit=limit,
            include_deleted=include_deleted,
            stage=stage,
        )
    }


class ManualOrderEditLine(BaseModel):
    product_code: str = Field(min_length=1, max_length=80)
    cartons: int = Field(ge=0, le=1_000_000, strict=True)


class ManualOrderEditRequest(BaseModel):
    expected_token: str = Field(min_length=64, max_length=64)
    lines: list[ManualOrderEditLine] = Field(min_length=1, max_length=500)
    delivery_date: str | None = Field(default=None, max_length=10)


class OrderDeliveryDateRequest(BaseModel):
    expected_token: str = Field(min_length=64, max_length=64)
    delivery_date: str = Field(min_length=10, max_length=10)


def _edit_order_delivery_date(kind, document_id, payload, request):
    from app.warehouse_order_delivery import update_delivery_date
    username = _require(request, 'warehouse.order.draft')
    try:
        return update_delivery_date(request.app.state.settings, username, kind, document_id,
                                    payload.delivery_date, expected_token=payload.expected_token,
                                    include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/supplier-orders/{order_id}/delivery-date', operation_id='editWarehouseManualDeliveryDate')
def edit_manual_delivery_date(order_id: int, payload: OrderDeliveryDateRequest, request: Request):
    return _edit_order_delivery_date('supplier_order', order_id, payload, request)


@router.post('/automatic-preorders/{preorder_id}/delivery-date', operation_id='editWarehouseSystemDeliveryDate')
def edit_system_delivery_date(preorder_id: int, payload: OrderDeliveryDateRequest, request: Request):
    return _edit_order_delivery_date('automatic_preorder', preorder_id, payload, request)


@router.get('/supplier-orders/{order_id}', operation_id='getWarehouseManualOrder')
def manual_order_detail(order_id: int, request: Request):
    return _order_for_document(request, order_id)


class RebalanceLine(BaseModel):
    product_code: str = Field(min_length=1, max_length=100)
    cartons: int = Field(strict=True, ge=1, le=1000000)


class RebalanceRequest(BaseModel):
    expected_token: str = Field(min_length=1, max_length=128)
    request_id: str = Field(min_length=1, max_length=100)
    lines: list[RebalanceLine] = Field(min_length=1, max_length=500)


@router.get('/interwarehouse/balance/{source}')
@router.get('/interwarehouse/balance/{source}/{destination}')
def warehouse_balance_proposals(source: str, request: Request, destination: str | None = None):
    from app.warehouse_balance_proposals import preview
    username = _require(request, 'warehouse.order.draft')
    try:
        return preview(request.app.state.settings, username, source, destination=destination, include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/interwarehouse/balance/{source}/accept')
@router.post('/interwarehouse/balance/{source}/{destination}/accept')
def warehouse_accept_balance(source: str, payload: RebalanceRequest, request: Request, destination: str | None = None):
    from app.warehouse_balance_proposals import accept
    username = _require(request, 'warehouse.order.draft')
    try:
        return accept(request.app.state.settings, username, source, [line.model_dump() for line in payload.lines],
            expected_token=payload.expected_token, request_id=payload.request_id, destination=destination, include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


class RebalanceReflection(BaseModel):
    snapshot_id: int = Field(strict=True, ge=1)
    source_document: str = Field(min_length=1, max_length=100)
    destination_document: str = Field(min_length=1, max_length=100)
    confirmed: bool = Field(strict=True)


class TransferDocumentRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=100)
    request_ids: list[StrictInt] = Field(min_length=1, max_length=500)


@router.post('/interwarehouse/documents')
def issue_transfer_documents(payload: TransferDocumentRequest, request: Request):
    from app.warehouse_transfer_documents import create_documents
    username = _require(request, 'warehouse.order.draft')
    try:
        return create_documents(request.app.state.settings, username, payload.request_ids,
            request_id=payload.request_id, include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.delete('/interwarehouse/requests/{request_id}')
def delete_pending_transfer(request_id: int, request: Request):
    from app.warehouse_transfer_documents import delete_pending
    username = _require(request, 'warehouse.order.draft')
    try:
        return delete_pending(request.app.state.settings, username, request_id, include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/interwarehouse/requests/{request_id}/revoke')
def revoke_pending_transfer(request_id: int, request: Request):
    from app.warehouse_transfer_documents import revoke_pending
    username = _require(request, 'warehouse.order.draft')
    try:
        return revoke_pending(request.app.state.settings, username, request_id, include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


class TransferPendingBatch(BaseModel):
    model_config = {'extra':'forbid'}
    request_ids: list[StrictInt] = Field(min_length=1,max_length=500)
    action: Literal['delete','revoke']


@router.post('/interwarehouse/requests/batch')
def mutate_transfer_pending_batch(payload: TransferPendingBatch, request: Request):
    from app.warehouse_transfer_documents import mutate_pending_batch
    username=_require(request,'warehouse.order.draft')
    try:
        return mutate_pending_batch(request.app.state.settings,username,payload.request_ids,
                                    action=payload.action,include_all=_is_admin(request,username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.delete('/interwarehouse/documents/{document_id}')
def delete_transfer_document(document_id: int, request: Request):
    from app.warehouse_transfer_documents import delete_document
    username = _require(request, 'warehouse.order.draft')
    try:
        return delete_document(request.app.state.settings, username, document_id, include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/interwarehouse/requests/{request_id}/reflect')
def reflect_rebalance(request_id: int, payload: RebalanceReflection, request: Request):
    from app.warehouse_rebalancing import reflect_in_stock
    username = _require(request, 'warehouse.receipt.transfer')
    _require(request, 'warehouse.order.draft')
    try:
        return reflect_in_stock(request.app.state.settings, username, request_id,
            **payload.model_dump(), include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


from app.warehouse_transfer_bridge import SubmitCredit


@router.get('/interwarehouse/documents/{document_id}/credit')
def transfer_credit_status(document_id: int, request: Request):
    from app.warehouse_transfer_bridge import status
    username=_require(request,'warehouse.order.draft')
    try:
        return status(request.app.state.settings,username,document_id,include_all=_is_admin(request,username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/interwarehouse/documents/{document_id}/credit/preview')
def preview_transfer_credit(document_id: int, request: Request):
    from app.warehouse_transfer_bridge import preview
    username=_require(request,'warehouse.order.draft')
    _require(request,'warehouse.receipt.transfer')
    try:
        return preview(request.app.state.settings,username,document_id,include_all=_is_admin(request,username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/interwarehouse/documents/{document_id}/credit/refresh')
def refresh_transfer_credit(document_id: int, request: Request):
    from app.warehouse_transfer_bridge import status
    username=_require(request,'warehouse.order.draft')
    try:
        return status(request.app.state.settings,username,document_id,
                      include_all=_is_admin(request,username),force=True)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/interwarehouse/documents/{document_id}/return-to-approved')
def recover_transfer_document(document_id: int, request: Request):
    from app.warehouse_transfer_recovery import recover_with_inventory_refresh
    username=_require(request,'warehouse.order.draft')
    _require(request,'warehouse.receipt.transfer')
    try:
        return recover_with_inventory_refresh(request.app.state.settings,username,document_id,
                                  include_all=_is_admin(request,username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/interwarehouse/documents/{document_id}/credit/submit')
def submit_transfer_credit(document_id: int, payload: SubmitCredit, request: Request):
    from app.warehouse_transfer_bridge import submit
    from app.warehouse_native_transit import refresh_after_post
    username=_require(request,'warehouse.order.draft')
    _require(request,'warehouse.receipt.transfer')
    try:
        result=submit(request.app.state.settings,username,document_id,payload,include_all=_is_admin(request,username))
        return refresh_after_post(request.app.state.settings,username,result)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/interwarehouse/documents/{document_id}/credit/retry')
def retry_transfer_credit(document_id: int, request: Request):
    from app.warehouse_transfer_bridge import retry
    from app.warehouse_native_transit import refresh_after_post
    username=_require(request,'warehouse.order.draft')
    _require(request,'warehouse.receipt.transfer')
    try:
        result=retry(request.app.state.settings,username,document_id,include_all=_is_admin(request,username))
        return refresh_after_post(request.app.state.settings,username,result)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get('/interwarehouse/{kind}/{order_id}/proposal')
def rebalance_proposal(kind: str, order_id: int, request: Request):
    _require(request, 'warehouse.order.draft')
    raise HTTPException(status_code=410, detail='پیشنهاد جابه‌جایی به بخش جابه‌جایی بین انبارها منتقل شده است؛ صفحه را بازخوانی کنید.')


@router.post('/interwarehouse/{kind}/{order_id}/accept')
def accept_rebalance(kind: str, order_id: int, payload: RebalanceRequest, request: Request):
    _require(request, 'warehouse.order.draft')
    raise HTTPException(status_code=410, detail='ثبت جابه‌جایی فقط از بخش جابه‌جایی بین انبارها انجام می‌شود؛ صفحه را بازخوانی کنید.')


@router.get('/interwarehouse')
def list_rebalance_requests(request: Request, refresh_erp: bool=False):
    from app import warehouse_rebalancing as rebalance
    from app.warehouse_transfer_lifecycle import sync
    username = _require(request, 'warehouse.order.draft')
    sync(request.app.state.settings,username,include_all=_is_admin(request,username),force=refresh_erp)
    return {'items': rebalance.list_requests(request.app.state.settings, username,
                                            include_all=_is_admin(request, username))}


@router.post('/supplier-orders/{order_id}/lines', operation_id='editWarehouseManualOrderLines')
def edit_manual_order(order_id: int, payload: ManualOrderEditRequest, request: Request):
    from app.warehouse_manual_order_edit import update_lines
    username = _require(request, 'warehouse.order.draft')
    try:
        return update_lines(request.app.state.settings, username, order_id,
                            [line.model_dump() for line in payload.lines],
                            expected_token=payload.expected_token, include_all=_is_admin(request, username),
                            delivery_date=payload.delivery_date)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/supplier-orders/{order_id}/approve', operation_id='approveWarehouseManualOrder')
def approve_manual_order(order_id: int, request: Request):
    username = _require(request, 'warehouse.order.draft')
    try:
        return transition_supplier_order(request.app.state.settings, username, order_id, 'approve',
                                         include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/supplier-orders/{order_id}/revoke-approval', operation_id='revokeWarehouseManualOrderApproval')
def revoke_manual_order_approval(order_id: int, request: Request):
    username = _require(request, 'warehouse.order.draft')
    try:
        return transition_supplier_order(request.app.state.settings, username, order_id, 'revoke_approval',
                                         include_all=_is_admin(request, username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post('/supplier-orders/{order_id}/send-email', operation_id='sendWarehouseManualOrderEmail')
def send_manual_order_email(order_id: int, payload: PreorderEmailRequest, request: Request):
    username = _require(request, 'warehouse.order.draft')
    _order_for_document(request, order_id)
    try:
        return send_supplier_order_email(request.app.state.settings, username, order_id, payload.expected_token)
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


class ManualOrderDeleteRequest(BaseModel):
    confirmed: bool = False


@router.delete('/supplier-orders/{order_id}', operation_id='deleteWarehouseManualOrder')
def delete_manual_order(order_id: int, payload: ManualOrderDeleteRequest, request: Request):
    username=_require(request,'warehouse.order.draft')
    if not payload.confirmed:
        raise HTTPException(status_code=400,detail='حذف سفارش را تأیید کنید.')
    from app.warehouse_assistant_service import delete_supplier_order
    try:
        return delete_supplier_order(request.app.state.settings,username,order_id,include_all=_is_admin(request,username))
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.post(
    "/supplier-orders/{order_id}/send-sms-link",
    operation_id="sendWarehouseSupplierOrderSmsLink",
)
def send_supplier_order_sms_link(
    order_id: int, payload: OrderSmsLinkRequest, request: Request
) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    _require_sms_confirmation(request, payload.confirmed)
    order = _order_for_document(request, order_id)
    if order.get("deleted") or order.get("status") == "cancelled":
        raise HTTPException(status_code=409, detail="برای سفارش حذف‌شده پیامک ارسال نمی‌شود.")
    if not order.get("is_approved"):
        raise HTTPException(status_code=409, detail="ابتدا سفارش دستی را تأیید کنید.")
    try:
        return order_sms.send_document_link(
            request.app.state.settings, username,
            document_kind="supplier_order", document_id=order_id,
            order_number=str(order["order_number"]), supplier=str(order["supplier"]),
            mobile=payload.mobile,
            filename=f"supplier-order-{order['order_number']}.xlsx",
            content=order_sms.supplier_order_workbook(order),
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


def _order_for_document(request: Request, order_id: int) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    try:
        return get_supplier_order(
            request.app.state.settings,
            order_id,
            username,
            include_all=_is_admin(request, username),
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc


@router.get(
    "/supplier-orders/{order_id}/document.txt",
    operation_id="downloadWarehouseSupplierOrderText",
)
def order_text_document(order_id: int, request: Request) -> PlainTextResponse:
    order = _order_for_document(request, order_id)
    return PlainTextResponse(
        supplier_order_text(order),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="supplier-order-{order_id}.txt"',
            "Cache-Control": "no-store",
        },
    )


@router.get(
    "/supplier-orders/{order_id}/document.xlsx",
    operation_id="downloadWarehouseSupplierOrderExcel",
)
def order_excel_document(order_id: int, request: Request) -> StreamingResponse:
    order = _order_for_document(request, order_id)
    content = order_sms.supplier_order_workbook(order)
    filename = quote(f"supplier-order-{order['order_number']}.xlsx")
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store",
        },
    )


@public_router.get(
    "/warehouse-download/{token}",
    operation_id="downloadWarehouseOrderFromSms",
    include_in_schema=False,
)
def download_order_from_sms(token: str, request: Request) -> HTMLResponse:
    document = order_sms.preview_download(request.app.state.settings, token)
    if document is None:
        raise HTTPException(status_code=404, detail="لینک سفارش معتبر نیست یا منقضی شده است.")
    rows = "".join(
        "<tr>"
        f"<td><strong>{escape(str(line['product_name']))}</strong>"
        f"<small>{escape(str(line['brand']))}</small></td>"
        f"<td class='code'>{escape(str(line['product_code']))}"
        f"<small>{escape(str(line['manufacturer_product_code']))}</small></td>"
        f"<td>{escape(str(line['cartons']))}</td>"
        f"<td>{escape(str(line['quantity']))}</td>"
        "</tr>"
        for line in document["lines"]
    )
    order_number = escape(str(document["order_number"]))
    supplier = escape(str(document["supplier"]))
    expires_at = escape(str(document["expires_at"]).replace("T", " ")[:16])
    file_url = f"/warehouse-download/{token}/file"
    html = f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>سفارش {order_number} | نگین پخش</title>
<style>
:root{{--ink:#15233a;--muted:#667085;--line:#e4e7ec;--brand:#155eef;--surface:#fff;--bg:#f4f7fb}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.65}}
.wrap{{width:min(980px,100%);margin:auto;padding:18px 14px 40px}}header{{background:linear-gradient(135deg,#0b3972,#155eef);color:white;border-radius:20px;padding:22px;box-shadow:0 14px 32px #155eef2b}}
.eyebrow{{margin:0 0 4px;opacity:.82;font-size:13px}}h1{{font-size:clamp(22px,6vw,34px);margin:0}}header p{{margin:7px 0 0;opacity:.92}}
.actions{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:16px 0}}.download{{display:inline-flex;align-items:center;justify-content:center;min-height:48px;padding:10px 20px;border-radius:12px;background:var(--brand);color:white;text-decoration:none;font-weight:700}}
.meta{{color:var(--muted);font-size:13px}}.card{{background:var(--surface);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 5px 18px #1018280a}}
.card h2{{font-size:17px;margin:0;padding:15px 16px;border-bottom:1px solid var(--line)}}.table-wrap{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%;min-width:650px}}th,td{{text-align:right;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}}th{{background:#f9fafb;color:#475467;font-size:13px;white-space:nowrap}}td small{{display:block;color:var(--muted);margin-top:2px}}.code{{direction:ltr;text-align:left;font-variant-numeric:tabular-nums}}tbody tr:last-child td{{border-bottom:0}}
@media(max-width:640px){{.wrap{{padding:10px 10px 30px}}header{{border-radius:15px;padding:18px}}.actions{{align-items:stretch}}.download{{width:100%}}}}
</style></head><body><main class="wrap">
<header><p class="eyebrow">نگین پخش · لیست سفارشات</p><h1>سفارش {order_number}</h1><p>تأمین‌کننده: {supplier}</p></header>
<section class="actions"><a class="download" href="{file_url}" download>دانلود فایل Excel سفارش</a><span class="meta">اعتبار تا {expires_at} UTC · {document['remaining_downloads']} بار دانلود باقی‌مانده</span></section>
<section class="card"><h2>اقلام سفارش ({len(document['lines'])} قلم)</h2><div class="table-wrap"><table>
<thead><tr><th>نام کالا</th><th>کد کالا / کد تولیدکننده</th><th>کارتن</th><th>تعداد</th></tr></thead><tbody>{rows}</tbody>
</table></div></section></main></body></html>"""
    return HTMLResponse(
        html,
        headers={"Cache-Control": "no-store, private", "Pragma": "no-cache",
                 "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff"},
    )


@public_router.get(
    "/warehouse-download/{token}/file",
    operation_id="downloadWarehouseOrderFileFromSms",
    include_in_schema=False,
)
def download_order_file_from_sms(token: str, request: Request) -> StreamingResponse:
    document = order_sms.consume_download(request.app.state.settings, token)
    if document is None:
        raise HTTPException(status_code=404, detail="لینک دانلود معتبر نیست یا منقضی شده است.")
    filename = quote(str(document["filename"]))
    return StreamingResponse(
        BytesIO(document["content"]), media_type=order_sms.XLSX_MEDIA_TYPE,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store, private", "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer", "X-Content-Type-Options": "nosniff",
        },
    )
