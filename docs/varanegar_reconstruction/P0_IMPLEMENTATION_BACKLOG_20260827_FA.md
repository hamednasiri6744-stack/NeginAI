# Backlog مرحلهٔ P0 برای ERP شخصی نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۲۶ آیتم، DAG معتبر و Validation برابر PASS؛ هنوز هیچ محیط یا کدی ساخته نشده است**

## خروجی تصمیمی

شناخت وارانگار به ۲۶ کار قابل تحویل در ۱۳ Workstream تبدیل شد. ۲۱ آیتم برای
Refinement آماده‌اند، دو تصمیم مستقیم کاربر می‌خواهند، یک مورد شاهد مالک
کسب‌وکار می‌خواهد و دو مورد تا تکمیل Dependencyها مسدودند. ۵۱ Edge وابستگی
بدون شناسهٔ تکراری یا Dependency یتیم ثبت شده است.

این Backlog عمداً با «ساخت چند جدول CRUD» شروع نمی‌شود. ترتیب اجباری آن چنین
است:

1. انتخاب Stack و ثبت ADR؛
2. مرزبندی Modular Monolith، محیط هدف جدا و Migration نسخه‌دار؛
3. Context سازمانی، مجوز Deny-first، Data scope و Audit؛
4. Command envelope، Idempotency، Outbox/Inbox و Observability؛
5. Snapshot فقط‌خواندنی، Provenance، Crosswalk، Quarantine و Reconciliation؛
6. Golden harness، Backup/Restore و Runbook؛
7. قرارداد Query و Web shell فقط‌خواندنی؛
8. Gate امضاشدهٔ خروج از P0.

## دو تصمیم لازم از کاربر

- `P0-001`: Stack Backend/Web/Database/Deployment/Test؛ تا این تصمیم گرفته نشود
  Web shell و Skeleton واقعی نباید حدس زده شود.
- `P0-021`: هدف‌های RPO/RTO و محل/سیاست Backup؛ بدون این تصمیم آمادگی عملیاتی
  ادعا نمی‌شود.

برآورد ۲ تا ۳ هفتهٔ Blueprint فقط زمان سپری‌شدهٔ یک تیم کوچک متمرکز بعد از
این تصمیم‌هاست؛ جمع Effort یک توسعه‌دهنده نیست و پس از انتخاب Stack باید دوباره
برآورد شود.

## شاهد کسب‌وکاری باز

`P0-025` برای سه Root حل‌نشده است:

- `frmBankReconciliationList`؛
- `frmReconciliationSetup`؛
- `FormSpecialOptionsDistrict`.

اسکن Static کامل Launcher بیرونی پیدا نکرده، اما این دلیل حذف قابلیت نیست. مالک
کسب‌وکار باید Retain/Replace/Retire را با شاهد و تست پذیرش تأیید کند.

## Gateهای فنی مهم

- Application account اجازهٔ DDL ندارد و هیچ Credential نوشتن به وارانگار در
  مسیر اجرا نیست؛
- Deny بر Allow مقدم است و نمایش منو مجوز Command نیست؛
- Retry یک Command outcome دوم تولید نمی‌کند؛
- Business commit و Outbox append اتمیک‌اند؛
- Snapshot به Source write-back ندارد و Business date را با زمان مهاجرت عوض
  نمی‌کند؛
- اختلاف ناشناختهٔ Reconciliation پذیرش Slice را متوقف می‌کند؛
- Golden runner اجازهٔ اجرای Case روی وارانگار یا Clone را ندارد؛
- P0/P1 فقط‌خواندنی هیچ دکمهٔ فرمان کسب‌وکاری ندارد.

## Definition of Ready مشترک

هر آیتم باید Evidence، Owner/Signoff، Dependency، تست مثبت و Deny، رفتار Retry،
Reconciliation و محیط‌های ممنوع را صریح داشته باشد. وجود کد بدون اجرای تست تازه
و Readback نتیجه، Done محسوب نمی‌شود.

## مرز ایمنی و اختیار

این Artifact فقط طراحی Offline است. هیچ Repository، Database، Account، Role،
Migration یا Service ایجاد نشده و هیچ Write، Dual-write، Pilot یا Cutover مجاز
نشده است. Grant واقعی نیز از داده‌های تجمیعی Legacy استنباط نمی‌شود.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_p0_backlog_20260827.json`
- `scripts/windows/build_negin_erp_p0_backlog.py`
- `tests/test_varanegar_ui_evidence.py`

گام ساخت پس از پایان تحلیل: ابتدا تصمیم `P0-001`، سپس `P0-002..P0-004` در محیط
کاملاً جدا و با تست Bootstrap؛ نه اتصال Write به وارانگار.
