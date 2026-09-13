from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from app.config import Settings
from app.database import sqlite_connection


# These are intentionally conservative. A source is not exposed to a seller merely
# because its name looks business-related; it must be reviewed or explicitly listed.
SELLER_CUSTOMER_SOURCES = frozenset({
    "dbo.salesreviewfast", "dbo.salesreturnreviewfast", "dbo.customer",
    "dbo.customercardex_info", "dbo.vwtablethistory", "acc.vwrcvpaymentsreview",
    "acc.vwrcvsalereview", "acc.vwrcvsalereviewfast", "acc.vwrcvstatementreviewfast",
    "acc.vwrcvchequereview", "acc.vwrcvbankordersreview", "acc.vwrcvretchequereview",
    "acc.vwrcvretsalereview", "acc.vwcustomerbalance", "acc.vwpaymentsfast",
    "dbo.vwreview_rcvaccountsale2", "dbo.vwreview_rcvaccountpayment2",
    "dbo.vwreview_rcvaccountsettlement2", "dbo.vwreview_rcvaccountcardex2",
    "gnr.vwcust",
})
SELLER_REFERENCE_SOURCES = frozenset({
    "gnr.tblbrand", "gnr.tblmanufacturer", "gnr.tblgoods", "gnr.tblgoodsgroup",
    "gnr.tblsalearea", "gnr.tblsalepath",
})

_WORD_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z]|\d|$)|[A-Z]?[a-z]+|\d+", re.ASCII)
_PERSIAN_WORDS = {
    "acc": "حسابداری", "account": "حساب", "amount": "مبلغ", "balance": "مانده",
    "bank": "بانک", "branch": "شعبه", "buy": "خرید", "cardex": "کاردکس",
    "category": "گروه", "cheque": "چک", "code": "کد", "customer": "مشتری",
    "cust": "مشتری", "date": "تاریخ", "detail": "جزئیات", "discount": "تخفیف",
    "factor": "فاکتور", "goods": "کالا", "group": "گروه", "history": "تاریخچه",
    "inventory": "موجودی", "invoice": "فاکتور", "item": "ردیف", "line": "لاین",
    "manufacturer": "تولیدکننده", "marketer": "بازاریاب", "name": "نام",
    "net": "خالص", "order": "سفارش", "payment": "پرداخت", "price": "قیمت",
    "product": "کالا", "profit": "سود", "purchase": "خرید", "receipt": "دریافت",
    "refund": "استرداد", "return": "برگشتی", "review": "گزارش", "sale": "فروش",
    "sales": "فروش", "salesman": "فروشنده", "seller": "فروشنده", "status": "وضعیت",
    "stock": "موجودی", "supplier": "تأمین‌کننده", "total": "جمع", "tour": "ویزیت",
    "type": "نوع", "user": "کاربر", "voucher": "سند", "warehouse": "انبار",
}
# Exact identifier meanings override the generic word-by-word translation.
# Financial abbreviations in particular are unsafe to expand one word at a time:
# AccYear is a fiscal-year key, and Bed/Bes are debit/credit amounts.
_EXACT_PERSIAN_LABELS = {
    "id": "شناسه رکورد",
    "accyear": "سال مالی",
    "dcref": "شناسه مرکز توزیع",
    "ud_id": "شناسه یکتا",
    "custref": "شناسه مشتری",
    "custctgrref": "شناسه گروه مشتری",
    "goodsref": "شناسه کالا",
    "dateof": "تاریخ",
    "validstartdate": "تاریخ شروع اعتبار",
    "validenddate": "تاریخ پایان اعتبار",
    "bedamount": "مبلغ بدهکار",
    "besamount": "مبلغ بستانکار",
    "balance": "مانده حساب",
    "voucherno": "شماره سند",
    "voucherid": "شناسه سند",
    "voucherdate": "تاریخ سند",
    "vchno": "شماره سند",
    "vchdate": "تاریخ سند",
    "vchtypename": "نوع سند",
    "bed_vocherdate": "تاریخ سند بدهکار",
    "bed_vocherno": "شماره سند بدهکار",
    "bes_vocherdate": "تاریخ سند بستانکار",
    "bes_vocherno": "شماره سند بستانکار",
    "vocherno": "شماره سند",
    "vchdate2": "تاریخ سند ۲",
    "invvchno": "شماره سند انبار",
    "voucheritemid": "شناسه قلم سند",
    "voucheritemtype": "نوع قلم سند",
    "voucheritemno": "شماره قلم سند",
    "voucheritemdesc": "شرح قلم سند",
    # Customer/contact fields used by the Box & Bottle module are unambiguous
    # even though that module does not publish them in the Varanegar resource.
    "boxbottlecustomerid": "شناسه مشتری باکس و بطری",
    "storename": "نام فروشگاه",
    "phone": "تلفن",
    "mobile": "موبایل",
    "address": "نشانی",
}
_COLUMN_WORDS = {
    "acc": "حساب", "act": "عملیات", "active": "فعال", "add": "افزوده", "added": "افزوده", "addition": "افزوده",
    "address": "نشانی", "amount": "مبلغ", "app": "برنامه", "application": "برنامه", "area": "ناحیه",
    "after": "پس از", "auto": "خودکار", "automatic": "خودکار", "back": "پشتی", "bank": "بانک", "barcode": "بارکد", "batch": "بچ", "before": "قبل از", "bes": "بستانکار", "bed": "بدهکار", "bottle": "بطری", "box": "باکس", "by": "توسط", "branch": "شعبه",
    "buy": "خرید", "can": "امکان", "caption": "عنوان", "carton": "کارتن", "category": "گروه", "center": "مرکز", "change": "تغییر", "check": "کنترل", "close": "بستن", "conclusive": "قطعی", "control": "کنترل", "create": "ایجاد",
    "code": "کد", "comment": "توضیحات", "concurrency": "هم‌زمانی", "confirm": "تأیید", "created": "ایجاد", "creation": "ایجاد",
    "credit": "بستانکار", "creator": "ایجادکننده", "cust": "مشتری", "ctgr": "گروه", "customer": "مشتری", "data": "داده", "date": "تاریخ", "dc": "مرکز توزیع", "debit": "بدهکار", "delete": "حذف", "desc": "شرح", "detail": "جزئیات",
    "dealer": "فروشنده", "description": "شرح", "dis": "تخفیف", "discount": "تخفیف", "dist": "توزیع", "end": "پایان",
    "exit": "خروج", "field": "فیلد", "filter": "فیلتر", "fifth": "پنجم", "first": "اول", "follow": "پیگیری", "full": "کامل", "gen": "تولید", "generated": "تولیدشده",
    "goods": "کالا", "group": "گروه", "hdr": "سربرگ", "healthy": "سالم", "host": "میزبان", "id": "شناسه",
    "in": "در", "inv": "انبار", "is": "آیا", "item": "قلم", "itm": "قلم", "last": "آخرین", "ledger": "دفتر", "link": "ارتباط", "list": "فهرست", "manual": "دستی", "manufacturer": "تولیدکننده", "modified": "ویرایش", "month": "ماه",
    "name": "نام", "net": "خالص", "no": "شماره", "number": "شماره", "office": "دفتر", "order": "سفارش",
    "other": "سایر", "out": "بدون", "owner": "مالک", "pack": "بسته", "percent": "درصد", "personnel": "پرسنل",
    "has": "دارای", "health": "سلامت", "history": "تاریخچه", "open": "باز", "priority": "اولویت", "pricing": "قیمت‌گذاری", "prize": "جایزه", "price": "قیمت", "product": "محصول", "qty": "تعداد", "quantity": "تعداد",
    "reason": "علت", "receipt": "دریافت", "reference": "مرجع", "ref": "شناسه", "removed": "حذف‌شده", "reprint": "چاپ مجدد", "ret": "برگشتی", "return": "برگشتی", "row": "ردیف",
    "safe": "صندوق", "sale": "فروش", "sales": "فروش", "sell": "فروش", "selected": "انتخاب‌شده", "sixth": "ششم",
    "side": "سمت", "sql": "اس‌کیوال", "start": "شروع", "state": "وضعیت", "status": "وضعیت", "stock": "انبار", "t": "عطف", "temp": "موقت", "third": "سوم",
    "title": "عنوان", "total": "کل", "type": "نوع", "un": "غیر", "unique": "یکتا", "unit": "واحد",
    "update": "به‌روزرسانی", "user": "کاربر", "username": "نام کاربری", "valid": "اعتبار", "vch": "سند", "vocher": "سند", "vouchers": "اسناد", "voucher": "سند",
    "weight": "وزن", "with": "با", "year": "سال",
}

