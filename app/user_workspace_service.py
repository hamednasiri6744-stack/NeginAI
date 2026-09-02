"""Trusted per-user workspace injected before conversational reasoning."""

from __future__ import annotations

from typing import Any

from app.auth_service import user_profile
from app.seller_identity_service import seller_identity_context


def build_user_workspace(
    settings: Any,
    username: str | None,
    access_policy: Any,
) -> dict[str, Any]:
    principal = str(username or "action-api-key").strip() or "action-api-key"
    profile = user_profile(settings, principal)
    identity: dict[str, Any] = {
        "username": principal,
        "authenticated": principal not in {"local", "action-api-key"},
    }
    if profile:
        identity.update({
            "username": str(profile.get("username") or principal),
            "full_name": str(profile.get("full_name") or ""),
            "role": str(profile.get("role") or ""),
            "branch": str(profile.get("branch") or ""),
            "sales_line": str(profile.get("sales_line") or ""),
            "personnel_id": profile.get("personnel_id"),
            "supervisor_personnel_id": profile.get("supervisor_personnel_id"),
        })

    seller_identity = seller_identity_context(settings, principal)
    workspace: dict[str, Any] = {
        "identity": identity,
        "organization": seller_identity or {},
        "access": access_policy.trusted_context(),
        "live_workspace": {
            "available": bool(seller_identity),
            "lazy": True,
            "instruction": (
                "For the signed-in seller's current routes, route customers, or sellable brands, "
                "use the dedicated live seller-workspace tools. Do not infer them from sales history."
            ),
        },
    }
    return workspace
