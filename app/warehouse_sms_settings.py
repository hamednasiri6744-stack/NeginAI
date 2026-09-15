"""Admin SMS configuration; saving does not send messages or start delivery jobs."""
from __future__ import annotations

import io
import os
import re
from threading import RLock

from dotenv import dotenv_values

from app.config import ENV_PATH

SEND_URL = 'https://panel.asanak.com/webservice/v2rest/sendsms'
STATUS_URL = 'https://panel.asanak.com/webservice/v2rest/msgstatus'
_lock = RLock()


class SmsSettingsError(ValueError):
    pass


def _public(values):
    username = values.get('ASANAK_USERNAME') or ''
    source = values.get('ASANAK_SOURCE') or ''
    has_password = bool(values.get('ASANAK_PASSWORD'))
    return {'provider': 'asanak', 'username': username, 'source': source,
            'password_configured': has_password,
            'configured': bool(username and source and has_password),
            'send_url': values.get('ASANAK_SEND_URL') or SEND_URL,
            'status_url': values.get('ASANAK_STATUS_URL') or STATUS_URL}


def read_settings():
    # Read the file each time: values saved by the UI must not come from stale
    # process environment. Disable interpolation so passwords containing $ stay literal.
    try:
        with _lock:
            return _public(dotenv_values(ENV_PATH, interpolate=False, encoding='utf-8-sig'))
    except (OSError, UnicodeError):
        raise SmsSettingsError('خواندن تنظیمات پیامک انجام نشد.') from None


def _validate(payload):
    if not isinstance(payload, dict) or set(payload) - {'username', 'source', 'password'}:
        raise SmsSettingsError('فیلدهای تنظیمات پیامک معتبر نیستند.')
    values = {}
    for key, label in [('username', 'نام کاربری'), ('source', 'خط ارسال')]:
        value = payload.get(key)
        if not isinstance(value, str):
            raise SmsSettingsError(f'{label} را وارد کنید.')
        value = value.translate(str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')).strip()
        if not re.fullmatch(r'[0-9]{5,20}', value):
            raise SmsSettingsError(f'{label} باید شامل ۵ تا ۲۰ رقم باشد.')
        values['ASANAK_' + key.upper()] = value
    password = payload.get('password', '')
    if not isinstance(password, str) or len(password) > 256 or any(ord(c) < 32 for c in password):
        raise SmsSettingsError('رمز پیامک معتبر نیست؛ ورود خط جدید مجاز نیست.')
    if password:
        values['ASANAK_PASSWORD'] = password
    return values


def save_settings(payload):
    updates = _validate(payload)
    try:
        with _lock:
            # Update the existing file in place to retain its Windows ACL/owner.
            # No backup containing passwords or second credential store is created.
            with ENV_PATH.open('r+b') as stream:
                original = stream.read()
                text = original.decode('utf-8-sig')
                values = dotenv_values(stream=io.StringIO(text), interpolate=False)
                if not updates.get('ASANAK_PASSWORD') and not values.get('ASANAK_PASSWORD'):
                    raise SmsSettingsError('برای راه‌اندازی اولیه، رمز پیامک را وارد کنید.')
                # Endpoints are fixed to Asanak. The UI cannot redirect credentials.
                updates.update(ASANAK_SEND_URL=SEND_URL, ASANAK_STATUS_URL=STATUS_URL)
                newline = '\r\n' if '\r\n' in text else '\n'
                lines = text.splitlines(keepends=True)
                for key, value in updates.items():
                    encoded = "'" + value.replace('\\', '\\\\').replace("'", "\\'") + "'"
                    replacement = f'{key}={encoded}{newline}'
                    matches = [i for i, line in enumerate(lines)
                               if re.match(r'^\s*(?:export\s+)?' + key + r'\s*=', line)]
                    if matches:
                        lines[matches[0]] = replacement
                        for index in matches[1:]:
                            lines[index] = ''
                    else:
                        if lines and not lines[-1].endswith(('\n', '\r')):
                            lines[-1] += newline
                        lines.append(replacement)
                candidate = ''.join(lines)
                checked = dotenv_values(stream=io.StringIO(candidate), interpolate=False)
                if any(checked.get(k) != v for k, v in updates.items()):
                    raise SmsSettingsError('ذخیرهٔ رمز با این نویسه‌ها ممکن نشد.')
                if any(checked.get(k) != v for k, v in values.items() if k not in updates):
                    raise SmsSettingsError('تنظیمات پیامک ذخیره نشد؛ ساختار فایل تنظیمات را بررسی کنید.')
                data = (b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'') + candidate.encode('utf-8')
                try:
                    stream.seek(0)
                    stream.write(data)
                    stream.truncate()
                    stream.flush()
                    os.fsync(stream.fileno())
                except OSError:
                    stream.seek(0)
                    stream.write(original)
                    stream.truncate()
                    stream.flush()
                    raise
                return _public(checked)
    except (OSError, UnicodeError):
        raise SmsSettingsError('ذخیرهٔ تنظیمات پیامک انجام نشد؛ دسترسی فایل تنظیمات سرور را بررسی کنید.') from None
