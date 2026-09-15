"""Local Rubika credential bootstrap. No order reads, polling, or message sending.

Credentials are deliberately separate from the application's shared .env.
The setup client calls only the official getMe endpoint, without logging URLs.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


DEFAULT_USERNAME = "neginpakhsh_orders_bot"
# Machine-wide location: the interactive setup and SYSTEM service must resolve
# the same file. Do not change shared project-directory ACLs to store a secret.
PRIVATE_DIRECTORY = (
    Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "NeginAI" / "warehouse-rubika-private"
    if os.name == "nt"
    else Path(__file__).resolve().parents[1] / "data" / "warehouse-rubika-private"
)


class RubikaSetupError(ValueError):
    """A safe user-facing error; never embed credentials or raw provider errors."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RubikaSetupError("روبیکا پاسخ انتقال آدرس داد؛ اتصال ذخیره نشد.")


def _open_request(request):
    # No environment proxies, redirects, debug HTTP logging, or automatic retries.
    return build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=15)


def _clean_token(value: str) -> str:
    token = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{20,512}", token):
        raise RubikaSetupError("توکن را کامل و مستقیم از پیام بات کپی کنید؛ نه لینک یا عکس.")
    return token


def verify_bot(token: str, expected_username: str = DEFAULT_USERNAME) -> dict:
    token = _clean_token(token)
    expected = expected_username.strip().lstrip("@").lower()
    if not re.fullmatch(r"[a-z0-9_]{5,64}", expected):
        raise RubikaSetupError("نام کاربری بات معتبر نیست.")
    request = Request(
        "https://botapi.rubika.ir/v3/" + quote(token, safe="") + "/getMe",
        data=b"{}", headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with _open_request(request) as response:
            if response.status != 200:
                raise RubikaSetupError("روبیکا اتصال را تأیید نکرد؛ توکن ذخیره نشد.")
            raw = response.read(65537)
        if len(raw) > 65536:
            raise RubikaSetupError("پاسخ روبیکا نامعتبر است؛ اتصال ذخیره نشد.")
        payload = json.loads(raw)
    except HTTPError as error:
        code = error.code
        error.close()
        if code in (401, 403):
            raise RubikaSetupError("روبیکا توکن را نپذیرفت؛ کپی کامل توکن را بررسی کنید.") from None
        raise RubikaSetupError("روبیکا خطای سرویس داد؛ بعداً دوباره امتحان کنید.") from None
    except (URLError, TimeoutError, OSError):
        raise RubikaSetupError("ارتباط با روبیکا برقرار نشد؛ اینترنت را بررسی و دوباره تلاش کنید.") from None
    except (ValueError, UnicodeError):
        raise RubikaSetupError("پاسخ معتبر از روبیکا دریافت نشد؛ اتصال ذخیره نشد.") from None
    if not isinstance(payload, dict) or payload.get("status", "OK") != "OK":
        raise RubikaSetupError("روبیکا اتصال را تأیید نکرد؛ توکن ذخیره نشد.")
    data = payload.get("data", payload)
    bot = data.get("bot") if isinstance(data, dict) else None
    if not isinstance(bot, dict) or not isinstance(bot.get("username"), str) or not bot.get("bot_id"):
        raise RubikaSetupError("مشخصات بات در پاسخ روبیکا کامل نیست؛ اتصال ذخیره نشد.")
    if bot["username"].lstrip("@").lower() != expected:
        raise RubikaSetupError("این توکن متعلق به بات مورد انتظار نیست؛ اتصال قبلی تغییر نکرد.")
    # Only expected identity is returned; do not echo arbitrary remote text or token.
    return {"username": expected, "verified_at": datetime.now(timezone.utc).isoformat()}


def _restrict_directory(directory: Path) -> None:
    """Restrict access before any secret is written; fail closed if ACL fails.

    SYSTEM access permits the existing Windows service to read it in a future
    delivery integration. No running service consumes this file yet.
    """
    if directory.is_symlink() or (directory.exists() and directory.resolve() != directory.absolute()):
        raise OSError("Private directory must not be a link")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        directory.chmod(0o700)
        return
    path_literal = str(directory.absolute()).replace("'", "''")
    script = """
$ErrorActionPreference = 'Stop'
$rubikaAcl = New-Object System.Security.AccessControl.DirectorySecurity
$rubikaAcl.SetAccessRuleProtection($true, $false)
$rubikaUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().User
$rubikaAcl.SetOwner($rubikaUser)
foreach ($rubikaSid in @($rubikaUser.Value, 'S-1-5-18', 'S-1-5-32-544') | Select-Object -Unique) {
    $rubikaIdentity = New-Object System.Security.Principal.SecurityIdentifier($rubikaSid)
    $rubikaRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $rubikaIdentity, 'FullControl', 'ContainerInherit,ObjectInherit', 'None', 'Allow')
    $rubikaAcl.AddAccessRule($rubikaRule)
}
[System.IO.Directory]::SetAccessControl('PATH_LITERAL', $rubikaAcl)
""".replace("PATH_LITERAL", path_literal)
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
         base64.b64encode(script.encode("utf-16-le")).decode("ascii")],
        check=True, capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW,
    )


def configure_bot(token: str, expected_username: str = DEFAULT_USERNAME,
                  private_directory: Path = PRIVATE_DIRECTORY) -> dict:
    token = _clean_token(token)
    result = verify_bot(token, expected_username)
    temporary = None
    try:
        _restrict_directory(private_directory)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=private_directory,
                                         prefix="connection-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump({**result, "token": token, "delivery_enabled": False}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, private_directory / "connection.json")
    except (OSError, subprocess.SubprocessError):
        raise RubikaSetupError("ذخیره با دسترسی محدود انجام نشد؛ تنظیمات قبلی حفظ شد.") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return {**result, "configured": True, "delivery_enabled": False}
