from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import secrets
import time
from collections import defaultdict
from urllib.parse import parse_qs, unquote_plus, urlencode, urlparse

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.auth_service import (
    authenticate_user,
    session_username,
    user_requires_password_change,
)
from app.database import record_oauth_client_diagnostic
from app.oauth_service import (
    DEFAULT_SCOPE,
    create_authorization_code,
    exchange_authorization_code,
    exchange_refresh_token,
)

router = APIRouter(prefix="/oauth", tags=["oauth"])
_attempts: dict[str, list[float]] = defaultdict(list)


def _setup_page(client_id: str, client_secret: str | None) -> HTMLResponse:
    if client_secret is None:
        content = """<h1>ورود مدیر</h1><p>برای مشاهده تنظیمات محرمانه OAuth وارد شوید.</p>
<form id="login"><label>نام کاربری<input id="u" autocomplete="username" required></label>
<label>رمز عبور<input id="p" type="password" autocomplete="current-password" required></label>
<p id="e" class="error"></p><button>ورود امن</button></form>
<script>document.getElementById('login').onsubmit=async(e)=>{e.preventDefault();const r=await fetch('/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u.value,password:p.value})});if(r.ok)location.reload();else document.getElementById('e').textContent='نام کاربری یا رمز عبور اشتباه است.'}</script>"""
    else:
        content = f"""<h1>تنظیم OAuth اکشن</h1><p>این مقادیر را فقط در GPT Builder وارد کن.</p>
<label>Client ID<input readonly value="{html.escape(client_id, quote=True)}"></label>
<label>Client Secret<input id="secret" readonly type="password" value="{html.escape(client_secret, quote=True)}"></label>
<button type="button" onclick="secret.type='text';secret.select();navigator.clipboard.writeText(secret.value);this.textContent='کپی شد'">نمایش و کپی Client Secret</button>
<hr><p><b>Authorization URL</b><br>https://ai.neginpakhsh.com/oauth/authorize</p>
<p><b>Token URL</b><br>https://ai.neginpakhsh.com/oauth/token</p>
<p><b>Scope</b><br>company.read</p><p><b>Token Exchange Method</b><br>Default (POST Request)</p>"""
    return HTMLResponse(
        f"""<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>تنظیم OAuth NeginAI</title><style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f5f7;font-family:Tahoma,Arial,sans-serif;color:#202124}}main{{width:min(92vw,480px);background:#fff;padding:28px;border-radius:20px;box-shadow:0 18px 60px #1d1d2a20}}h1{{font-size:21px}}p{{font-size:13px;line-height:1.9;color:#5f6068;overflow-wrap:anywhere}}label{{display:grid;gap:7px;font-size:12px;margin:13px 0}}input{{width:100%;padding:13px;border:1px solid #d9d9df;border-radius:11px;font:inherit;direction:ltr}}button{{width:100%;border:0;border-radius:12px;padding:13px;background:#6037d6;color:#fff;font:bold 13px inherit;cursor:pointer}}.error{{color:#b42318}}hr{{border:0;border-top:1px solid #eee;margin:24px 0}}</style></head><body><main>{content}</main></body></html>""",
        headers={
            "Cache-Control": "no-store, max-age=0",
            "Pragma": "no-cache",
            "Referrer-Policy": "no-referrer",
            "X-Frame-Options": "DENY",
        },
    )


@router.get("/setup", response_class=HTMLResponse, include_in_schema=False)
def oauth_setup(request: Request):
    settings = request.app.state.settings
    session = request.cookies.get("negin_session", "")
    username = session_username(settings, session) if session else None
    authorized = bool(
        username
        and settings.login_username
        and hmac.compare_digest(username, settings.login_username)
    )
    return _setup_page(
        settings.oauth_client_id,
        settings.oauth_client_secret if authorized else None,
    )


