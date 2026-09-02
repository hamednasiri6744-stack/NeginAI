from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.control_service import permission_keys_for_user
from app.excel_service import build_report_workbook
from app.organization_structure_service import require_admin
from app.routes.dependencies import require_session_user
from app.warehouse_assistant_service import (
    WAREHOUSES,
    WarehouseAssistantError,
    build_suggestions,
    create_supplier_orders,
    get_supplier_order,
    import_inventory_snapshot,
    latest_snapshot,
    list_supplier_orders,
    supplier_order_text,
    sync_varanegar_snapshot,
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


class VaranegarSyncRequest(BaseModel):
    period_days: int = Field(default=60, ge=7, le=365)

router = APIRouter(
    prefix="/warehouse-assistant/api",
    tags=["warehouse-assistant"],
    dependencies=[Depends(require_session_user)],
)


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


@router.get("/bootstrap", operation_id="getWarehouseAssistantBootstrap")
def bootstrap(request: Request) -> dict[str, object]:
    username = _require(request, "warehouse.assistant.view")
    capabilities = _capabilities(request, username)
    return {
        "username": username,
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
    }


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
    result["sources"] = ["GNR.tblStockGoods", "dbo.SalesReviewFast"]
    return JSONResponse(
        result,
        status_code=200 if result["duplicate"] else 201,
        headers={"Cache-Control": "no-store"},
    )


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
    target_days: int = Query(default=30, ge=1, le=180),
    safety_days: int = Query(default=7, ge=0, le=90),
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
        )
    except WarehouseAssistantError as exc:
        raise _error(exc) from exc
    return {
        "orders": orders,
        "delivery_mode": "supplier_documents",
        "varanegar_write": False,
    }


@router.get("/supplier-orders", operation_id="listWarehouseSupplierOrders")
def orders(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> dict[str, object]:
    username = _require(request, "warehouse.order.draft")
    return {
        "orders": list_supplier_orders(
            request.app.state.settings,
            username,
            include_all=_is_admin(request, username),
            limit=limit,
        )
    }


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
    columns = [
        "شماره سفارش",
        "تأمین‌کننده",
        "انبار مقصد",
        "کد کالا",
        "نام کالا",
        "برند",
        "کارتن",
        "تعداد سفارش",
        "ضریب کارتن",
        "قیمت خرید",
        "ارزش تخمینی",
        "توضیحات قلم",
    ]
    rows = [
        [
            order["order_number"],
            order["supplier"],
            order["warehouse_name"],
            line["product_code"],
            line["product_name"],
            line["brand"],
            line["cartons"],
            line["order_quantity"],
            line["conversion_rate"],
            line["buy_price"],
            line["estimated_value"],
            line["note"],
        ]
        for line in order["lines"]
    ]
    content = build_report_workbook(
        columns,
        rows,
        f"سفارش خرید {order['order_number']} برای {order['supplier']}",
    )
    filename = quote(f"supplier-order-{order['order_number']}.xlsx")
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Cache-Control": "no-store",
        },
    )
