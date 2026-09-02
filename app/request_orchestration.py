"""Deterministic request routing for the conversational data assistant."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Literal


RequestMode = Literal["conversation", "company_data", "automation"]


@dataclass(frozen=True)
class RequestPlan:
    mode: RequestMode
    needs_company_data: bool
    needs_live_workspace: bool
    reason: str

    def trusted_context(self) -> dict[str, object]:
        return asdict(self)


_NORMAL_TRANSLATION = str.maketrans({"ي": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه"})
_GREETING_RE = re.compile(
    r"^\s*(?:سلام|درود|صبح\s+بخیر|ظهر\s+بخیر|عصر\s+بخیر|شب\s+بخیر|خسته\s+نباش(?:ی|ید)?|"
    r"ممنون|مرسی|سپاس|خداحافظ|فعلا|فعلاً|سلام\s+(?:خوبی|چطوری)|درود\s+بر\s+شما)"
    r"[\s!؟?.،]*$",
    re.IGNORECASE,
)
_AUTOMATION_RE = re.compile(
    r"هر\s+(?:ساعت|روز|هفته|ماه)|خودکار|اتومات|یادآوری|اطلاع\s*بده|نوتیف|"
    r"اگر.*(?:شد|رسید).*خبر|(?:ساعت|روزانه|هفتگی|ماهانه).*گزارش",
    re.IGNORECASE,
)
_COMPANY_DATA_RE = re.compile(
    r"فروش|فاکتور|حواله|برگشت|مرجوع|مشتری|کاردکس|مانده|وصول|دریافت|تسویه|"
    r"سفارش|توزیع|پخش|انبار|موجودی|کالا|محصول|برند|تولیدکننده|بازاریاب|فروشنده|"
    r"سرپرست|تیم|شعبه|لاین|خط\s+فروش|مسیر|ویزیت|تور|سود|حاشیه|قیمت\s+خرید|"
    r"پرسنل|حقوق|تأمین|تامین|خزانه|حسابداری|گزارش|آمار|عملکرد|دیتابیس|پایگاه\s+داده|"
    r"جدول|ویو|بودجه|برنامه[‌\s-]*ریزی|پیش[‌\s-]*بینی|سناریو|فرض(?:یات)?|هدف|انحراف|"
    r"sql|invoice|sales|customer|inventory|route|brand|budget|forecast|scenario|planning|database",
    re.IGNORECASE,
)
_FIRST_PERSON_WORKSPACE_RE = re.compile(
    r"(?:^|\s)(?:من|خودم|مال\s+من|برای\s+من|برند(?:ها)?م|مسیر(?:ها)?م|"
    r"تیمم|سرپرستم|شعبه(?:‌|\s)?م|لاین(?:‌|\s)?م|فروشم)(?:\s|$)",
    re.IGNORECASE,
)


def _normalize(value: str) -> str:
    return " ".join(str(value or "").translate(_NORMAL_TRANSLATION).casefold().split())


def plan_request(message: str, history: list[dict[str, str]] | None = None) -> RequestPlan:
    """Classify whether the current turn needs company data before retrieval.

    The classifier is intentionally conservative: uncertain requests stay in the
    normal conversational agent, which can still elect to use a tool.  Its main
    job is to keep obvious small-talk turns from eagerly loading schema context.
    """

    normalized = _normalize(message)
    if _AUTOMATION_RE.search(normalized):
        return RequestPlan("automation", False, False, "automation_management")
    if _GREETING_RE.fullmatch(normalized):
        return RequestPlan("conversation", False, False, "obvious_small_talk")
    if _COMPANY_DATA_RE.search(normalized):
        return RequestPlan(
            "company_data",
            True,
            bool(_FIRST_PERSON_WORKSPACE_RE.search(normalized)),
            "explicit_company_data_terms",
        )

    recent = " ".join(
        _normalize(item.get("content", ""))
        for item in (history or [])[-4:]
        if item.get("role") in {"user", "assistant"}
    )
    words = normalized.split()
    if len(words) <= 12 and recent and _COMPANY_DATA_RE.search(recent):
        return RequestPlan(
            "company_data",
            True,
            bool(_FIRST_PERSON_WORKSPACE_RE.search(normalized)),
            "short_followup_to_company_data",
        )
    return RequestPlan("conversation", False, False, "no_company_data_signal")
