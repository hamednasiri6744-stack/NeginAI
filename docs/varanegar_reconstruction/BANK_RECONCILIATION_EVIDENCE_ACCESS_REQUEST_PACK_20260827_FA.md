# بستهٔ درخواست شواهد و دسترسی مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS طراحی؛ هیچ دسترسی یا Approval جدیدی اعطا نشده است**

## نتیجه

نه درخواست دقیق با مالک، حداقل دسترسی، موارد ممنوع، Gate قابل‌رفع و وضعیت فعلی
ثبت شد. هر سطح اولویت سه درخواست دارد:

1. Snapshot تازهٔ READ_ONLY دارای Fixture، Profile/Sample file Redacted و Fixture
   یازده‌خروجی Summary؛
2. تصمیم‌های هفت‌گانه مالک، Provision هفت Principal slot و Fixtureهای UAT؛
3. محیط Failure injection مقصد، Telemetry allowlisted سه Root و تصمیم Scope مالک.

هیچ Production write grant لازم نیست. DBA Clone را می‌سازد ولی Login تحلیلگر
SELECT-only/Deny-write می‌ماند؛ Identity/Credential فقط در IdP/Secret store است؛
UAT write فقط روی Target disposable انجام می‌شود؛ Telemetry Root هیچ Business
value/Identity/SQL/Path یا UI command ندارد.

## ترتیب پیشنهادی

`001+002 → 003+004 → 005+006 → 007 → 008+009`

در Snapshot فعلی Runtime fixture، Owner approval، UAT account/execution، Root
closure و Target command execution همگی صفرند. این Pack درخواست می‌کند؛ چیزی را
اعطا، اجرا یا تأیید نمی‌کند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_evidence_request_pack_20260827.json`
- `scripts/windows/build_negin_erp_bank_reconciliation_evidence_request_pack.py`
- `tests/test_varanegar_ui_evidence.py`