# Remaining abbreviations in technical View columns.  These are displayed in
# Persian after the Varanegar/SQL labels have had precedence.
_EXACT_PERSIAN_LABELS.update({
    "vocherdate": "تاریخ سند",
    "vochertatus": "وضعیت سند",
    "voucheritemid": "شناسه قلم سند",
    "voucheritemtype": "نوع قلم سند",
    "voucheritemno": "شماره قلم سند",
    "voucheritemdesc": "شرح قلم سند",
})
_COLUMN_WORDS.update({
    "all": "همه", "asn": "اسنادی", "ba": "با", "cancel": "ابطال", "capacity": "ظرفیت",
    "accept": "پذیرش", "cardex": "کاردکس", "conflict": "مغایرت", "damaged": "آسیب‌دیده", "day": "روز", "days": "روزها", "do": "انجام", "duration": "مدت",
    "edit": "ویرایش", "effect": "اثر", "effectiveon": "مؤثر", "external": "خارجی", "flag": "علامت",
    "followup": "پیگیری", "for": "برای", "form": "فرم", "from": "از", "hand": "دست",
    "ica": "تأمین", "initial": "اولیه", "input": "ورودی", "insert": "ثبت", "invoice": "فاکتور",
    "issue": "صدور", "level": "سطح", "limit": "حد", "log": "ثبت", "main": "اصلی", "match": "تطبیق",
    "msg": "پیام", "nut": "خالص", "old": "قدیمی", "on": "در", "opr": "عملیات", "pre": "پیش", "print": "چاپ", "rule": "قانون",
    "separate": "جدا", "setad": "ستاد", "show": "نمایش", "supplier": "تأمین‌کننده", "tasvie": "تسویه",
    "to": "تا", "trail": "مسیر", "vochers": "اسناد",
})