def _allowed_redirect(uri: str) -> bool:
    parsed = urlparse(uri)
    host = (parsed.hostname or "").lower().rstrip(".")
    official_host = (
        host in {"openai.com", "chatgpt.com"}
        or host.endswith(".openai.com")
        or host.endswith(".chatgpt.com")
    )
    return parsed.scheme == "https" and official_host


def _authorization_error(
    response_type: str,
    client_id: str,
    expected_client_id: str,
    redirect_uri: str,
    scope: str,
    code_challenge_method: str,
) -> str | None:
    if response_type not in {"", "code"}:
        return "نوع پاسخ OAuth باید code باشد."
    if not secrets.compare_digest(client_id.strip(), expected_client_id):
        return "Client ID با مقدار ثبت‌شده در NeginAI یکسان نیست."
    if not _allowed_redirect(redirect_uri.strip()):
        host = urlparse(redirect_uri).hostname or "نامشخص"
        return f"Callback URL ارسالی ChatGPT مجاز نیست (میزبان: {host})."
    if _scope(scope.strip()) is None:
        return "Scope باید دقیقاً company.read باشد."
    if code_challenge_method.strip().upper() not in {"", "PLAIN", "S256"}:
        return "روش PKCE ارسالی ChatGPT پشتیبانی نمی‌شود."
    return None


def _scope(value: str) -> str | None:
    requested = set(value.split()) if value else {DEFAULT_SCOPE}
    return " ".join(sorted(requested)) if requested <= {DEFAULT_SCOPE} else None


def _signature(secret: str, values: list[str]) -> str:
    payload = "\x1f".join(values).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _authorize_values(data: dict[str, str]) -> list[str]:
    return [
        data.get("client_id", ""), data.get("redirect_uri", ""), data.get("state", ""),
        data.get("scope", ""), data.get("code_challenge", ""),
        data.get("code_challenge_method", ""),
    ]


