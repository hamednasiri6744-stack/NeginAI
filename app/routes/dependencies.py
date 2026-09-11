import secrets

from fastapi import Header, HTTPException, Request, status

from app.config import Settings
from app.auth_service import session_username, user_profile, user_requires_password_change
from app.oauth_service import verify_access_token


def settings_from(request: Request) -> Settings:
    return request.app.state.settings


def _require_completed_first_login(request: Request, username: str) -> None:
    if user_requires_password_change(request.app.state.settings, username):
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="برای ادامه ابتدا رمز موقت خود را تغییر دهید.",
        )


def require_api_key(request: Request, x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    expected = request.app.state.settings.action_api_key
    if not expected or not x_api_key or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    request.state.username = "action-api-key"


def require_local_or_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Allow the installed UI locally; require the internal key over the network."""
    client_host = request.client.host if request.client else ""
    if client_host in {"127.0.0.1", "::1"}:
        return
    require_api_key(request, x_api_key)


def require_user_or_local(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    client_host = request.client.host if request.client else ""
    if authorization and authorization.lower().startswith("bearer "):
        username = verify_access_token(
            request.app.state.settings, authorization.split(" ", 1)[1].strip()
        )
        if username:
            _require_completed_first_login(request, username)
            request.state.username = username
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
        )
    session = request.cookies.get("negin_session", "")
    username = session_username(request.app.state.settings, session) if session else None
    if username:
        _require_completed_first_login(request, username)
        request.state.username = username
        return
    # Local desktop/native clients can still use the workspace without a
    # browser session, but a signed-in seller session must win first.
    if client_host in {"127.0.0.1", "::1"}:
        request.state.username = "local"
        return
    require_api_key(request, x_api_key)
    path = str(getattr(getattr(request, "url", None), "path", "") or "")
    protected_prefixes = ("/planning", "/automations", "/organization-structure", "/seller-workspace")
    if any(path == prefix or path.startswith(prefix + "/") for prefix in protected_prefixes):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A named user or local operator is required for this resource")
    request.state.username = "action-api-key"


def require_named_user_or_local(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Require a human/local principal; the service API key is read/report only."""
    require_user_or_local(request, x_api_key=x_api_key, authorization=authorization)
    if str(getattr(request.state, "username", "") or "") == "action-api-key":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A named user or local operator is required for this resource")


def require_admin_user_or_local(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> None:
    """Require local operator or an authenticated administrator for local metadata mutation."""
    require_named_user_or_local(request, x_api_key=x_api_key, authorization=authorization)
    username = str(getattr(request.state, "username", "") or "").strip()
    if username == "local":
        return
    profile = user_profile(request.app.state.settings, username) or {}
    role = str(profile.get("role") or "").casefold()
    permissions = {str(item) for item in (profile.get("permissions") or [])}
    if username.casefold() == "admin" or role in {"admin", "administrator"} or "control.manage" in permissions:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access is required")


def require_session_user(request: Request) -> None:
    """Require a named browser session; internal API keys cannot own push endpoints."""
    session = request.cookies.get("negin_session", "")
    username = session_username(request.app.state.settings, session) if session else None
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A signed-in user session is required",
        )
    _require_completed_first_login(request, username)
    request.state.username = username