_DOMAIN_MARKERS = (
    ("فروش و مشتری", ("sale", "sales", "customer", "cust", "factor", "invoice", "receipt")),
    ("کالا و انبار", ("goods", "product", "stock", "inventory", "warehouse")),
    ("خرید و تأمین", ("buy", "purchase", "supplier")),
    ("مالی و حسابداری", ("account", "bank", "cheque", "voucher", "treasury")),
    ("منابع انسانی و سازمان", ("personnel", "employee", "payroll", "salary")),
)
_RESTRICTED_MARKERS = ("buy", "purchase", "supplier", "profit", "margin", "cost", "ica", "treasury", "payroll", "salary")
_CLASSIFICATIONS = frozenset({
    "customer_sales", "customer_collections", "customer_master", "product_reference",
    "inventory", "purchase", "finance", "treasury", "personnel", "master_data",
    "marketing_distribution", "system_security", "workflow_configuration", "reporting",
    "needs_review",
})

# High-value sources are named deliberately rather than relying on word-by-word
# translation. They are the first objects surfaced to the assistant for sales and
# inventory questions. Inventory reports remain restricted for sellers unless a
# future policy explicitly introduces a safe stock scope.
_CURATED_OBJECTS: dict[str, dict[str, Any]] = {
    "dbo.salesreviewfast": {
        "persian_name": "گزارش سریع فروش مشتریان",
        "description": "View اصلی گزارش فروش مشتریان؛ برای فروش و تحلیل مشتری در محدودهٔ مجاز فروشنده.",
        "domain": "فروش و مشتری", "classification": "customer_sales", "seller_access": "customer_scope",
        "aliases": ["فروش مشتری", "گزارش فروش", "فروش سریع", "فروش خالص"],
    },
    "dbo.salesreturnreviewfast": {
        "persian_name": "گزارش سریع برگشت از فروش مشتریان",
        "description": "View اصلی برگشت از فروش مشتریان؛ مکمل فروش برای محاسبهٔ فروش خالص.",
        "domain": "فروش و مشتری", "classification": "customer_sales", "seller_access": "customer_scope",
        "aliases": ["برگشت از فروش", "مرجوعی فروش", "فروش خالص"],
    },
    "dbo.customercardex_info": {
        "persian_name": "گردش حساب مشتری",
        "description": "کاردکس بدهکار/بستانکار مشتریان؛ فقط با محدودهٔ مشتری مجاز فروشنده.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "customer_scope",
        "aliases": ["کاردکس مشتری", "گردش مشتری", "بدهکار بستانکار مشتری"],
    },
    "acc.vwrcvpaymentsreview": {
        "persian_name": "گزارش دریافت‌های مشتریان",
        "description": "دریافت و وصول مشتریان؛ فقط در محدودهٔ مشتری مجاز فروشنده.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "customer_scope",
        "aliases": ["دریافتی مشتری", "وصول مشتری", "پرداخت مشتری"],
    },
    "acc.vwrcvsalereview": {
        "persian_name": "مانده و وضعیت تسویه فاکتور مشتری",
        "description": "View عملیاتی فاکتور مشتری با مبلغ خالص، مبلغ تسویه، مانده و وضعیت پرداخت.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "customer_scope",
        "aliases": ["مانده فاکتور", "فاکتور باز", "وضعیت تسویه", "RemainingAmount", "PaymentStatus"],
    },
    "dbo.vwreview_rcvaccountsale2": {
        "persian_name": "گزارش رسمی فاکتورهای حساب مشتری",
        "description": "View متناظر تب رسمی فاکتور در مرور حساب مشتری؛ دارای مانده، وضعیت تسویه و اجزای پرداخت.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "customer_scope",
        "aliases": ["مرور فاکتور مشتری", "مانده فاکتور", "وضعیت پرداخت فاکتور"],
    },
    "dbo.vwreview_rcvaccountpayment2": {
        "persian_name": "گزارش رسمی اقلام حساب مشتری",
        "description": "اقلام بدهکار و بستانکار حساب مشتری در مرور رسمی ورانگر.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "customer_scope",
        "aliases": ["اقلام حساب مشتری", "پرداخت مشتری", "بدهکار بستانکار"],
    },
    "dbo.vwreview_rcvaccountsettlement2": {
        "persian_name": "جزئیات تسویه فاکتور مشتری",
        "description": "اتصال قلم تسویه، دریافت، چک، برگشت یا تعدیل به فاکتور مشتری.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "customer_scope",
        "aliases": ["تسویه فاکتور", "اقلام تسویه", "تخصیص دریافت"],
    },
    "dbo.vwreview_rcvaccountcardex2": {
        "persian_name": "کاردکس رسمی مشتری",
        "description": "گردش بدهکار و بستانکار اسناد مشتری و مانده تجمعی.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "customer_scope",
        "aliases": ["کاردکس مشتری", "گردش حساب مشتری", "مانده تجمعی"],
    },
    "dbo.receipt2": {
        "persian_name": "دریافت‌های خزانه",
        "description": "دریافت وجه و اسناد خزانه، اجزای نقد/چک/حواله بانکی، مبلغ مصرف‌شده و مانده دریافت.",
        "domain": "خزانه و بانک", "classification": "treasury", "seller_access": "restricted",
        "aliases": ["دریافت خزانه", "رسید دریافت", "مانده دریافت", "ReceiptRemainAmount"],
    },
    "dbo.vwreview_treasuryreceipt2": {
        "persian_name": "گزارش رسمی دریافت خزانه",
        "description": "View متناظر تب رسمی دریافت در مرور خزانه‌داری ورانگر.",
        "domain": "خزانه و بانک", "classification": "treasury", "seller_access": "restricted",
        "aliases": ["مرور دریافت خزانه", "دریافت باز", "گزارش وصول"],
    },
    "dbo.settlementfast": {
        "persian_name": "جزئیات سریع تسویه",
        "description": "نوع و مبلغ تسویه، علامت اثر، سند دریافت و فاکتور مرتبط.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "restricted",
        "aliases": ["تسویه", "تسویه فاکتور", "نوع تسویه", "PayTypePlusMinus"],
    },
    "dbo.invoicereceipt": {
        "persian_name": "ارتباط دریافت و فاکتور",
        "description": "پل مستقیم شناسه دریافت خزانه و شناسه فاکتور.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "restricted",
        "aliases": ["تخصیص دریافت", "دریافت فاکتور", "InvoiceId ReceiptId"],
    },
    "sle.ordersreview": {
        "persian_name": "گزارش درخواست‌ها و سفارش‌های مشتری",
        "description": "درخواست مشتری، اقلام، وضعیت تبدیل به فروش، فروشنده، شعبه و مسیر.",
        "domain": "فروش و مشتری", "classification": "customer_sales", "seller_access": "restricted",
        "aliases": ["درخواست مشتری", "سفارش مشتری", "وضعیت سفارش", "تبدیل درخواست"],
    },
    "acc.vwcustomerbalance": {
        "persian_name": "مانده حساب مشتریان",
        "description": "مانده حساب مشتریان؛ فقط در محدودهٔ مشتری مجاز فروشنده.",
        "domain": "فروش و مشتری", "classification": "customer_collections", "seller_access": "customer_scope",
        "aliases": ["مانده مشتری", "بدهی مشتری", "مطالبات مشتری"],
    },
    "gnr.vwcust": {
        "persian_name": "فهرست و طبقه‌بندی مشتریان",
        "description": "مرجع مشتری، شعبه و لاین فروش؛ برای اعمال محدودهٔ دسترسی مشتری استفاده می‌شود.",
        "domain": "فروش و مشتری", "classification": "customer_master", "seller_access": "customer_scope",
        "aliases": ["مشتریان", "شعبه مشتری", "لاین مشتری"],
    },
    "gnr.tblgoods": {
        "persian_name": "کالای پایه",
        "description": "مرجع اصلی کالا برای اتصال فروش و گزارش‌های انبار.",
        "domain": "کالا و انبار", "classification": "product_reference", "seller_access": "reference",
        "aliases": ["کالا", "محصول", "فهرست کالا"],
    },
    "gnr.tblgoodsgroup": {
        "persian_name": "گروه کالا",
        "description": "دسته‌بندی و گروه‌بندی کالاها.",
        "domain": "کالا و انبار", "classification": "product_reference", "seller_access": "reference",
        "aliases": ["دسته کالا", "گروه محصول"],
    },
    "gnr.tblbrand": {
        "persian_name": "برند کالا",
        "description": "مرجع برند کالاها.",
        "domain": "کالا و انبار", "classification": "product_reference", "seller_access": "reference",
        "aliases": ["برند", "نام تجاری"],
    },
    "gnr.tblmanufacturer": {
        "persian_name": "تولیدکننده کالا",
        "description": "مرجع تولیدکننده کالاها؛ با برند متفاوت است.",
        "domain": "کالا و انبار", "classification": "product_reference", "seller_access": "reference",
        "aliases": ["تولیدکننده", "سازنده کالا"],
    },
    "dbo.vwreview_sellproduct2": {
        "persian_name": "گزارش فروش به تفکیک کالا",
        "description": "گزارش تحلیلی فروش کالا؛ برای کاربران داخلی و مدیران.",
        "domain": "فروش و مشتری", "classification": "customer_sales", "seller_access": "restricted",
        "aliases": ["فروش کالا", "فروش محصول"],
    },
    "dbo.vwreview_sellproductgroup2": {
        "persian_name": "گزارش فروش به تفکیک گروه کالا",
        "description": "گزارش تحلیلی فروش بر مبنای گروه کالا؛ برای کاربران داخلی و مدیران.",
        "domain": "فروش و مشتری", "classification": "customer_sales", "seller_access": "restricted",
        "aliases": ["فروش گروه کالا", "فروش دسته کالا"],
    },
    "dbo.vwreview_stockproduct2": {
        "persian_name": "گزارش موجودی به تفکیک کالا",
        "description": "گزارش موجودی کالا در سطح سازمان؛ شامل محدودهٔ مشتری نیست.",
        "domain": "کالا و انبار", "classification": "inventory", "seller_access": "restricted",
        "aliases": ["موجودی کالا", "موجودی محصول"],
    },
    "dbo.vwreview_stockproductgroup2": {
        "persian_name": "گزارش موجودی به تفکیک گروه کالا",
        "description": "گزارش موجودی بر مبنای گروه کالا در سطح سازمان.",
        "domain": "کالا و انبار", "classification": "inventory", "seller_access": "restricted",
        "aliases": ["موجودی گروه کالا", "موجودی دسته کالا"],
    },
    "dbo.vwreview_stockcardex2": {
        "persian_name": "گردش موجودی کالا",
        "description": "کاردکس و گردش انبار کالا در سطح سازمان.",
        "domain": "کالا و انبار", "classification": "inventory", "seller_access": "restricted",
        "aliases": ["کاردکس کالا", "گردش انبار"],
    },
}


