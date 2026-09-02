# Manifest یکپارچهٔ شواهد شبانه وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ کنترل Offline و بدون اتصال به Runtime/DB**

## نتیجه

خروجی‌های شناخت Runtime و طراحی مقصد اکنون یک واحد قابل بازتولید هستند:

- Manifest هجده دامنهٔ داده با وضعیت `PASS`؛
- ۱۸۹ Artifact ماشین‌خوان UI/Runtime/SQL/Authorization/Workflow/Blueprint؛
- ۱۱۸ سند فارسی؛
- ۱۵۶ Builder/Extractor/Validator تکرارپذیر؛
- صفر خطای هویت Artifact، نسخه Schema، فایل گمشده، Index دانش یا Count gate.

Validator علاوه بر وجود فایل، Artifact identity، `schema_version=1`، Hash هر
فایل، ثبت سند در README و Discovery Log و Countهای اصلی ۴۴۵ فرم، ۲۲ وضعیت، ۱۱
Trace، ۸۷۷ Golden case، ۲۰ Report surface، ۴۴۲ Call contract، هفت Gap فرم،
۴۶ Risk، ۱۸۴ Role-UAT case، ۱۴۱ Field-metadata form، Extension contractها،
قراردادهای مالی سه فرم وصول، برچسب‌های استاتیک و Screen contractهای نامزد وب و
SQL semantic footprint را کنترل می‌کند. همچنین طرح مقصد باید ۱۴ ماژول، هفت فاز و وضعیت
`not_selected_by_user` برای Stack داشته باشد.

## چرا Hash فایل و Hash Drift هر دو لازم‌اند؟

Baseline Drift محتوای معنایی شواهد Runtime را بدون Timestamp مقایسه می‌کند.
Manifest شبانه برعکس، Snapshot دقیق فایل‌های همین Checkpoint را Fingerprint
می‌کند. اولی برای تشخیص تغییر معنایی Release و دومی برای تشخیص تغییر بستهٔ دانش
و Reproducibility است.

## اجرای تکرارپذیر

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\validate_varanegar_night_evidence_bundle.py `
  --project-root G:\NeginAI `
  --output G:\NeginAI\artifacts\varanegar_analysis\varanegar_night_evidence_bundle_20260827.json
```

اجرای این فرمان هیچ Connection دیتابیس، Network read، UI action یا Command
کسب‌وکاری ندارد. فقط فایل‌های موجود پروژه را می‌خواند و Manifest را بازسازی
می‌کند.

برای شکستن وابستگی دوری میان همین Manifest و Handoff صبح، Builder تحویل فقط یک
حالت Bootstrap محدود را می‌پذیرد: تنها خطای Bundle باید دقیقاً شمارش قدیمی
`synthetic_golden_case_count` خود Handoff باشد. وجود هر فایل گمشده یا هر خطای
دیگر همچنان بازسازی Handoff را متوقف می‌کند؛ سپس Validator دوباره باید `PASS`
شود.

## مرز نتیجه

`PASS` یعنی بستهٔ دانش داخلی سازگار و کامل است؛ به معنی درست بودن تمام رفتار
Legacy، مجوز Write، Command-ready بودن، Pilot-ready بودن یا آمادگی Cutover نیست.

## Artifact و کد

- `artifacts/varanegar_analysis/varanegar_night_evidence_bundle_20260827.json`
- `scripts/windows/validate_varanegar_night_evidence_bundle.py`
- `tests/test_varanegar_ui_evidence.py`
