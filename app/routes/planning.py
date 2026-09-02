from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.models import (
    PlanningScenarioCreateRequest,
    PlanningTransitionRequest,
    PlanningValuesUpsertRequest,
)
from app.organization_structure_service import require_admin
from app.control_service import permission_keys_for_user
from app.planning_service import (
    PLANNING_METRICS,
    PlanningError,
    compare_scenarios,
    create_scenario,
    get_scenario,
    list_scenarios,
    list_values,
    transition_scenario,
    upsert_values,
)
from app.routes.dependencies import require_user_or_local


router = APIRouter(
    prefix="/planning",
    tags=["planning"],
    dependencies=[Depends(require_user_or_local)],
)


def _admin(request: Request) -> str:
    username = str(getattr(request.state, "username", "") or "").strip()
    try:
        require_admin(request.app.state.settings, username)
    except PermissionError as exc:
        if "planning.manage" not in permission_keys_for_user(
            request.app.state.settings, username
        ):
            raise HTTPException(status_code=403, detail="این بخش فقط برای مدیران مجاز است") from exc
    return username


def _planning_error(exc: PlanningError) -> HTTPException:
    message = str(exc)
    status = 404 if "پیدا نشد" in message else 422
    return HTTPException(status_code=status, detail=message)


@router.get("/metadata", operation_id="getPlanningMetadata")
def planning_metadata(request: Request):
    _admin(request)
    return {
        "metrics": [
            {"code": code, "label": label}
            for code, label in PLANNING_METRICS.items()
        ],
        "scenario_types": [
            {"code": "budget", "label": "بودجه"},
            {"code": "forecast", "label": "پیش‌بینی"},
            {"code": "plan", "label": "برنامه"},
        ],
        "statuses": {
            "draft": "پیش‌نویس",
            "submitted": "ارسال‌شده",
            "approved": "تأییدشده",
            "locked": "قفل‌شده",
            "archived": "بایگانی‌شده",
        },
    }


@router.get("/scenarios", operation_id="listPlanningScenarios")
def planning_scenarios(
    request: Request,
    fiscal_year: int | None = Query(default=None, ge=1300, le=2500),
    include_archived: bool = False,
):
    _admin(request)
    return {
        "scenarios": list_scenarios(
            request.app.state.settings,
            fiscal_year=fiscal_year,
            include_archived=include_archived,
        )
    }


@router.post("/scenarios", status_code=201, operation_id="createPlanningScenario")
def create_planning_scenario(
    payload: PlanningScenarioCreateRequest, request: Request
):
    username = _admin(request)
    try:
        return create_scenario(
            request.app.state.settings,
            username,
            **payload.model_dump(),
        )
    except PlanningError as exc:
        raise _planning_error(exc) from exc


@router.get("/scenarios/{scenario_id}", operation_id="getPlanningScenario")
def planning_scenario(scenario_id: int, request: Request):
    _admin(request)
    try:
        return get_scenario(request.app.state.settings, scenario_id)
    except PlanningError as exc:
        raise _planning_error(exc) from exc


@router.post(
    "/scenarios/{scenario_id}/transition",
    operation_id="transitionPlanningScenario",
)
def transition_planning_scenario(
    scenario_id: int, payload: PlanningTransitionRequest, request: Request
):
    username = _admin(request)
    try:
        return transition_scenario(
            request.app.state.settings,
            scenario_id,
            username,
            payload.action,
            payload.note,
        )
    except PlanningError as exc:
        raise _planning_error(exc) from exc


@router.put("/scenarios/{scenario_id}/values", operation_id="upsertPlanningValues")
def upsert_planning_values(
    scenario_id: int, payload: PlanningValuesUpsertRequest, request: Request
):
    username = _admin(request)
    try:
        return upsert_values(
            request.app.state.settings,
            scenario_id,
            username,
            [value.model_dump() for value in payload.values],
        )
    except PlanningError as exc:
        raise _planning_error(exc) from exc


@router.get("/scenarios/{scenario_id}/values", operation_id="listPlanningValues")
def planning_values(
    scenario_id: int,
    request: Request,
    metric: str | None = Query(default=None, max_length=50),
    period: str | None = Query(default=None, pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    limit: int = Query(default=1000, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
):
    _admin(request)
    try:
        return list_values(
            request.app.state.settings,
            scenario_id,
            metric=metric,
            period=period,
            limit=limit,
            offset=offset,
        )
    except PlanningError as exc:
        raise _planning_error(exc) from exc


@router.get("/compare", operation_id="comparePlanningScenarios")
def planning_compare(
    request: Request,
    left_id: int = Query(gt=0),
    right_id: int = Query(gt=0),
    metric: str = Query(min_length=1, max_length=50),
):
    _admin(request)
    try:
        return compare_scenarios(
            request.app.state.settings, left_id, right_id, metric
        )
    except PlanningError as exc:
        raise _planning_error(exc) from exc
