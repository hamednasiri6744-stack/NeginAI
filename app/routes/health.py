from fastapi import APIRouter, Depends, Request

from app.routes.chat import model_resource_policy
from app.routes.dependencies import require_user_or_local
from app.seller_workspace_service import _neshan_direction

router = APIRouter(tags=["health"])


@router.get("/health", operation_id="getHealth")
async def health() -> dict[str, object]:
    """Public process liveness without deployment or provider metadata."""
    return {
        "status": "ok",
        "service": "NeginAI",
    }


@router.get(
    "/health/neshan",
    operation_id="getNeshanHealth",
    dependencies=[Depends(require_user_or_local)],
)
def neshan_health(request: Request) -> dict[str, object]:
    """Protected provider probe without exposing map credentials or provider payloads."""
    settings = request.app.state.settings
    web_configured = bool(settings.neshan_web_api_key)
    service_configured = bool(settings.neshan_service_api_key)
    if not service_configured:
        return {
            "configured": web_configured and service_configured,
            "web_configured": web_configured,
            "service_configured": service_configured,
            "service_reachable": False,
            "error_type": "not_configured",
        }
    try:
        result = _neshan_direction(settings, 35.7219, 51.3347, 35.6892, 51.3890)
    except Exception as exc:
        return {
            "configured": web_configured and service_configured,
            "web_configured": web_configured,
            "service_configured": service_configured,
            "service_reachable": False,
            "error_type": type(exc).__name__,
        }
    return {
        "configured": web_configured and service_configured,
        "web_configured": web_configured,
        "service_configured": service_configured,
        "service_reachable": bool(result.get("leg") or result.get("polyline")),
        "error_type": None,
    }


@router.get(
    "/health/readiness",
    operation_id="getReadiness",
    dependencies=[Depends(require_user_or_local)],
)
def readiness(request: Request) -> dict[str, object]:
    """Authenticated configuration readiness for operators and diagnostics."""
    settings = request.app.state.settings
    external_resource_backend = getattr(request.app.state, "model_resource_backend", ...)
    try:
        resource_policy = model_resource_policy()
        resource_controls_ready = not getattr(
            request.app.state, "_model_resource_backend_failed", False
        ) and external_resource_backend is not None
    except RuntimeError:
        resource_policy = None
        resource_controls_ready = False
    return {
        "status": "ok",
        "service": "NeginAI SQL Gateway",
        "sql_configured": settings.sql_configured,
        "openai_configured": bool(settings.openai_api_key),
        "automation_configured": bool(settings.openai_automation_api_key),
        "automation_enabled": settings.automation_enabled,
        "push_configured": bool(settings.vapid_private_key_path),
        "neshan_web_configured": bool(settings.neshan_web_api_key),
        "neshan_service_configured": bool(settings.neshan_service_api_key),
        "varanegar_order_bridge_configured": settings.varanegar_order_sql_configured,
        "varanegar_order_bridge_enabled": settings.varanegar_order_bridge_enabled,
        "varanegar_order_commit_enabled": settings.varanegar_order_commit_enabled,
        "varanegar_order_numbering_verified": settings.varanegar_order_numbering_verified,
        "varanegar_order_registration_ready": bool(
            settings.varanegar_order_sql_configured
            and settings.varanegar_order_bridge_enabled
            and settings.varanegar_order_commit_enabled
            and settings.varanegar_order_numbering_verified
        ),
        "enterprise_database_configured": bool(settings.enterprise_database_url),
        "enterprise_database_ready": (
            bool(getattr(request.app.state, "enterprise_database_ready", False))
            if settings.enterprise_database_url else None
        ),
        "redis_configured": bool(settings.redis_url),
        "redis_ready": (
            bool(getattr(request.app.state, "redis_ready", False))
            if settings.redis_url else None
        ),
        "enterprise_runtime_ready": bool(
            (not settings.enterprise_database_url or getattr(request.app.state, "enterprise_database_ready", False))
            and (not settings.redis_url or getattr(request.app.state, "redis_ready", False))
            and (not settings.command_outbox_enabled or getattr(request.app.state, "command_worker_ready", False))
        ),
        "command_outbox_enabled": settings.command_outbox_enabled,
        "command_worker_ready": (
            getattr(request.app.state, "command_worker_ready", False)
            if settings.command_outbox_enabled
            else None
        ),
        "openai_model": settings.openai_model,
        "openai_reasoning_effort": settings.openai_reasoning_effort,
        "model_router_enabled": settings.model_router_enabled,
        "router_fast_model": settings.router_fast_model,
        "router_standard_model": settings.router_standard_model,
        "openai_max_turns": settings.openai_max_turns,
        "admin_openai_max_turns": settings.admin_openai_max_turns,
        "admin_openai_history_limit": settings.admin_openai_history_limit,
        "admin_openai_max_tokens": settings.admin_openai_max_tokens,
        "model_resource_controls_ready": resource_controls_ready,
        "model_resource_backend": (
            "process-local"
            if external_resource_backend is ...
            else "external" if external_resource_backend is not None else "unavailable"
        ),
        "model_resource_limits": (
            {
                "global_concurrency": resource_policy.global_concurrency,
                "user_concurrency": resource_policy.user_concurrency,
                "user_requests_per_minute": resource_policy.user_requests_per_minute,
                "user_daily_budget_units": resource_policy.user_daily_budget_units,
                "global_daily_budget_units": resource_policy.global_daily_budget_units,
                "max_request_budget_units": resource_policy.max_request_budget_units,
            }
            if resource_policy
            else None
        ),
    }
