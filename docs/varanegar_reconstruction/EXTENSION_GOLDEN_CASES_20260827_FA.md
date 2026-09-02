# Golden caseهای Extension برای ERP مقصد

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS — ۲۱۵ مشخصات تست مصنوعی، اجرای عملیاتی صفر**

این بسته، یازده Command و دو Query تعریف‌شده برای افزونه‌های POS/Tablet/Setting
را به Caseهای قابل‌خودکارسازی تبدیل می‌کند. مقصد اجرای Caseها Test harness ایزوله
ERP نگین است؛ اجرای آن‌ها روی وارانگار مجاز نیست.

## پوشش

| دسته | تعداد |
|---|---:|
| Happy path | ۱۳ |
| Authorization | ۱۳ |
| Scope | ۱۳ |
| Concurrency | ۱۱ |
| Idempotency | ۲۲ |
| Invariant | ۴۶ |
| Fault injection | ۴۴ |
| Reconciliation | ۴۵ |
| Pagination | ۲ |
| Freshness/cutoff | ۲ |
| Privacy | ۲ |
| Query no-mutation | ۲ |

جمع کل ۲۱۵ Case است و `legacy_execution_allowed` برای همه صفر است.

## Gate پذیرش Command

هر Command باید ثابت کند:

1. Actor بدون مجوز و Actor خارج از Scope پیش از Mutation رد می‌شوند.
2. `expected_version` قدیمی هیچ state جدیدی را overwrite نمی‌کند.
3. Retry همان `command_id` همان نتیجه نخست را بدون Event/Outbox تکراری می‌دهد.
4. Payload متفاوت با `command_id` مصرف‌شده، Idempotency conflict می‌گیرد.
5. Crash بعد از هر failure stage به Partial accepted outcome منجر نمی‌شود.
6. Reconciliation mismatch به‌صورت قطعی کشف و Quarantine می‌شود و Auto-fix ندارد.

## Gate پذیرش Query

برای صندوق و نشست POS، Case مستقل ثابت می‌کند که Query هیچ Command یا Data
mutation را فراخوانی نمی‌کند. علاوه بر Role/Scope، ترتیب Pagination، Watermark،
Staleness و عدم نشت Field حساس نیز آزموده می‌شود.

## محدودیت

این Caseها Spec هستند، نه نتیجه اجرای تست. Fixtureها، Expected valueهای مالی و
هویت‌های UAT باید با مالک فرایند تعیین شوند. پوشش قواعد شناخته‌شده نیز به‌تنهایی
قاعده کسب‌وکار کشف‌نشده را پیدا نمی‌کند.

منبع ماشین‌خوان:
`artifacts/varanegar_analysis/ui/varanegar_extension_golden_cases_20260827.json`

سازنده:
`scripts/windows/build_varanegar_extension_golden_cases.py`
