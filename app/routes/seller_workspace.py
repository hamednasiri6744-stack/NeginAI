from urllib.error import HTTPError, URLError

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.models import PrevisitCustomerUpdateDraftRequest, PrevisitDraftUpdateRequest, PrevisitOutcomeRequest, PrevisitPreviewRequest, PrevisitSavedRequestUpsert, PrevisitVisitStartRequest
from app.ngt_previsit_service import catalog_image, previsit_context, preview_previsit, validate_order_draft, warm_previsit_route
from app.previsit_service import PrevisitError, complete_visit, create_saved_request, get_order_completion_state, get_saved_request, get_visit_draft, list_route_saved_requests, list_saved_requests, start_visit, update_draft, update_saved_request
from app.varanegar_order_bridge import (
    VaranegarOrderBridgeError,
    VaranegarOrderBridgeUnavailable,
    submit_validated_order,
)
from app.routes.dependencies import require_user_or_local
from app.target_pulse_service import seller_target_pulse
from app.seller_workspace_service import (
    SellerDayRouteMismatch,
    SellerRouteNotFound,
    SellerWorkspaceError,
    seller_brands,
    seller_customer_profile_any_route,
    seller_customer_visit_workspace,
    seller_customer_open_invoices,
    seller_distribution_in_progress,
    seller_open_invoices,
    seller_returned_cheques,
    seller_voucher_return_report,
    seller_route_customers,
    seller_route_customers_basic,
    seller_route_customer_profile,
    seller_visit_policy,
    save_seller_route_customer_profile_draft,
    seller_route_map_leg,
    seller_route_map_plan,
    seller_routes,
)

router = APIRouter(
    prefix="/seller-workspace",
    tags=["seller workspace"],
    # Native clients may authenticate with a short-lived bearer token while the
    # web workspace continues to use its signed session cookie.
    dependencies=[Depends(require_user_or_local)],
)


def _username(request: Request) -> str:
    return str(request.state.username)