def source_key(schema: str, name: str) -> str:
    return f"{schema}.{name}".casefold()


def _words(value: str) -> list[str]:
    return [word.casefold() for word in _WORD_RE.findall(value.replace("_", " "))]


def persian_label(value: str, *, fallback: str) -> str:
    exact = _EXACT_PERSIAN_LABELS.get(value.casefold())
    if exact:
        return exact
    translated = [_PERSIAN_WORDS[word] for word in _words(value) if word in _PERSIAN_WORDS]
    return " ".join(dict.fromkeys(translated)) or fallback


def column_persian_label(
    value: str, *, relationship_label: str | None = None
) -> tuple[str, str, str | None]:
    """Translate a column conservatively and retain its confidence for review."""
    key = value.casefold()
    exact = _EXACT_PERSIAN_LABELS.get(key)
    if exact:
        return exact, "verified", None
    if relationship_label:
        return relationship_label, "verified", "foreign_key"
    words = _words(value)
    normalized = [word.casefold() for word in words]
    if not normalized or any(not word.isdigit() and word not in _COLUMN_WORDS for word in normalized):
        unknown = [word for word in normalized if not word.isdigit() and word not in _COLUMN_WORDS]
        return value, "needs_review", "unknown_terms:" + ",".join(unknown or normalized)
    def translated_word(word: str) -> str:
        return word if word.isdigit() else _COLUMN_WORDS[word]
    if normalized[-1] in {"id", "ref"}:
        subject = " ".join(translated_word(word) for word in normalized[:-1])
        if subject:
            return f"شناسه {subject}", "inferred", "identifier_suffix"
    if normalized[-1] == "name":
        subject = " ".join(translated_word(word) for word in normalized[:-1])
        if subject:
            return f"نام {subject}", "inferred", "name_suffix"
    if normalized[-1] == "code":
        subject = " ".join(translated_word(word) for word in normalized[:-1])
        if subject:
            return f"کد {subject}", "inferred", "code_suffix"
    if normalized[0] == "is" and len(normalized) > 1:
        return " ".join(translated_word(word) for word in normalized[1:]), "inferred", "boolean_prefix"
    return " ".join(translated_word(word) for word in normalized), "inferred", "token_dictionary"


