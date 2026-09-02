# قرارداد بستن سه Root حل‌نشده

## نتیجه

اسکن ایستای بیشتر با همان ورودی‌ها دیگر ارزش افزوده ندارد. ۶۲ Assembly و ۸۵۳
فایل Deployment با مجموع ۵۹۸٬۵۵۸٬۴۳۱ بایت بررسی شده‌اند و Reference بیرونی
برای هیچ‌یک از سه Root پیدا نشده است. این نبودن به معنی unused بودن یا مجوز حذف
نیست؛ برای هر Root، نوع شاهد نهایی اکنون دقیق تعریف شده است.

وضعیت: `STATIC_SCAN_EXHAUSTED_RUNTIME_OR_OWNER_EVIDENCE_REQUIRED`.

## ۱. frmBankReconciliationList

طبقه‌بندی:
`UNRESOLVED_TEMPLATE_OR_FILE_PREVIEW_SURFACE_NOT_A_PROVEN_RECONCILIATION_QUEUE`.

- ۳۸ کنترل مستقیم دارد، اما `ApplyingFilter` خالی است؛
- Permission از TransferList و وضعیت ردیف از Transfer می‌آید؛
- Child آن فایل XLS را با Office Interop preview می‌کند؛
- Query/Load هستهٔ Reconcile مشاهده نشده است.

تصمیم موقت: Route «صف مغایرت بانکی» برای آن ساخته نشود. برای بستن Root باید
مالک نشان دهد این صفحه امروز از کجا باز می‌شود و چه کاربردی دارد، یا scope
exclusion را امضا کند. حذف Source همچنان تصمیم جداگانه است.

## ۲. frmReconciliationSetup

طبقه‌بندی:
`REAL_BANK_STATEMENT_IMPORT_AND_SESSION_SETUP_LOGIC_WITH_UNRESOLVED_LAUNCHER`.

- ۲۰ کنترل، شش Method write-like و Permission method دارد؛
- Profile، Parser، Save/Delete و Aggregate آن با شواهد مستقل اثبات شده‌اند؛
- Launcher/Menu/Reflection dispatcher آن هنوز پیدا نشده است.

تصمیم موقت: Workflow Import در Scope ERP باقی می‌ماند، ولی Route mapping آن
provisional است. شاهد نهایی باید Menu/Shortcut/Parent/Dispatcher واقعی و Node
مجوز متناظر را مشخص کند. اگر Launcher فعال ندارد، مالک باید Entry point جدید
وب را آگاهانه تصویب کند؛ Route قدیمی حدس زده نمی‌شود.

## ۳. FormSpecialOptionsDistrict

طبقه‌بندی: `PLACEHOLDER_OR_DYNAMIC_FEATURE_CANDIDATE_UNRESOLVED`.

- صفر Field مستقیم و صفر Business method؛
- صفر Route، Launcher و Clone catalog candidate؛
- فقط ۸۸ Field ارث‌رسیده از Base دارد.

تصمیم موقت: هیچ Schema/Command/Route مقصدی استنتاج نشود. مالک باید وجود
License/استفاده و معنای کسب‌وکاری را تأیید کند یا scope exclusion را امضا کند.

## Telemetry حداقلی و بدون هویت

سه Session کنترل‌شده کافی است: یک Context مجاز، یک Context ممنوع و یک Navigation
هدایت‌شده توسط مالک. Eventهای مجاز:

- تلاش و نتیجهٔ فعال‌سازی Form؛
- Route/Menu/Dispatcher انتخاب‌شده؛
- Bind شدن یا خالی ماندن Data source.

فقط Timestamp UTC، Environment، Version/Assembly hash، Form type allowlist‌شده،
Source kind، Parent/Menu key، Permission node بدون Assignment، نتیجه و Data
source type مجاز است.

User identity، Membership، Credential، Connection string، business value،
file path/content، raw SQL و exception payload ممنوع است. Telemetry فقط مشاهده
می‌کند و هیچ Command یا Source write لازم ندارد.

## سیاست تصمیم

- نبود Reference ایستا unused بودن را ثابت نمی‌کند؛
- Shape خالی مجوز حذف نیست؛
- منطق واقعی بدون Launcher در Domain scope می‌ماند؛
- Navigation mapping به Runtime یا Owner evidence نیاز دارد؛
- Scope exclusion فقط با sign-off مالک نام‌دار انجام می‌شود.

در نتیجه شمار Rootهای واقعاً بسته‌شده هنوز صفر است، اما برای هر سه، آخرین Gate
و خروجی مورد انتظار مشخص شده و اسکن تکراری متوقف می‌شود.

## بازتولید

```powershell
.\.venv\Scripts\python.exe scripts\windows\build_varanegar_unresolved_root_closure_contract.py `
  --root-entrypoints artifacts\varanegar_analysis\ui\varanegar_root_entrypoints_20260827.json `
  --deployment-scan artifacts\varanegar_analysis\ui\varanegar_deployment_root_reference_scan_20260827.json `
  --declared-fields artifacts\varanegar_analysis\ui\varanegar_priority_gap_declared_fields_20260827.json `
  --profile-state-boundary artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_profile_state_boundary_20260827.json `
  --special-options-assessment artifacts\varanegar_analysis\ui\varanegar_special_options_district_assessment_20260827.json `
  --output artifacts\varanegar_analysis\ui\varanegar_unresolved_root_closure_contract_20260827.json
```