def _previsit_error(exc: PrevisitError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


def _ngt_timeout_error() -> HTTPException:
    return HTTPException(
        status_code=504,
        detail="پاسخ پایگاه داده NGT در زمان مقرر دریافت نشد؛ چند لحظه بعد دوباره تلاش کنید.",
    )


def _canonical_saved_request_payload(
    settings,
    username: str,
    visit_id: str,
    payload: PrevisitSavedRequestUpsert,
) -> PrevisitSavedRequestUpsert:
    # Browser-selected Saved Requests cross an HTTP trust boundary. Product
    # choices/quantities and allowed option names may come from the client, but
    # durable prices, discounts, totals and credit state must come from NGT.
    visit = get_visit_draft(settings, username, visit_id)
    route_id = str(visit["route_id"])
    customer_id = str(visit["customer_id"])
    context = previsit_context(
        settings,
        username,
        route_id,
        customer_id,
        limit=1000,
    )

    order_name = payload.order_type.strip()
    payment_name = payload.payment_type.strip()
    order_matches = [
        item for item in context.get("order_types") or []
        if str(item.get("name") or "").strip() == order_name
    ]
    payment_matches = [
        item for item in context.get("payment_types") or []
        if str(item.get("name") or "").strip() == payment_name
    ]
    if len(order_matches) != 1:
        raise PrevisitError("Selected order type is not uniquely available in the current NGT contract")
    if len(payment_matches) != 1:
        raise PrevisitError("Selected payment type is not uniquely available in the current NGT contract")

    warehouse_ref = (
        int(payload.warehouse_ref)
        if payload.warehouse_ref is not None
        else int(context.get("warehouse_selection", {}).get("default_ref") or 0) or None
    )
    official = preview_previsit(
        settings,
        username,
        PrevisitPreviewRequest(
            route_id=route_id,
            customer_id=customer_id,
            order_type_ref=int(order_matches[0]["id"]),
            payment_usance_ref=str(payment_matches[0]["id"]),
            warehouse_ref=warehouse_ref,
            lines=[
                {"product_id": str(line.product_id), "quantity": float(line.quantity)}
                for line in payload.lines
            ],
        ),
    )
    if not official.get("ok"):
        raise PrevisitError(str(official.get("message") or "Official NGT preview rejected this request"))
    credit = official.get("credit_control") or {}
    if credit.get("allowed") is False:
        raise PrevisitError(str(credit.get("message") or "NGT credit control rejected this request"))
    official = dict(official)
    official["_server_canonicalized"] = {
        "version": 1,
        "source": "NGT EVC presale",
    }

    products = {
        str(item.get("id")): item
        for item in context.get("products") or []
        if item.get("id") is not None
    }
    official_items: dict[str, list[dict]] = {}
    for item in official.get("items") or []:
        official_items.setdefault(str(item.get("product_id") or ""), []).append(item)

    canonical_lines = []
    for requested in payload.lines:
        product_id = str(requested.product_id)
        candidates = official_items.get(product_id) or []
        if not candidates:
            raise PrevisitError(f"Official NGT preview did not return product {product_id}")
        item = candidates.pop(0)
        product = products.get(product_id) or {}
        canonical_lines.append({
            "product_id": product_id,
            "quantity": float(item.get("quantity") or requested.quantity),
            "unit_price": float(item.get("unit_price") or 0),
            "discount_amount": float(item.get("discount_amount") or 0),
            "title": str(product.get("name") or requested.title or product_id),
        })

    official_order = official.get("order_type") or order_matches[0]
    official_payment = official.get("payment_type") or payment_matches[0]
    official_warehouse = official.get("warehouse") or {}
    canonical_warehouse_ref = (
        official_warehouse.get("ref")
        if isinstance(official_warehouse, dict)
        else None
    ) or warehouse_ref
    warehouse_name = (
        str(official_warehouse.get("name") or "")
        if isinstance(official_warehouse, dict)
        else ""
    )
    if not warehouse_name and canonical_warehouse_ref is not None:
        warehouse_name = next(
            (
                str(item.get("name") or "")
                for item in context.get("warehouses") or []
                if int(item.get("ref") or 0) == int(canonical_warehouse_ref)
            ),
            "",
        )

    return PrevisitSavedRequestUpsert(
        lines=canonical_lines,
        payment_type=str(official_payment.get("name") or payment_name),
        order_type=str(official_order.get("name") or order_name),
        warehouse_ref=int(canonical_warehouse_ref) if canonical_warehouse_ref is not None else None,
        warehouse_name=warehouse_name,
        preview=official,
    )


@router.get("/routes")
def get_my_routes(request: Request):
    try:
        return seller_routes(request.app.state.settings, _username(request))
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/target-pulse")
def get_my_target_pulse(request: Request):
    try:
        return seller_target_pulse(request.app.state.settings, _username(request))
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/brands")
def get_my_brands(request: Request):
    try:
        return seller_brands(request.app.state.settings, _username(request))
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/open-invoices")
def get_my_open_invoices(request: Request):
    try:
        return seller_open_invoices(request.app.state.settings, _username(request))
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/open-invoices/{customer_id}")
def get_my_customer_open_invoices(customer_id: str, request: Request):
    try:
        return seller_customer_open_invoices(request.app.state.settings, _username(request), customer_id)
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/returned-cheques")
def get_my_returned_cheques(request: Request):
    try:
        return seller_returned_cheques(request.app.state.settings, _username(request))
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/distribution-in-progress")
def get_my_distribution_in_progress(request: Request):
    try:
        return seller_distribution_in_progress(request.app.state.settings, _username(request))
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/voucher-return-report")
def get_my_voucher_return_report(request: Request):
    try:
        return seller_voucher_return_report(request.app.state.settings, _username(request))
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/routes/{path_id}/customers")
def get_my_route_customers(
    path_id: str,
    request: Request,
    detail: str = Query("basic", pattern="^(basic|full)$"),
):
    try:
        if detail == "full":
            return seller_route_customers(request.app.state.settings, _username(request), path_id)
        return seller_route_customers_basic(request.app.state.settings, _username(request), path_id)
    except SellerRouteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/routes/{path_id}/saved-requests")
def get_my_route_saved_requests(path_id: str, request: Request):
    try:
        # Validate that this route still belongs to the signed-in seller before
        # exposing locally saved work for the tour.
        seller_route_customers_basic(request.app.state.settings, _username(request), path_id)
        return {
            "requests": list_route_saved_requests(
                request.app.state.settings,
                _username(request),
                path_id,
            )
        }
    except SellerRouteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/customers/{customer_id}/profile")
def get_my_customer_profile_any_route(customer_id: str, request: Request):
    try:
        return seller_customer_profile_any_route(request.app.state.settings, _username(request), customer_id)
    except SellerRouteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/routes/{path_id}/customers/{customer_id}/profile")
def get_my_route_customer_profile(path_id: str, customer_id: str, request: Request):
    try:
        return seller_route_customer_profile(request.app.state.settings, _username(request), path_id, customer_id)
    except SellerRouteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/routes/{path_id}/customers/{customer_id}/visit-workspace")
def get_my_customer_visit_workspace(path_id: str, customer_id: str, request: Request):
    try:
        return seller_customer_visit_workspace(
            request.app.state.settings,
            _username(request),
            path_id,
            customer_id,
        )
    except SellerRouteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise _ngt_timeout_error() from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.put("/routes/{path_id}/customers/{customer_id}/profile-draft")
def save_my_route_customer_profile_draft(
    path_id: str,
    customer_id: str,
    payload: PrevisitCustomerUpdateDraftRequest,
    request: Request,
):
    try:
        return save_seller_route_customer_profile_draft(
            request.app.state.settings,
            _username(request),
            path_id,
            customer_id,
            payload.dict(),
        )
    except SellerRouteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/previsit/visits", status_code=201)
def start_my_previsit(payload: PrevisitVisitStartRequest, request: Request):
    try:
        return start_visit(request.app.state.settings, _username(request), payload)
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/previsit/policy")
def get_my_previsit_policy(
    request: Request,
    path_id: str = Query(min_length=1, max_length=100),
    customer_id: str = Query(min_length=1, max_length=100),
):
    try:
        return seller_visit_policy(
            request.app.state.settings,
            _username(request),
            path_id,
            customer_id,
        )
    except SellerRouteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TimeoutError as exc:
        raise _ngt_timeout_error() from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/previsit/context")
def get_my_previsit_context(
    request: Request,
    path_id: str = Query(min_length=1, max_length=100),
    customer_id: str = Query(min_length=1, max_length=100),
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=250, ge=1, le=1000),
):
    try:
        result = previsit_context(
            request.app.state.settings,
            _username(request),
            path_id,
            customer_id,
            search=search,
            limit=limit,
        )
        # Bridge-only values must never be trusted or changed by the browser.
        result.pop("_bridge", None)
        return result
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc
    except TimeoutError as exc:
        raise _ngt_timeout_error() from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/previsit/browse-context")