def _login_page(data: dict[str, str], signature: str, error: str = "") -> HTMLResponse:
    hidden = "".join(
        f'<input type="hidden" name="{html.escape(key)}" value="{html.escape(value, quote=True)}">'
        for key, value in data.items()
    )
    hidden += f'<input type="hidden" name="request_signature" value="{signature}">'
    error_html = f'<p class="error">{html.escape(error)}</p>' if error else ""
    return HTMLResponse(f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ورود به NeginAI</title><style>
*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;display:grid;place-items:center;background:#f5f5f7;font-family:Tahoma,Arial,sans-serif;color:#202124}}
form{{width:min(92vw,410px);background:#fff;padding:30px;border-radius:22px;box-shadow:0 18px 60px #1d1d2a20}}
.logo{{width:52px;height:52px;border-radius:16px;display:grid;place-items:center;background:#6037d6;color:#fff;font-size:24px;font-weight:bold;margin-bottom:18px}}
h1{{font-size:21px;margin:0 0 8px}}p{{font-size:13px;line-height:1.9;color:#6b6b73;margin:0 0 18px}}label{{display:grid;gap:7px;font-size:12px;margin:13px 0}}input{{width:100%;padding:13px;border:1px solid #d9d9df;border-radius:11px;font:inherit;outline:none}}input:focus{{border-color:#7656d6;box-shadow:0 0 0 3px #eee9ff}}button{{width:100%;border:0;border-radius:12px;padding:13px;background:#6037d6;color:#fff;font:bold 13px inherit;cursor:pointer;margin-top:8px}}.error{{color:#b42318;background:#fff1f0;border-radius:9px;padding:8px 10px}}
</style></head><body><form method="post" action="/oauth/authorize">
<div class="logo">ن</div><h1>ورود به هوش مصنوعی نگین پخش</h1>
<p>برای دسترسی به اطلاعات داخلی، با حساب سازمانی خود وارد شوید. رمز عبور به ChatGPT ارسال نمی‌شود.</p>
{error_html}{hidden}
<label>نام کاربری<input name="username" autocomplete="username" required autofocus></label>
<label>رمز عبور<input name="password" type="password" autocomplete="current-password" required></label>
<button type="submit">ورود امن و ادامه</button></form></body></html>""")


@router.get("/authorize", response_class=HTMLResponse, include_in_schema=False)
def authorize_page(
    request: Request,
    response_type: str = "",
    client_id: str = "",
    redirect_uri: str = "",
    state: str = "",
    scope: str = DEFAULT_SCOPE,
    code_challenge: str = "",
    code_challenge_method: str = "",
):
    settings = request.app.state.settings
    error = _authorization_error(
        response_type.strip(), client_id, settings.oauth_client_id, redirect_uri,
        scope, code_challenge_method,
    )
    if error:
        return HTMLResponse(
            f"<html lang='fa' dir='rtl'><meta charset='utf-8'><body style='font-family:Tahoma;padding:24px'><h2>درخواست ورود معتبر نیست</h2><p>{html.escape(error)}</p></body></html>",
            status_code=400,
        )
    clean_scope = _scope(scope.strip()) or DEFAULT_SCOPE
    normalized_method = code_challenge_method.strip().upper()
    if normalized_method == "PLAIN":
        normalized_method = "plain"
    data = {
        "client_id": client_id.strip(), "redirect_uri": redirect_uri.strip(), "state": state,
        "scope": clean_scope, "code_challenge": code_challenge,
        "code_challenge_method": normalized_method,
    }
    return _login_page(data, _signature(settings.oauth_client_secret, _authorize_values(data)))


@router.post("/authorize", include_in_schema=False)
async def authorize_login(request: Request):
    raw = (await request.body()).decode("utf-8", "replace")
    parsed = {key: values[-1] for key, values in parse_qs(raw, keep_blank_values=True).items()}
    settings = request.app.state.settings
    data = {key: parsed.get(key, "") for key in (
        "client_id", "redirect_uri", "state", "scope", "code_challenge", "code_challenge_method"
    )}
    expected_signature = _signature(settings.oauth_client_secret, _authorize_values(data))
    if not hmac.compare_digest(parsed.get("request_signature", ""), expected_signature):
        return HTMLResponse("درخواست ورود منقضی یا نامعتبر است.", status_code=400)
    if (
        not secrets.compare_digest(data["client_id"], settings.oauth_client_id)
        or not _allowed_redirect(data["redirect_uri"])
        or _scope(data["scope"]) is None
    ):
        return HTMLResponse("درخواست ورود معتبر نیست.", status_code=400)

    client = request.client.host if request.client else "unknown"
    cutoff = time.time() - 300
    _attempts[client] = [stamp for stamp in _attempts[client] if stamp > cutoff]
    if len(_attempts[client]) >= 8:
        return _login_page(data, expected_signature, "تعداد تلاش‌ها زیاد است؛ پنج دقیقه بعد دوباره امتحان کنید.")
    username = authenticate_user(
        settings, parsed.get("username", ""), parsed.get("password", "")
    )
    if username is None:
        _attempts[client].append(time.time())
        return _login_page(data, expected_signature, "نام کاربری یا رمز عبور اشتباه است.")
    if user_requires_password_change(settings, username):
        return _login_page(
            data,
            expected_signature,
            "ابتدا وارد اپ نگین AI شوید و رمز موقت خود را تغییر دهید.",
        )
    _attempts.pop(client, None)
    code = create_authorization_code(
        settings, username, data["client_id"], data["redirect_uri"],
        data["scope"], data["code_challenge"] or None, data["code_challenge_method"] or None,
    )
    separator = "&" if "?" in data["redirect_uri"] else "?"
    target = data["redirect_uri"] + separator + urlencode({"code": code, "state": data["state"]})
    return RedirectResponse(target, status_code=303)


def _normalize_token_payload(payload: dict[str, object]) -> dict[str, str]:
    aliases = {
        "clientId": "client_id", "clientSecret": "client_secret",
        "grantType": "grant_type", "redirectUri": "redirect_uri",
        "codeVerifier": "code_verifier", "refreshToken": "refresh_token",
    }
    normalized: dict[str, str] = {}
    for key, value in payload.items():
        target = aliases.get(key, key)
        if isinstance(value, (str, int, float)):
            normalized[target] = str(value)
    return normalized


async def _token_payload(request: Request) -> dict[str, str]:
    raw = (await request.body()).decode("utf-8", "replace")
    content_type = request.headers.get("content-type", "").lower()
    payload: dict[str, object] = {}
    if "application/json" in content_type or raw.lstrip().startswith("{"):
        try:
            value = json.loads(raw or "{}")
            if isinstance(value, dict):
                payload = value
        except json.JSONDecodeError:
            payload = {}
    if not payload:
        payload = {
            key: values[-1]
            for key, values in parse_qs(raw, keep_blank_values=True).items()
        }
    for key, value in request.query_params.items():
        payload.setdefault(key, value)
    return _normalize_token_payload(payload)


def _client_credentials(request: Request, parsed: dict[str, str]) -> tuple[str, str, str]:
    authorization = request.headers.get("Authorization", "")
    if authorization.lower().startswith("basic "):
        try:
            decoded = base64.b64decode(authorization.split(" ", 1)[1]).decode("utf-8")
            client_id, client_secret = decoded.split(":", 1)
            return unquote_plus(client_id).strip(), unquote_plus(client_secret).strip(), "basic"
        except (ValueError, UnicodeError):
            return "", "", "basic_invalid"
    if "client_id" in parsed or "client_secret" in parsed:
        content_type = request.headers.get("content-type", "").lower()
        method = "json" if "application/json" in content_type else "form_or_query"
        return parsed.get("client_id", "").strip(), parsed.get("client_secret", "").strip(), method
    if request.headers.get("X-Client-ID") or request.headers.get("X-Client-Secret"):
        return (
            request.headers.get("X-Client-ID", "").strip(),
            request.headers.get("X-Client-Secret", "").strip(),
            "x_headers",
        )
    return "", "", "missing"


def _content_type_category(request: Request) -> str:
    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        return "json"
    if "application/x-www-form-urlencoded" in content_type:
        return "form"
    if "multipart/form-data" in content_type:
        return "multipart"
    return "other" if content_type else "missing"


@router.post("/token", include_in_schema=False)
async def token(request: Request):
    parsed = await _token_payload(request)
    settings = request.app.state.settings
    client_id, client_secret, auth_method = _client_credentials(request, parsed)
    client_id_match = secrets.compare_digest(client_id, settings.oauth_client_id)
    client_secret_match = secrets.compare_digest(client_secret, settings.oauth_client_secret)
    record_oauth_client_diagnostic(
        settings,
        auth_method=auth_method,
        content_type=_content_type_category(request),
        client_id_present=bool(client_id),
        client_id_match=client_id_match,
        client_secret_present=bool(client_secret),
        client_secret_length=len(client_secret),
        client_secret_match=client_secret_match,
    )
    if not (client_id_match and client_secret_match):
        return JSONResponse(
            {"error": "invalid_client", "error_description": "OAuth client credentials did not match."},
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="NeginAI OAuth"', "Cache-Control": "no-store"},
        )
    grant_type = parsed.get("grant_type", "")
    if grant_type == "authorization_code":
        result = exchange_authorization_code(
            settings, parsed.get("code", ""), client_id, parsed.get("redirect_uri", ""),
            parsed.get("code_verifier", ""),
        )
    elif grant_type == "refresh_token":
        result = exchange_refresh_token(settings, parsed.get("refresh_token", ""))
    else:
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400)
    if result is None:
        return JSONResponse({"error": "invalid_grant"}, status_code=400)
    return JSONResponse(result, headers={"Cache-Control": "no-store", "Pragma": "no-cache"})
