"""User-initiated supplier mail. No background sender or automatic retries.

Claim in SQLite before SMTP, protecting the approved snapshot from refresh.
An interrupted/ambiguous send remains locked for operator investigation.
SMTP acceptance is not proof of inbox delivery.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import smtplib
import ssl
from contextlib import suppress
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

from app.business_time import jalali_business_date, tehran_now
from app.warehouse_order_excel import build_supplier_workbook
from app.warehouse_assistant_service import (
    WarehouseAssistantError, _automatic_preorder_from_row, _now,
    _order_from_row, get_automatic_preorder, get_supplier_order,
    init_warehouse_store, warehouse_connection,
)

CONFIG_PATH = Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'NeginAI' / 'warehouse-mail-private' / 'connection.json'


class MailDeliveryFailure(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def _address(value):
    if not isinstance(value, str) or len(value) > 254 or not re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,63}", value
    ):
        raise WarehouseAssistantError('ایمیل تأمین‌کننده باید یک آدرس معتبر و بدون فاصله باشد.')
    return value


def _config():
    try:
        config = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        if config.get('delivery_enabled') is not True:
            raise ValueError('disabled')
        _address(config['username'])
        if not config['password'] or config['port'] != 465 or config['tls'] != 'implicit':
            raise ValueError('invalid TLS configuration')
        if not re.fullmatch(r'[a-zA-Z0-9.-]+', config['host']):
            raise ValueError('invalid host')
        return config
    except (OSError, ValueError, KeyError, TypeError):
        raise WarehouseAssistantError('اتصال ایمیل فعال یا تنظیم نشده است؛ مدیر سیستم بررسی کند.') from None


def preorder_workbook(preorder):
    columns = [
        'شماره پیش‌سفارش', 'تأمین‌کننده', 'انبار مقصد', 'کد کالا',
        'کد کالای تولیدکننده', 'بارکد', 'نام کالا', 'برند', 'کارتن', 'تعداد سفارش', 'ضریب کارتن',
        'قیمت تولیدکننده', 'قیمت مصرف‌کننده', 'قیمت حدودی', 'ارزش تخمینی',
    ]
    rows = [[preorder['preorder_number'], preorder['supplier'], line['warehouse_name'],
             line['product_code'], str(line.get('manufacturer_product_code') or ''), str(line.get('barcode') or ''), line['product_name'], line['brand'], line['cartons'],
             line['order_quantity'], line['conversion_rate'], line['manufacturer_price'],
             line['consumer_price'], line['approximate_price'], line['estimated_value']]
            for line in preorder['lines']]
    return build_supplier_workbook(columns, rows,
        f"پیش‌سفارش {preorder['preorder_number']} برای {preorder['supplier']}", preorder['lines'])


def _smtp_send(config, message):
    client = None
    data_started = False
    try:
        client = smtplib.SMTP_SSL(config['host'], 465, timeout=25,
                                  context=ssl.create_default_context())
        client.login(config['username'], config['password'])
        data_started = True
        refused = client.send_message(message)
        if refused:
            raise MailDeliveryFailure('failed', 'سرور ایمیل گیرنده را نپذیرفت.')
    except MailDeliveryFailure:
        raise
    except smtplib.SMTPResponseException:
        raise MailDeliveryFailure('failed', 'سرور ایمیل ارسال را نپذیرفت؛ تنظیمات و گیرنده را بررسی کنید.') from None
    except smtplib.SMTPRecipientsRefused:
        raise MailDeliveryFailure('failed', 'آدرس گیرنده توسط سرور ایمیل پذیرفته نشد.') from None
    except (OSError, smtplib.SMTPException):
        if data_started:
            raise MailDeliveryFailure('unknown', 'نتیجه ارسال نامشخص است؛ قبل از ارسال مجدد گزارش سرور بررسی شود.') from None
        raise MailDeliveryFailure('failed', 'اتصال امن یا ورود به سرور ایمیل موفق نبود؛ دوباره تلاش کنید.') from None
    finally:
        if client is not None:
            # A failed QUIT after accepted DATA must not turn success into a retry.
            with suppress(Exception):
                client.quit()
            with suppress(Exception):
                client.close()


def send_preorder_email(settings, username, preorder_id, expected_token):
    config = _config()
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT * FROM warehouse_automatic_preorders WHERE id=?', (preorder_id,)).fetchone()
        if row is None:
            raise WarehouseAssistantError('پیش‌سفارش پیدا نشد.')
        preorder = _automatic_preorder_from_row(conn, row)
        last = preorder['email_delivery']
        if last and last['status'] == 'sent':
            return {'preorder': preorder, 'send_status': 'sent', 'external_delivery_performed': False,
                    'already_sent': True}
        if last and last['status'] in ('sending', 'unknown'):
            raise WarehouseAssistantError('ارسال در حال انجام یا نیازمند بررسی است؛ برای جلوگیری از تکرار مجدداً ارسال نشد.')
        if preorder['business_date'] != jalali_business_date(tehran_now()):
            raise WarehouseAssistantError('این سفارش متعلق به روز جاری نیست؛ صف را بازخوانی کنید.')
        if preorder['status'] not in ('approved', 'send_requested') or not preorder['approved_at']:
            raise WarehouseAssistantError('ابتدا پیش‌سفارش را تأیید کنید.')
        if preorder['email_send_token'] != expected_token:
            raise WarehouseAssistantError('سفارش یا گیرنده تغییر کرده است؛ صف را بازخوانی و دوباره بررسی کنید.')
        from app.warehouse_order_receipts import ensure_orderable
        ensure_orderable(conn, preorder['warehouse_code'], [line['product_code'] for line in preorder['lines']])
        recipient = _address(preorder['contact_email'])
        if not preorder['lines'] or any(line['cartons'] < 1 for line in preorder['lines']):
            raise WarehouseAssistantError('اقلام سفارش برای ارسال معتبر نیستند.')
        content = preorder_workbook(preorder)
        if len(content) > 10 * 1024 * 1024:
            raise WarehouseAssistantError('حجم فایل سفارش برای ایمیل بیش از حد مجاز است.')
        message = EmailMessage()
        message['From'] = f"Negin Pakhsh Orders <{config['username']}>"
        message['To'] = recipient
        message['Subject'] = f"سفارش نگین پخش - {preorder['preorder_number']}"
        message['Date'] = formatdate(localtime=True)
        message['Message-ID'] = make_msgid(domain=config['username'].split('@')[1])
        message.set_content(
            f"سلام،\n\nسفارش تأییدشده نگین پخش برای {preorder['supplier']} به پیوست ارسال شده است.\n"
            f"شماره سفارش: {preorder['preorder_number']}\nانبار مقصد: {preorder['warehouse_name']}\n"
            f"تعداد اقلام: {len(preorder['lines'])}\nجمع کارتن: {preorder['total_cartons']}\n\n"
            'لطفاً دریافت سفارش، امکان تأمین و زمان تحویل را با پاسخ به همین ایمیل اعلام کنید.\n'
            'مبالغ درج‌شده حدودی هستند و به معنی تأیید قیمت نهایی نیستند.\n\nنگین پخش\n')
        message.add_attachment(content, maintype='application',
            subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            filename=f"order-{preorder['preorder_number']}.xlsx")
        # Serialize headers before claiming: invalid stored text must not leave a lock.
        message.as_bytes()
        started = _now()
        attempt_id = conn.execute("""INSERT INTO warehouse_email_attempts
            (preorder_id,recipient,sender,status,message_id,attachment_sha256,requested_by,started_at)
            VALUES(?,?,?,'sending',?,?,?,?)""",
            (preorder_id, recipient, config['username'], message['Message-ID'],
             hashlib.sha256(content).hexdigest(), username[:100], started)).lastrowid
        conn.execute("""UPDATE warehouse_automatic_preorders SET status='send_requested',
            send_requested_by=?,send_requested_at=?, contact_first_name=?,
            contact_last_name=?,contact_email=?,contact_mobile=? WHERE id=?""",
            (username[:100], started, preorder['contact_first_name'],
             preorder['contact_last_name'], recipient, preorder['contact_mobile'], preorder_id))
    outcome, error = 'sent', ''
    try:
        _smtp_send(config, message)
    except MailDeliveryFailure as exc:
        outcome, error = exc.status, str(exc)
    except Exception:
        # A crash after claim may have transmitted DATA. Never auto-retry it.
        outcome, error = 'unknown', 'نتیجه ارسال نیازمند بررسی مدیر سیستم است.'
    with warehouse_connection(settings) as conn:
        conn.execute('UPDATE warehouse_email_attempts SET status=?,error=?,completed_at=? WHERE id=?',
                     (outcome, error, _now(), attempt_id))
    return {'preorder': get_automatic_preorder(settings, preorder_id),
            'send_status': outcome,
            'external_delivery_performed': None if outcome == 'unknown' else outcome == 'sent',
            'already_sent': False}


def send_supplier_order_email(settings, username, order_id, expected_token):
    """Send one approved manual supplier order, with the same immutable claim semantics."""
    config = _config()
    init_warehouse_store(settings)
    with warehouse_connection(settings) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM supplier_orders WHERE id=?", (order_id,)).fetchone()
        if row is None:
            raise WarehouseAssistantError("سفارش تأمین‌کننده پیدا نشد.")
        order = _order_from_row(conn, row)
        last = order["email_delivery"]
        if last and last["status"] == "sent":
            return {"order": order, "send_status": "sent", "external_delivery_performed": False,
                    "already_sent": True}
        if last and last["status"] in ("sending", "unknown"):
            raise WarehouseAssistantError("ارسال در حال انجام یا نیازمند بررسی است؛ دوباره ارسال نشد.")
        if order["deleted"] or not order["is_approved"]:
            raise WarehouseAssistantError("ابتدا سفارش دستی را تأیید کنید.")
        if order["email_send_token"] != expected_token:
            raise WarehouseAssistantError("سفارش یا گیرنده تغییر کرده است؛ فهرست را بازخوانی و دوباره بررسی کنید.")
        if not order.get("receipt_review_override_at"):
            from app.warehouse_order_receipts import ensure_orderable
            ensure_orderable(conn, order["warehouse_code"], [line["product_code"] for line in order["lines"]])
        recipient = _address(order["contact_email"])
        from app.warehouse_order_sms import supplier_order_workbook
        content = supplier_order_workbook(order)
        if not order["lines"] or len(content) > 10 * 1024 * 1024:
            raise WarehouseAssistantError("اقلام یا حجم فایل سفارش برای ارسال معتبر نیست.")
        message = EmailMessage()
        message["From"] = f"Negin Pakhsh Orders <{config['username']}>"
        message["To"] = recipient
        message["Subject"] = f"سفارش نگین پخش - {order['order_number']}"
        message["Date"] = formatdate(localtime=True)
        message["Message-ID"] = make_msgid(domain=config["username"].split("@")[1])
        message.set_content(
            f"سلام،\n\nسفارش تأییدشده نگین پخش برای {order['supplier']} به پیوست ارسال شده است.\n"
            f"شماره سفارش: {order['order_number']}\nانبار مقصد: {order['warehouse_name']}\n"
            f"تعداد اقلام: {len(order['lines'])}\n\nلطفاً دریافت سفارش و زمان تحویل را اعلام کنید.\n\nنگین پخش\n"
        )
        message.add_attachment(content, maintype="application",
            subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"order-{order['order_number']}.xlsx")
        message.as_bytes()
        started = _now()
        attempt_id = conn.execute("""INSERT INTO warehouse_supplier_order_email_attempts
            (order_id,recipient,sender,status,message_id,attachment_sha256,requested_by,started_at)
            VALUES(?,?,?,'sending',?,?,?,?)""", (order_id, recipient, config["username"],
            message["Message-ID"], hashlib.sha256(content).hexdigest(), username[:100], started)).lastrowid
    outcome, error = "sent", ""
    try:
        _smtp_send(config, message)
    except MailDeliveryFailure as exc:
        outcome, error = exc.status, str(exc)
    except Exception:
        outcome, error = "unknown", "نتیجه ارسال نیازمند بررسی مدیر سیستم است."
    with warehouse_connection(settings) as conn:
        conn.execute("""UPDATE warehouse_supplier_order_email_attempts
                        SET status=?,error=?,completed_at=? WHERE id=?""",
                     (outcome, error, _now(), attempt_id))
    return {"order": get_supplier_order(settings, order_id, username, include_all=True),
            "send_status": outcome,
            "external_delivery_performed": None if outcome == "unknown" else outcome == "sent",
            "already_sent": False}
