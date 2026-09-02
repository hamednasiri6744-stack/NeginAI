import secrets

from fastapi import Header, HTTPException, Request, status

from app.config import Settings
from app.auth_service import session_username, user_requires_password_change
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
    request.state.username = "action-api-key"


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
