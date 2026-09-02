from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health", operation_id="getHealth")
def health(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    return {
        "status": "ok",
        "service": "NeginAI SQL Gateway",
        "sql_configured": settings.sql_configured,
        "openai_configured": bool(settings.openai_api_key),
        "automation_configured": bool(settings.openai_automation_api_key),
        "automation_enabled": settings.automation_enabled,
        "push_configured": bool(settings.vapid_private_key_path),
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
        "openai_model": settings.openai_model,
        "openai_reasoning_effort": settings.openai_reasoning_effort,
        "model_router_enabled": settings.model_router_enabled,
        "router_fast_model": settings.router_fast_model,
        "router_standard_model": settings.router_standard_model,
        "openai_max_turns": settings.openai_max_turns,
        "admin_openai_max_turns": settings.admin_openai_max_turns,
        "admin_openai_history_limit": settings.admin_openai_history_limit,
        "admin_openai_max_tokens": settings.admin_openai_max_tokens,
    }
