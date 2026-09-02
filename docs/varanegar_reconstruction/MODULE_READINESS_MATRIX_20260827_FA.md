# ماتریس شناخت و آمادگی چهارده ماژول ERP نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **Validation برابر PASS؛ هیچ ماژولی Command-ready، Pilot-ready یا Production-ready نیست**

## پاسخ کوتاه

شناخت ما اکنون برای نه ماژول کسب‌وکاری «چندمنبعی و قابل‌توجه اما ناکامل» است؛
پنج ماژول Foundation برای Refinement مرحلهٔ P0، دو ماژول برای Refinement برش
فقط‌خواندنی P1 و هفت ماژول فقط برای طراحی/تست مصنوعی فازهای بعد آماده‌اند.
این واژه‌ها درصد پیشرفت یا مجوز پیاده‌سازی نیستند.

## ماتریس شواهد

| ماژول | دامنه معتبر | فرم | Workflow | Report | Golden | Gate بعدی |
|---|---:|---:|---:|---:|---:|---|
| platform | ۰ | ۰ | ۰ | ۰ | ۰ | P0 refinement؛ Stack/RPO/RTO باز |
| organization_context | ۲ | ۵ | ۰ | ۰ | ۶۴ | P0؛ معنای DC=0/1 و Context UAT |
| identity_authorization | ۱ | ۰ | ۰ | ۰ | ۱۹ | P0؛ منبع هویت و Grant واقعی باز |
| configuration | ۱ | ۱۰ | ۱ | ۰ | ۳۶ | P0؛ precedence/approval و SpecialOptions باز |
| master_data | ۴ | ۷۹ | ۰ | ۲ | ۱۱۴ | P1 فقط‌خواندنی؛ Barcode/Route/Party quarantine |
| pricing_rules | ۱ | ۳۱ | ۰ | ۰ | ۸۲ | فاز بعد؛ Rule precedence و allocator اتمیک |
| sales | ۲ | ۸۷ | ۴ | ۵ | ۹۷ | طراحی/تست مصنوعی؛ Transaction boundary باز |
| inventory | ۲ | ۷۸ | ۰ | ۷ | ۷۹ | طراحی/تست مصنوعی؛ صفر Residual ولی فرمول ۱٬۵۹۴ تعهد فروش باز باید حفظ شود |
| distribution | ۱ | ۱۲ | ۸ | ۰ | ۷۴ | طراحی/تست مصنوعی؛ ۲۶٬۰۸۶ Path gap |
| receivables_treasury | ۳ | ۸۹ | ۵ | ۳ | ۱۶۲ | سه Read-side بانک؛ Profile/Runtime parity/UAT/Cancel و ۲ Root باز |
| procurement_payables | ۳ | ۱۹ | ۲ | ۱ | ۵۰ | طراحی/تست مصنوعی؛ Link/Book-item quarantine |
| accounting | ۲ | ۱۱ | ۰ | ۱ | ۱۸ | طراحی؛ Ledger pointer/version و Posting UAT |
| reporting_documents | ۰ | ۰ | ۰ | ۲۰ | ۱۷۵ | P1 فقط‌خواندنی؛ Stateful print/export semantics |
| integration_migration | ۰ | ۰ | ۰ | ۰ | ۰ | P0؛ Snapshot/Import اجراشده صفر |

Formها بر اساس Primary domain شمرده شده‌اند. ۳۷۹ از ۴۴۵ Candidate Primary
domain دارند و ۶۶ مورد Unmapped مانده‌اند. Assignment فرم ۴۲۱ است چون دامنه‌های
چندمالکیتی مانند برگشت فروش به بیش از یک ماژول شاهد می‌دهند. به همین دلیل
Assignment گزارش ۳۹ برای ۲۰ Report یکتا نیز جمع سادهٔ فرم‌ها نیست.

## آنچه واقعاً قوی‌تر شناخته شده است

Configuration، Master data، Sales، Inventory، Distribution، Receivables،
Procurement/Payables و Accounting هم‌زمان شاهد دامنهٔ داده و UI دارند و حداقل
یکی از Workflow/Report/Golden را نیز پوشش می‌دهند. در Sales، Inventory،
Golden bundle توسعه‌یافته هر ۹۷۰ Case مصنوعی را به مالک ماژولی نگاشت می‌کند؛
این مجموعه اکنون ۶۴ Case مشتری/کالا و ۱۹۲ Case تأمین‌کننده/Context/قیمت را نیز
در کنار Caseهای مسیر فعال، Orchestrator، Extension و Report دارد.
۹۳ Case مغایرت بانکی نیز به‌صورت کاندید به Receivables/Treasury افزوده شده، اما
مالکیت فرایند P06 و اجرای Target هنوز تأیید نشده است. Profileهای واقعی Clone
صفرند و Cancel مستقل Legacy اثبات نشده؛ پس Cancel provisional و UAT/row parity
همچنان Gate اجباری‌اند.
قرارداد تجمیعی جدید شروع سه برش Read-side شامل Profile، Parser/Staging و Summary
candidate را مجاز می‌داند و هر سه اکنون Schema/Pipeline/Query contract دارند؛
Match/Unmatch، Confirm، Cancel و Reverse با وجود State/Command envelope تا عبور
از هشت Gate Pilot اجازهٔ شروع Command ندارند.

این شواهد برای طراحی مرزها، تست و ترتیب ساخت کافی است؛ برای ادعای رفتار کامل
Legacy کافی نیست. به‌ویژه Atomicity واقعی، Effective permission شخص، Runtime
branchها و UAT مالک کسب‌وکار هنوز کامل نشده‌اند.

در Configuration، تحلیل تازهٔ تاریخ عملیات/قطعی ۱۱ یافتهٔ تشخیصی (سه بحرانی)
را نیز ثابت کرده است. تا تعیین تکلیف `FD001..FD011`، محدودکردن Reopen به
`DC+FiscalYear` و آزمون اتمی ساخت نخستین رکورد، این ماژول حتی با وجود شناخت
بیشتر همچنان Command-ready نیست.

## نواحی کم‌شاهدتر

- Platform و Integration/Migration قرارداد مقصد دارند، نه Runtime مشابه Legacy؛
- Identity/Authorization داده و Policy دارد، ولی هیچ Grant شخصی استخراج یا مجاز
  نشده است؛
- Organization Context دادهٔ قوی دارد اما UI و معنای DC/سال نیازمند UAT است؛
- Reporting بیست Surface دارد ولی دامنهٔ مالک خروجی و مرز Print-completed برای
  همه قطعی نیست؛
- Pricing فرم فراوان و Golden command دارد، اما Rule precedence و allocator
  همزمانی‌امن هنوز پیاده/تست نشده است.

## چرا هیچ ماژولی Command-ready نیست؟

Command contract و Case مصنوعی با پیاده‌سازی Target، Transaction واقعی، تست
Fault روی Target DB، Reconciliation صفر/توضیح‌پذیر، Deny واقعی، Backup/Restore و
UAT برابر نیست. بنابراین Matrix برای هر چهارده ماژول سه Flag
`command_ready=false`، `pilot_ready=false` و `production_ready=false` را صریح
نگه می‌دارد.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_module_readiness_matrix_20260827.json`
- `scripts/windows/build_negin_erp_module_readiness_matrix.py`
- `tests/test_varanegar_ui_evidence.py`

گام بعدی تحلیل: تبدیل Blockerهای Matrix به Risk register و Definition of Ready
مرحله‌ای؛ گام بعدی ساخت پس از انتخاب Stack، Foundation P0 است.