def view_voucher_context_label(item: dict[str, Any], column_name: str) -> str | None:
    """Choose the business meaning of a generic voucher number/date in a View.

    SQL Server does not expose dependencies for the review Views in this
    database, so the report/module identity is the available reliable context.
    This applies only to generic Voucher/Vch/Vocher number and date fields;
    more specific field names keep their official Varanegar resource label.
    """
    if str(item.get("type") or "").upper() != "VIEW":
        return None
    field = column_name.casefold().replace("_", "")
    number_fields = {"voucherno", "vocherno", "vchno"}
    date_fields = {"voucherdate", "vocherdate", "vchdate"}
    if field not in number_fields | date_fields:
        return None
    references = " ".join(
        f"{reference.get('schema', '')} {reference.get('name', '')}"
        for reference in list(item.get("referenced_tables") or [])
    )
    source = f"{item.get('schema', '')} {item.get('name', '')} {references}".casefold()
    if any(marker in source for marker in ("loan", "amani")):
        return "شماره حواله امانی" if field in number_fields else "تاریخ حواله امانی"
    if any(marker in source for marker in ("return", "retsale", "retinvoice")):
        return "شماره حواله برگشتی" if field in number_fields else "تاریخ حواله برگشتی"
    if any(marker in source for marker in ("stock", "warehouse", "ica", "inv")):
        return "شماره سند انبار" if field in number_fields else "تاریخ سند انبار"
    if any(marker in source for marker in ("sell", "sale", "dist")):
        return "شماره حواله" if field in number_fields else "تاریخ حواله"
    return None


def view_varanegar_resource_label(
    item: dict[str, Any], column_name: str,
    candidates: dict[str, list[tuple[str, str]]],
) -> str | None:
    """Use the Varanegar module that matches a View's referenced tables."""
    if str(item.get("type") or "").upper() != "VIEW":
        return None
    options = candidates.get(column_name.casefold(), [])
    if not options:
        return None
    references = " ".join(
        f"{reference.get('schema', '')} {reference.get('name', '')}"
        for reference in list(item.get("referenced_tables") or [])
    )
    context = f"{item.get('schema', '')} {item.get('name', '')} {references}".casefold()
    resource_order: list[str] = []
    if any(marker in context for marker in ("loan", "amani")):
        resource_order.append("LoanResources")
    if any(marker in context for marker in ("stock", "warehouse", "goods", "ica", "inv")):
        resource_order.extend(("StockResources", "WhAccountResource", "BaseInformationResource"))
    if any(marker in context for marker in ("sell", "sale", "customer", "cust", "dealer", "dist")):
        resource_order.append("SalesResources")
    if any(marker in context for marker in ("buy", "purchase", "supplier", "supinvoice")):
        resource_order.append("BuyResource")
    if any(marker in context for marker in ("acc", "ledger", "gl", "voucher")):
        resource_order.append("GeneralLedger")
    if any(marker in context for marker in ("bank", "cheque", "treasury", "receipt", "payment")):
        resource_order.extend(("TreasuryResources", "RcvAccountResources", "TreasuryFundResources"))
    for resource_hint in resource_order:
        labels = {label for resource, label in options if resource_hint in resource}
        if len(labels) == 1:
            return labels.pop()
    return None


