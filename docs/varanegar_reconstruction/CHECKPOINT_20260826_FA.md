# Checkpoint ادامه بازسازی وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۶  
وضعیت: **بسته شناخت ۱۸ دامنه‌ای کامل و معتبر؛ هیچ Write به منبع انجام نشده**

## قبل از هر ادامه

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\validate_varanegar_reconstruction_bundle.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\manifest_20260826.json

G:\NeginAI\.venv\Scripts\python.exe -m pytest `
  G:\NeginAI\tests\test_varanegar_reconstruction_evidence.py -q
```

انتظار: Manifest=`PASS`، domain_count=18 و `7 passed`.

## مرجع‌های اصلی، به ترتیب خواندن

1. `FOUR_HOUR_ANALYSIS_20260826_FA.md` — نتیجه، معماری، ریسک، ابزار و زمان؛
2. `THREE_MONTH_OPERATIONAL_ACTIVITY_20260826_FA.md` — حجم واقعی سه ماه؛
3. `RECONSTRUCTION_READINESS_MATRIX_20260826_FA.md` — Gate هر دامنه و DoD؛
4. `DISCOVERY_LOG_FA.md` — ترتیب کشفیات و شواهد؛
5. `domains/01..18` — قرارداد کامل هر دامنه؛
6. `artifacts/varanegar_analysis/manifest_20260826.json` — Hash و وضعیت ماشین‌خوان.

## آخرین اعداد معتبر

- ۱۸ Extractor/Artifact/Doc؛
- ۲۷٬۵۵۶٬۶۷۰ بایت Artifact دامنه؛
- ۲۸۸ Table slot، ۳٬۱۹۹ FK slot، ۲۳٬۷۳۹ Consumer slot؛
- ۳٬۲۳۴ Implicit-link slot و ۱۶۳ Semantic-contract slot؛
- ۱۳ دامنه و ۱۴ بلوک در تجمیع سه‌ماهه؛
- هفت تست متمرکز PASS.

## آخرین کشف

زنجیره حسابداری:

```text
Domain source
  -> PreVoucher
  -> ExternalVoucherHeader/Line
  -> Voucher/VoucherItem + explicit status pointer
```

۱۷ VoucherCreator وجود دارد، ۱۱ فعال است. همه ۱۱ View فعال resolve و قابل مشاهده
است؛ Hash، ۵۶۱ ستون خروجی و ۱۸۶ dependency ثبت شده و متن SQL ذخیره نشده است.
در سه ماه، ۲۰۴ سند سیستمی + ۶۸۳ سند Manual دقیقاً ۸۸۷ Journal را می‌سازند و
اختلاف مبلغ Journal/External کاملاً با سهم Manual برابر است.

## کار بعدی دقیق

### اگر ادامه شناخت انتخاب شود

1. برای هر ۱۱ Creator، Rule/Validation را از View dependency و Procedure مشترک
   به Contract مستقل تبدیل کن؛
2. Golden fixture بدون PII برای هر Creator بساز؛
3. Source → PreVoucher → External → Journal count/amount/account-dimension parity؛
4. معنی وضعیت «موقت/قطعی» و ۱٬۰۹۴ Pointer غیرMAX را با UI/حسابدار تأیید کن؛
5. AccessNode↔NGT Permission و Config scope precedence را ببند.

### اگر شروع ساخت Slice A انتخاب شود

1. دیتابیس مقصد جدا؛
2. Migration/Audit پایه: `SourceSnapshot`, `SourceCrosswalk`, `MigrationRun`,
   `QuarantineFinding`, `AuditEvent`, `Outbox`, `IdempotencyRecord`؛
3. Organization/Fiscal/DC/Office/Warehouse؛
4. Unit/Document types و Product catalog؛
5. Party/Customer/Supplier/Personnel؛
6. Authorization/Data scope و Config resolver؛
7. Import فقط‌خواندنی + Reconciliation API/UI.

تا زمان Golden parity و UAT، Command عملیاتی و Write مستقیم به وارانگار ممنوع
است. Frontend در این مرحله فقط Review/read-only است.

## دسترسی لازم برای گام بعد

- برای ادامه تحلیل SQL: همان Clone و حساب فعلی کافی است؛
- برای Slice A: Target DB جدا، Repo/Runtime تصمیم‌گیری‌شده و Fixture ماسک‌شده؛
- برای Command/Pilot: Roleهای آزمایشی، UI رسمی read-only، کارشناسان دامنه،
  Approval/rollback/UAT؛
- Plugin جدید در حال حاضر لازم نیست.
