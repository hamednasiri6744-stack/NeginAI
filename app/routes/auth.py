from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status

from app.auth_service import (
    SESSION_SECONDS,
    authenticate_user,
    change_password,
    create_session,
    session_username,
    user_profile,
)
from app.models import ChangePasswordRequest, LoginRequest

router = APIRouter(prefix="/auth", tags=["authentication"])
_attempts: dict[str, list[float]] = defaultdict(list)
_lock = threading.Lock()


def _check_rate_limit(client: str) -> None:
    cutoff = time.time() - 300
    with _lock:
        recent = [stamp for stamp in _attempts[client] if stamp > cutoff]
        _attempts[client] = recent
        if len(recent) >= 8:
            raise HTTPException(status_code=429, detail="تعداد تلاش‌ها زیاد است؛ پنج دقیقه بعد امتحان کنید.")


@router.post("/login", operation_id="loginToNeginAI")
def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    client = request.client.host if request.client else "unknown"
    _check_rate_limit(client)
    settings = request.app.state.settings
    username = authenticate_user(settings, payload.username, payload.password)
    if username is None:
        with _lock:
            _attempts[client].append(time.time())
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="نام کاربری یا رمز عبور اشتباه است.")
    with _lock:
        _attempts.pop(client, None)
    is_local = client in {"127.0.0.1", "::1"}
    response.set_cookie(
        "negin_session", create_session(settings, username), max_age=SESSION_SECONDS,
        httponly=True, secure=not is_local, samesite="strict", path="/",
    )
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
    response.headers["Cache-Control"] = "no-store"
    return user_profile(request.app.state.settings, str(profile["username"])) or profile


@router.post("/logout", operation_id="logoutFromNeginAI")
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie("negin_session", path="/")
    return {"authenticated": False}