def account_name_context_label(item: dict[str, Any], column_name: str) -> tuple[str, str, str] | None:
    """Resolve the reused ``AccountName`` field from its business context.

    In the Varanegar review resources, ``AccountName`` is the *bank account
    holder* label.  SQL also reuses the same technical name in accounting
    account Views (for example ``Acc.vwExpenseAccount``), where it means the
    name of the ledger/account itself.  A global resource lookup would make
    the latter incorrectly display as "صاحب حساب".
    """
    if column_name.casefold() != "accountname":
        return None
    references = " ".join(
        f"{reference.get('schema', '')} {reference.get('name', '')}"
        for reference in list(item.get("referenced_tables") or [])
    )
    context = f"{item.get('schema', '')} {item.get('name', '')} {references}".casefold()
    if any(marker in context for marker in ("bank", "cheque", "rcvaccount", "treasury")):
        # Captured from Varanegar's bank-account/cheque grids; the resource
        # wording is "صاحب حساب" and the grid caption is "نام صاحب حساب".
        return "نام صاحب حساب", "verified", "varanegar_review_grid"
    if str(item.get("schema") or "").casefold() == "acc" or any(
        marker in context for marker in ("expenseaccount", "ledger", "gl")
    ):
        return "نام حساب", "inferred", "accounting_object_context"
    return None


def infer_domain(schema: str, name: str) -> str:
    schema_key = schema.casefold()
    # Schema identity is stronger than a substring in an object name.  In
    # particular, `acc` must not match unrelated names such as AccessLog.
    if schema_key == "acc":
        if any(marker in name.casefold() for marker in ("bank", "cheque", "treasury")):
            return "خزانه و بانک"
        return "مالی و حسابداری"
    haystack = f"{schema} {name}".casefold()
    for domain, markers in _DOMAIN_MARKERS:
        if any(marker in haystack for marker in markers):
            return domain
    schema_domains = {
        "acc": "مالی و حسابداری",
        "ica": "خرید و تأمین",
        "inv": "کالا و انبار",
        "sle": "فروش و مشتری",
        "rpt": "گزارش و تحلیل",
        "hsp": "مدیریت کاربران و امنیت",
        "grs": "منابع انسانی و سازمان",
        "grs_": "منابع انسانی و سازمان",
        "pol": "بازاریابی و توزیع",
        "ngt": "بازاریابی و توزیع",
        "cmr": "قراردادها و تأمین",
        "gnr": "داده‌های پایه",
        "fru": "تنظیمات و گردش کار",
    }
    return schema_domains.get(schema_key, "تنظیمات و گردش کار")


def infer_access_class(schema: str, name: str) -> str:
    source = source_key(schema, name)
    if source in SELLER_CUSTOMER_SOURCES:
        return "customer_scope"
    if source in SELLER_REFERENCE_SOURCES:
        return "reference"
    if any(marker in source for marker in _RESTRICTED_MARKERS):
        return "restricted"
    return "restricted"


def infer_classification(schema: str, name: str) -> str:
    source = source_key(schema, name)
    if source in SELLER_REFERENCE_SOURCES:
        return "product_reference"
    if source in SELLER_CUSTOMER_SOURCES:
        if any(marker in source for marker in ("payment", "balance", "cardex", "rcv", "history")):
            return "customer_collections"
        if source == "gnr.vwcust" or source.endswith(".customer"):
            return "customer_master"
        return "customer_sales"
    if any(marker in source for marker in ("stock", "inventory", "warehouse", "cardex")):
        return "inventory"
    if any(marker in source for marker in ("buy", "purchase", "supplier")):
        return "purchase"
    if any(marker in source for marker in ("bank", "cheque", "treasury")):
        return "treasury"
    if schema.casefold() == "acc" or any(marker in source for marker in ("account", "ledger", "journal")):
        return "finance"
    if any(marker in source for marker in ("user", "role", "access", "permission", "token", "claim")):
        return "system_security"
    if any(marker in source for marker in ("personnel", "employee", "payroll", "salary")):
        return "personnel"
    domain_classes = {
        "فروش و مشتری": "customer_sales",
        "کالا و انبار": "inventory",
        "خرید و تأمین": "purchase",
        "قراردادها و تأمین": "purchase",
        "مالی و حسابداری": "finance",
        "خزانه و بانک": "treasury",
        "منابع انسانی و سازمان": "personnel",
        "مدیریت کاربران و امنیت": "system_security",
        "بازاریابی و توزیع": "marketing_distribution",
        "گزارش و تحلیل": "reporting",
        "داده‌های پایه": "master_data",
        "تنظیمات و گردش کار": "workflow_configuration",
    }
    return domain_classes.get(infer_domain(schema, name), "needs_review")


def _automatic_catalog(item: dict[str, Any]) -> dict[str, Any]:
    schema = str(item.get("schema") or "")
    name = str(item.get("name") or "")
    object_type = str(item.get("type") or "OBJECT").upper()
    kind = "نمای" if object_type == "VIEW" else "جدول"
    label = persian_label(name, fallback=f"{kind} {name}")
    aliases = list(dict.fromkeys([label, name, *(_words(name))]))
    automatic = {
        "persian_name": label,
        "description": f"{kind} {label} در حوزهٔ {infer_domain(schema, name)}.",
        "domain": infer_domain(schema, name),
        "classification": infer_classification(schema, name),
        "seller_access": infer_access_class(schema, name),
        "aliases": aliases,
    }
    curated = _CURATED_OBJECTS.get(source_key(schema, name))
    if not curated:
        return automatic
    return {**automatic, **curated, "aliases": list(dict.fromkeys([*curated["aliases"], *aliases]))}


