from __future__ import annotations

import ipaddress
import os

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.auth_service import (
    SESSION_SECONDS,
    activate_user,
    authenticate_user,
    change_password,
    create_session,
    revoke_user_sessions,
    session_username,
    user_profile,
)
from app.models import ChangePasswordRequest, LoginRequest
from app.login_rate_limit import (
    LoginRateLimitExceeded,
    LoginRateLimitUnavailable,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


class ActivationRequest(BaseModel):
    activation_token: str = Field(min_length=32, max_length=512)
    new_password: str = Field(min_length=8, max_length=200)


def _allow_tailnet_http_cookie(client: str) -> bool:
    if os.getenv("NEGINAI_DEV_PREVIEW_ALLOW_TAILNET_HTTP_COOKIE", "").strip() != "1":
        return False
    try:
        address = ipaddress.ip_address(client)
    except ValueError:
        return False
    return address in ipaddress.ip_network("100.64.0.0/10") or address in ipaddress.ip_network("fd7a:115c:a1e0::/48")


def _set_session_cookie(
    request: Request, response: Response, settings, username: str
) -> None:
    client = request.client.host if request.client else "unknown"
    is_local = client in {"127.0.0.1", "::1"}
    response.set_cookie(
        "negin_session",
        create_session(settings, username),
        max_age=SESSION_SECONDS,
        httponly=True,
        secure=not (is_local or _allow_tailnet_http_cookie(client)),
        samesite="strict",
        path="/",
    )


def _login_limiter(request: Request):
    limiter = getattr(request.app.state, "login_rate_limiter", None)
    if limiter is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication rate limiter is unavailable",
        )
    return limiter


def _consume_login_attempt(request: Request, client: str) -> None:
    try:
        _login_limiter(request).consume("auth-login", client)
    except LoginRateLimitExceeded as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="تعداد تلاش‌ها زیاد است؛ پنج دقیقه بعد امتحان کنید.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except LoginRateLimitUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication rate limiter is unavailable",
        ) from exc


@router.post("/login", operation_id="loginToNeginAI")
def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    client = request.client.host if request.client else "unknown"
    _consume_login_attempt(request, client)
    settings = request.app.state.settings
    username = authenticate_user(settings, payload.username, payload.password)
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نام کاربری یا رمز عبور اشتباه است.")
    try:
        _login_limiter(request).reset("auth-login", client)
    except LoginRateLimitUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication rate limiter is unavailable",
        ) from exc
    _set_session_cookie(request, response, settings, username)
    profile = user_profile(settings, username) or {"username": username}
    return {"authenticated": True, **profile}


def _session_profile(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    token = request.cookies.get("negin_session", "")
    username = session_username(settings, token) if token else None
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A signed-in user session is required",
        )
    profile = user_profile(settings, username)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return profile


@router.get("/me", operation_id="getCurrentNeginAIUser")
def me(request: Request, response: Response) -> dict[str, Any]:
    response.headers["Cache-Control"] = "no-store"
    return _session_profile(request)


@router.post("/change-password", operation_id="changeNeginAIPassword")
def update_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
) -> dict[str, Any]:
    profile = _session_profile(request)
    try:
        changed = change_password(
            request.app.state.settings,
            str(profile["username"]),
            payload.current_password,
            payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not changed:
        raise HTTPException(status_code=400, detail="رمز فعلی صحیح نیست.")
    # change_password invalidates every previous session and OAuth grant. This
    # successful workflow receives one fresh browser session.
    _set_session_cookie(
        request,
        response,
        request.app.state.settings,
        str(profile["username"]),
    )
    response.headers["Cache-Control"] = "no-store"
    return user_profile(request.app.state.settings, str(profile["username"])) or profile


@router.post("/logout", operation_id="logoutFromNeginAI")
def logout(request: Request, response: Response) -> dict[str, bool]:
    settings = request.app.state.settings
    token = request.cookies.get("negin_session", "")
    username = session_username(settings, token) if token else None
    if username:
        revoke_user_sessions(settings, username)
    response.delete_cookie("negin_session", path="/")
    return {"authenticated": False}


@router.post("/activate", operation_id="activateNeginAIUser")
def activate_account(
    payload: ActivationRequest,
    request: Request,
    response: Response,
) -> dict[str, Any]:
    try:
        username = activate_user(
            request.app.state.settings,
            payload.activation_token,
            payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activation token is invalid, expired, or already used",
        )
    _set_session_cookie(request, response, request.app.state.settings, username)
    response.headers["Cache-Control"] = "no-store"
    return {
        "activated": True,
        **(user_profile(request.app.state.settings, username) or {"username": username}),
    }
