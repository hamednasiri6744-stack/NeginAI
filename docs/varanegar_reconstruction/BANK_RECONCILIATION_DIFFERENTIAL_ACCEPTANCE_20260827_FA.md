# تعهدات Acceptance تفاضلی مغایرت بانکی ERP نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS طراحی؛ ۱۱۶ Case ساخته شد، اجرای واقعی و Owner approval صفر است**

## چرا این Artifact لازم است؟

کشف فرمول، Parser و Defect Confirm اگر فقط در سند بماند هنگام ساخت وب به‌سادگی
فراموش می‌شود. این Artifact آن‌ها را به ۱۱۶ Case با ID پایدار، Fixture، Expected
result و Gate اجرا تبدیل می‌کند. این Caseها به شمارش ۹۷۰ Golden ماژولی افزوده
نشده‌اند تا «تعهد جدید» با «تست اجراشده» یا پوشش قبلی اشتباه نشود.

## ترکیب Caseها

| گروه | تعداد | پوشش |
|---|---:|---|
| Summary | ۳۸ | ۱۱ فرمول، Null، Branch مبنا، Date، Type/Status، Alias، Presentation |
| Parser | ۲۴ | Format، شش ستون، Amount، Dedup، Atomicity، فیلد Profile |
| Confirm/Unmatch/Reverse/Cancel | ۵۴ | Type/Multi-link/Fault/Auth، Unmatch/Reverse و Discard/Cancel |

از ۱۱۶ Case، تعداد ۴۱ نیازمند Fixture واقعی Redacted، ۱۲ نیازمند تصمیم مالک، ۱۱
نیازمند Failure injection و پنج مورد نیازمند UAT احراز‌شده‌اند. همهٔ آن‌ها اکنون
`NOT_EXECUTED` هستند.

## Regressionهای غیرقابل حذف

- `RBANKDARFT/RBANKDRAFT` و `RCASHDRAF/RCASHDRAFT` نباید بی‌صدا Normalize شوند.
- Parser نباید SQL خام Profile یا Office automation اجرا کند.
- Missing column و Parse/Validation failure باید صفر Persistence داشته باشد.
- Dedup باید Account/ProfileVersion/RowFingerprint را پوشش دهد.
- Multi-link Confirm باید همهٔ Instrumentها را Update کند؛ تست باید صریحاً وقتی
  affected instrument count برابر یک است Fail شود.
- Markerهای Confirm باید روی هر Link failure Rollback شوند.
- Unauthorized، Closed date و Stale version باید قبل از Mutation رد شوند.
- Unmatch نباید همهٔ Linkهای BankBill را پاک یا روی Confirmed state اجرا شود؛
  Reverse باید Instrumentها و Session را کامل و اتمیک برگرداند.
- Reverse مجوز مستقل، SoD، تاریخ عملیات، State، Version و Idempotency دارد و
  شکست Audit/Outbox نیز باید کل تغییرات را Rollback کند.
- Discard ردیف‌ها نباید Header فعال یتیم بگذارد؛ Cancel باید Header/Rows را
  Transition/Archive و Replay/Stale version را کنترل کند.

## سیاست اجرا

- Varanegar همیشه فقط‌خواندنی است؛ Legacy side فقط Fixture Redacted موردتأیید یا
  Query تجمیعی می‌گیرد.
- Target side فقط روی Test database ایزوله اجرا می‌شود.
- Caseهای Owner-pending ابتدا باید تصمیم داشته باشند؛ Caseهای دیگر باید پیش از
  Pilot Pass شوند.
- Differential parity مجوز بازتولید SQL ناامن، Partial commit یا Defect یک‌لینکی نیست.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_differential_acceptance_20260827.json`
- `scripts/windows/build_negin_erp_bank_reconciliation_differential_acceptance.py`
- `tests/test_varanegar_ui_evidence.py`

این Artifact هیچ Identity، Profile row، Statement row یا نتیجهٔ مغایرت واقعی را
استفاده نمی‌کند و هیچ Commandی اجرا نکرده است.