def sync_schema_catalog(settings: Settings) -> dict[str, int]:
    """Enrich the cached schema and retain any curator-approved catalog overrides."""
    now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute("SELECT schema_name, object_name, details_json FROM schema_objects").fetchall()
        # The Varanegar language pack is a first-party vocabulary.  Use a
        # global label only when *every* module gives the technical name the
        # same Persian meaning.  A majority vote is unsafe: names such as
        # VoucherNo, Amount and DCName are intentionally reused by different
        # modules with different captions.  Those are resolved from the
        # View/table context below, or retained for review when context is
        # insufficient.
        varanegar_labels = {
            str(row["technical_name"]).casefold(): str(row["persian_name"])
            for row in conn.execute(
                """WITH label_consensus AS (
                       SELECT technical_name COLLATE NOCASE AS technical_name,
                              MIN(persian_name) AS persian_name,
                              COUNT(DISTINCT persian_name) AS meaning_count
                       FROM varanegar_column_labels
                       GROUP BY technical_name COLLATE NOCASE, persian_name
                   )
                   SELECT technical_name, MIN(persian_name) AS persian_name
                   FROM label_consensus
                   GROUP BY technical_name
                   HAVING SUM(meaning_count) = 1"""
            ).fetchall()
        }
        varanegar_candidates: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for label_row in conn.execute(
            "SELECT resource_name, technical_name, persian_name FROM varanegar_column_labels"
        ).fetchall():
            varanegar_candidates[str(label_row["technical_name"]).casefold()].append(
                (str(label_row["resource_name"]), str(label_row["persian_name"]))
            )
        items_by_key = {
            (str(row["schema_name"]).casefold(), str(row["object_name"]).casefold()): json.loads(row["details_json"])
            for row in rows
        }
        existing = {
            (row["schema_name"].casefold(), row["object_name"].casefold()): row
            for row in conn.execute("SELECT * FROM schema_catalog").fetchall()
        }
        updated = 0
        automatic = 0
        review_items: dict[str, dict[str, Any]] = {}
        for row in rows:
            item = json.loads(row["details_json"])
            key = (str(row["schema_name"]).casefold(), str(row["object_name"]).casefold())
            calculated = _automatic_catalog(item)
            prior = existing.get(key)
            if prior and prior["is_manual"]:
                catalog = {
                    "persian_name": prior["persian_name"],
                    "description": prior["description"],
                    "domain": prior["domain"],
                    "classification": prior["data_classification"],
                    "seller_access": prior["seller_access"],
                    "aliases": json.loads(prior["aliases_json"]),
                }
            else:
                catalog = calculated
                automatic += 1
            item["catalog"] = catalog
            relationship_labels: dict[str, str] = {}
            relationship_conflicts: set[str] = set()
            for foreign_key in list(item.get("foreign_keys") or []):
                source_column = str(foreign_key.get("column") or "")
                target_key = (
                    str(foreign_key.get("target_schema") or "").casefold(),
                    str(foreign_key.get("target_table") or "").casefold(),
                )
                target = items_by_key.get(target_key)
                if not source_column or not target:
                    continue
                target_catalog = dict(target.get("catalog") or _automatic_catalog(target))
                target_name = str(target_catalog.get("persian_name") or foreign_key.get("target_table") or "")
                label = f"شناسه {target_name}"
                column_key = source_column.casefold()
                if column_key in relationship_labels and relationship_labels[column_key] != label:
                    relationship_conflicts.add(column_key)
                else:
                    relationship_labels[column_key] = label

            translated_columns = []
            for column in list(item.get("columns") or []):
                column_name = str(column.get("name") or "")
                official_label = str(column.get("official_persian_name") or "").strip()
                # Some technical names are intentionally reused by Varanegar
                # in different modules.  They must be resolved from the
                # object context, never from a database-wide majority vote.
                varanegar_label = (
                    None if column_name.casefold() == "accountname"
                    else varanegar_labels.get(column_name.casefold())
                )
                contextual_label = view_voucher_context_label(item, column_name)
                contextual_varanegar_label = view_varanegar_resource_label(
                    item, column_name, varanegar_candidates
                )
                account_label = account_name_context_label(item, column_name)
                relation_label = None if column_name.casefold() in relationship_conflicts else relationship_labels.get(column_name.casefold())
                # Varanegar's Persian review vocabulary is the requested
                # primary display language. SQL descriptions remain the next
                # authoritative fallback when a review term is unavailable.
                if contextual_label:
                    label, status, reason = contextual_label, "verified", "view_module_context"
                elif account_label:
                    label, status, reason = account_label
                elif contextual_varanegar_label:
                    label, status, reason = contextual_varanegar_label, "verified", "view_table_context"
                elif official_label:
                    label, status, reason = official_label, "verified", "sql_server_ms_description"
                elif varanegar_label:
                    label, status, reason = varanegar_label, "verified", "varanegar_fa_resource"
                else:
                    label, status, reason = column_persian_label(column_name, relationship_label=relation_label)
                enriched = {**column, "persian_name": label, "translation_status": status}
                if reason:
                    enriched["translation_reason"] = reason
                translated_columns.append(enriched)
                if status == "needs_review":
                    review_key = column_name.casefold()
                    entry = review_items.setdefault(review_key, {
                        "column_name": column_name, "occurrence_count": 0, "sample_sources": [],
                        "suggested_label": label, "reason": reason or "unknown",
                    })
                    entry["occurrence_count"] += 1
                    source = f"{row['schema_name']}.{row['object_name']}"
                    if source not in entry["sample_sources"] and len(entry["sample_sources"]) < 5:
                        entry["sample_sources"].append(source)
            item["columns"] = translated_columns
            conn.execute(
                """INSERT INTO schema_catalog
                   (schema_name, object_name, persian_name, description, domain, seller_access,
                    data_classification, aliases_json, is_manual, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                   ON CONFLICT(schema_name, object_name) DO UPDATE SET
                     persian_name=excluded.persian_name, description=excluded.description,
                     domain=excluded.domain, seller_access=excluded.seller_access,
                     data_classification=excluded.data_classification,
                     aliases_json=excluded.aliases_json, updated_at=excluded.updated_at
                   WHERE schema_catalog.is_manual=0""",
                 (row["schema_name"], row["object_name"], catalog["persian_name"],
                 catalog["description"], catalog["domain"], catalog["seller_access"], catalog["classification"],
                 json.dumps(catalog["aliases"], ensure_ascii=False), now),
            )
            conn.execute(
                "UPDATE schema_objects SET details_json=? WHERE schema_name=? AND object_name=?",
                (json.dumps(item, ensure_ascii=False), row["schema_name"], row["object_name"]),
            )
            updated += 1
        conn.execute("DELETE FROM schema_translation_review")
        conn.executemany(
            """INSERT INTO schema_translation_review
               (column_name, occurrence_count, sample_sources_json, suggested_label, reason, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (entry["column_name"], entry["occurrence_count"], json.dumps(entry["sample_sources"], ensure_ascii=False),
                 entry["suggested_label"], entry["reason"], now)
                for entry in review_items.values()
            ],
        )
    return {"cataloged_objects": updated, "automatic_labels": automatic}


def translation_stats(settings: Settings) -> dict[str, int]:
    """Return coverage based on unique technical column names and all occurrences."""
    by_name: dict[str, str] = {}
    occurrence_statuses: Counter[str] = Counter()
    object_count = 0
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute("SELECT details_json FROM schema_objects").fetchall()
    for row in rows:
        object_count += 1
        item = json.loads(row["details_json"])
        for column in list(item.get("columns") or []):
            name = str(column.get("name") or "")
            status = str(column.get("translation_status") or "needs_review")
            by_name.setdefault(name.casefold(), status)
            occurrence_statuses[status] += 1
    unique_statuses = Counter(by_name.values())
    translated_statuses = ("verified", "inferred")
    return {
        "objects": object_count,
        "column_instances": sum(occurrence_statuses.values()),
        "unique_column_names": len(by_name),
        "translated_unique_names": sum(unique_statuses[status] for status in translated_statuses),
        "translated_column_instances": sum(occurrence_statuses[status] for status in translated_statuses),
        "verified_unique_names": unique_statuses["verified"],
        "inferred_unique_names": unique_statuses["inferred"],
        "review_unique_names": unique_statuses["needs_review"],
        "review_column_instances": occurrence_statuses["needs_review"],
    }


def translation_review(settings: Settings, limit: int = 200) -> list[dict[str, Any]]:
    with sqlite_connection(settings.sqlite_path) as conn:
        rows = conn.execute(
            """SELECT column_name, occurrence_count, sample_sources_json, suggested_label, reason
               FROM schema_translation_review ORDER BY occurrence_count DESC, column_name LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {**dict(row), "sample_sources": json.loads(row["sample_sources_json"])}
        for row in rows
    ]