def get_my_previsit_browse_context(
    request: Request,
    path_id: str = Query(min_length=1, max_length=100),
    customer_id: str = Query(min_length=1, max_length=100),
    search: str = Query(default="", max_length=100),
    limit: int = Query(default=250, ge=1, le=1000),
):
    try:
        result = previsit_context(
            request.app.state.settings,
            _username(request),
            path_id,
            customer_id,
            search=search,
            limit=limit,
            require_day_route=False,
        )
        result.pop("_bridge", None)
        result["browse_only"] = True
        return result
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc
    except TimeoutError as exc:
        raise _ngt_timeout_error() from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/previsit/catalog-images/{catalog_id}/{image_name}")
def get_previsit_catalog_image(
    catalog_id: str,
    image_name: str,
    request: Request,
    size: str = Query(default="thumb", max_length=12),
):
    try:
        content, content_type = catalog_image(
            request.app.state.settings,
            catalog_id,
            image_name,
            size,
        )
        return Response(
            content=content,
            media_type=content_type,
            headers={"Cache-Control": "private, max-age=86400"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (HTTPError, URLError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="تصویر کاتالوگ دریافت نشد") from exc


@router.post("/previsit/warmup")
def warm_my_previsit_route(
    request: Request,
    path_id: str = Query(min_length=1, max_length=100),
):
    try:
        return warm_previsit_route(
            request.app.state.settings,
            _username(request),
            path_id,
        )
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc
    except TimeoutError as exc:
        raise _ngt_timeout_error() from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/previsit/preview")
def preview_my_previsit(payload: PrevisitPreviewRequest, request: Request):
    try:
        return preview_previsit(request.app.state.settings, _username(request), payload)
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc
    except TimeoutError as exc:
        raise _ngt_timeout_error() from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/previsit/visits/{visit_id}")
def get_my_previsit(visit_id: str, request: Request):
    try:
        return get_visit_draft(request.app.state.settings, _username(request), visit_id)
    except PrevisitError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/previsit/visits/{visit_id}/draft")
def save_my_previsit_draft(visit_id: str, payload: PrevisitDraftUpdateRequest, request: Request):
    try:
        return update_draft(request.app.state.settings, _username(request), visit_id, payload)
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc


@router.get("/previsit/visits/{visit_id}/saved-requests")
def list_my_saved_previsit_requests(visit_id: str, request: Request):
    try:
        return {"requests": list_saved_requests(request.app.state.settings, _username(request), visit_id)}
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc


@router.post("/previsit/visits/{visit_id}/saved-requests")
def create_my_saved_previsit_request(
    visit_id: str, payload: PrevisitSavedRequestUpsert, request: Request,
):
    try:
        settings = request.app.state.settings
        username = _username(request)
        canonical = _canonical_saved_request_payload(settings, username, visit_id, payload)
        return create_saved_request(settings, username, visit_id, canonical)
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc
    except TimeoutError as exc:
        raise _ngt_timeout_error() from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/previsit/visits/{visit_id}/saved-requests/{request_id}")
def get_my_saved_previsit_request(visit_id: str, request_id: str, request: Request):
    try:
        return get_saved_request(request.app.state.settings, _username(request), visit_id, request_id)
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc


@router.put("/previsit/visits/{visit_id}/saved-requests/{request_id}")
def update_my_saved_previsit_request(
    visit_id: str, request_id: str, payload: PrevisitSavedRequestUpsert, request: Request,
):
    try:
        settings = request.app.state.settings
        username = _username(request)
        canonical = _canonical_saved_request_payload(settings, username, visit_id, payload)
        return update_saved_request(settings, username, visit_id, request_id, canonical)
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc
    except TimeoutError as exc:
        raise _ngt_timeout_error() from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/previsit/visits/{visit_id}/complete")
def complete_my_previsit(visit_id: str, payload: PrevisitOutcomeRequest, request: Request):
    try:
        settings = request.app.state.settings
        username = _username(request)
        is_order = payload.outcome == "order"
        bridge_order = is_order and settings.varanegar_order_bridge_enabled
        completion_state = (
            get_order_completion_state(settings, username, visit_id) if is_order else None
        )
        if bridge_order and completion_state is None:
            # Preserve the bridge's strict visit/draft ownership check.
            get_visit_draft(settings, username, visit_id)
        if (
            is_order
            and completion_state is not None
            and not completion_state["line_count"]
            and completion_state["saved_request_count"]
        ):
            # Saved requests persisted before the server-canonicalization boundary
            # are upgraded once before completion. New requests carry a server
            # marker and do not incur another EVC calculation here.
            for saved in list_saved_requests(settings, username, visit_id):
                marker = (saved.get("preview") or {}).get("_server_canonicalized") or {}
                if marker.get("version") == 1:
                    continue
                canonical = _canonical_saved_request_payload(
                    settings,
                    username,
                    visit_id,
                    PrevisitSavedRequestUpsert(
                        lines=saved.get("lines") or [],
                        payment_type=str(saved.get("payment_type") or ""),
                        order_type=str(saved.get("order_type") or ""),
                        warehouse_ref=saved.get("warehouse_ref"),
                        warehouse_name=str(saved.get("warehouse_name") or ""),
                        preview=saved.get("preview") or {},
                    ),
                )
                update_saved_request(
                    settings,
                    username,
                    visit_id,
                    str(saved["id"]),
                    canonical,
                )
        # A server-canonicalized saved request was officially calculated and credit-checked
        # when it was created. Ending its visit must not revalidate the now-empty
        # working cart or accidentally submit one of several saved requests.
        validation = (
            validate_order_draft(settings, username, visit_id)
            if is_order
            and (completion_state is None or completion_state["line_count"])
            else None
        )
        if (
            completion_state is not None
            and not completion_state["line_count"]
            and not completion_state["saved_request_count"]
        ):
            raise PrevisitError("پایان ویزیت سفارشی نیاز به حداقل یک درخواست ذخیره‌شده دارد")
        registration = None
        # Keeping the feature switch off preserves the current local completion
        # flow and guarantees that this staged bridge cannot touch Varanegar.
        if validation is not None and settings.varanegar_order_bridge_enabled:
            registration = submit_validated_order(
                settings,
                username,
                visit_id,
                validation,
                getattr(request.app.state, "enterprise_store", None),
            )
            if not registration.get("committed"):
                result = get_visit_draft(settings, username, visit_id)
                result["order_registration"] = registration
                result["credit_control"] = validation["credit_control"]
                result["official_totals"] = validation["totals"]
                return result
        result = complete_visit(settings, username, visit_id, payload)
        if validation is not None:
            result["credit_control"] = validation["credit_control"]
            result["official_totals"] = validation["totals"]
            if registration is not None:
                result["order_registration"] = registration
        return result
    except VaranegarOrderBridgeUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VaranegarOrderBridgeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except PrevisitError as exc:
        raise _previsit_error(exc) from exc
    except TimeoutError as exc:
        raise _ngt_timeout_error() from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/map-config")
def get_neshan_map_config(request: Request):
    key = request.app.state.settings.neshan_web_api_key
    if not key:
        raise HTTPException(status_code=503, detail="Neshan web map is not configured")
    return {"api_key": key}


@router.get("/routes/{path_id}/map-plan")
def get_my_route_map_plan(
    path_id: str,
    request: Request,
    origin_latitude: float | None = Query(default=None),
    origin_longitude: float | None = Query(default=None),
    route_mode: str = Query(default="sales_priority"),
    start_day_route: bool = Query(default=False),
):
    try:
        return seller_route_map_plan(
            request.app.state.settings,
            _username(request),
            path_id,
            origin_latitude,
            origin_longitude,
            route_mode.strip() or "sales_priority",
            require_day_route=start_day_route,
        )
    except SellerRouteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SellerDayRouteMismatch as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/routes/{path_id}/map-leg")
def get_my_route_map_leg(path_id: str, destination_id: str, request: Request, origin_latitude: float = Query(), origin_longitude: float = Query()):
    try:
        return seller_route_map_leg(request.app.state.settings, _username(request), path_id, destination_id, origin_latitude, origin_longitude)
    except SellerRouteNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SellerWorkspaceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