def update_catalog_entry(settings: Settings, schema: str, name: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    with sqlite_connection(settings.sqlite_path) as conn:
        row = conn.execute(
            "SELECT details_json FROM schema_objects WHERE schema_name=? COLLATE NOCASE AND object_name=? COLLATE NOCASE",
            (schema, name),
        ).fetchone()
        if row is None:
            return None
        item = json.loads(row["details_json"])
        current = dict(item.get("catalog") or _automatic_catalog(item))
        for field in ("persian_name", "description", "domain", "classification", "seller_access", "aliases"):
            if field in payload and payload[field] is not None:
                current[field] = payload[field]
        if current["seller_access"] not in {"restricted", "customer_scope", "reference"}:
            raise ValueError("seller_access must be restricted, customer_scope, or reference")
        if current["classification"] not in _CLASSIFICATIONS:
            raise ValueError("classification is not valid")
        current["aliases"] = list(dict.fromkeys(str(value).strip() for value in current["aliases"] if str(value).strip()))
        now = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        conn.execute(
            """INSERT INTO schema_catalog
               (schema_name, object_name, persian_name, description, domain, seller_access,
                data_classification, aliases_json, is_manual, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
               ON CONFLICT(schema_name, object_name) DO UPDATE SET
                 persian_name=excluded.persian_name, description=excluded.description,
                 domain=excluded.domain, seller_access=excluded.seller_access,
                 data_classification=excluded.data_classification,
                 aliases_json=excluded.aliases_json, is_manual=1, updated_at=excluded.updated_at""",
            (schema, name, current["persian_name"], current["description"], current["domain"],
             current["seller_access"], current["classification"], json.dumps(current["aliases"], ensure_ascii=False), now),
        )
        item["catalog"] = current
        conn.execute(
            "UPDATE schema_objects SET details_json=? WHERE schema_name=? COLLATE NOCASE AND object_name=? COLLATE NOCASE",
            (json.dumps(item, ensure_ascii=False), schema, name),
        )
    return current
