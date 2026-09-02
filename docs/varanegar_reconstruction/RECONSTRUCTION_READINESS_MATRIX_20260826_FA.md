# ماتریس آمادگی بازسازی وب وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۶  
مبنای Evidence: ۱۸ دامنه و Manifest معتبر فقط‌خواندنی

این ماتریس فرق «شناخت کافی برای طراحی» و «آمادگی برای عملیات Production» را
حفظ می‌کند. هیچ ردیفی صرف وجود Schema یا UI، Production-ready محسوب نمی‌شود.
در Manifest فعلی، ۱۸ دامنه جمعاً ۱۱۱ محدودیت شواهد/ابهام باز دارند؛ چرخهٔ چک
دریافتی با ۸ مورد بیشترین تعداد را دارد. این‌ها Gateهای بسته‌شدن طراحی و UAT
هستند، نه مجوز حدس‌زدن رفتار Legacy.

## سطح‌ها

- **E1 — Structure:** جدول، کلید و مصرف‌کننده شناخته شده؛
- **E2 — Population:** شمارش، وضعیت و کیفیت Ref اندازه‌گیری شده؛
- **E3 — Contract:** قواعد، State/ledger و Golden case مستند؛
- **E4 — Parity evidence:** فرمول/زنجیره رسمی و تطبیق عددی گسترده تأیید شده؛
- **P0 — Not buildable:** قرارداد بنیادی باز؛
- **P1 — Schema-ready:** مدل و Import خواندنی قابل شروع است؛
- **P2 — Command-ready:** پس از Golden parity می‌توان Command آزمایشی ساخت؛
- **P3 — Pilot-ready:** Auth، Approval، Audit، rollback و UAT واقعی تأیید شده.

## ماتریس دامنه

| # | دامنه | Evidence | آمادگی فعلی | Gate بعدی | Slice |
|---:|---|---|---|---|---|
| ۱ | سازمان و سال مالی | E3 | P1 | تأیید DC=0 مالی/DC=1 عملیاتی و Company | A |
| ۲ | جغرافیا و مسیر | E3 | P1 | Crosswalk رسمی Legacy↔NGT و عنوان Area | A |
| ۳ | واحد/انبار/نوع سند | E3 | P1 | Selectable=2 و دو VoucherType بلااستفاده | A |
| ۴ | کالا/گروه/برند/بسته/بارکد | E3 | P1 | سیاست Barcode مشترک و Brand↔NGT group | A |
| ۵ | Party/Customer/Supplier/Personnel | E3 | P1 | PII policy، identity reset و ownership مشتری | A |
| ۶ | قیمت/تخفیف/جایزه | E3 | P1 | Golden parity ترتیب Rule و DSL امن | B |
| ۷ | Order→Sale | E3 | P1 | State machine رسمی، Split NGT و retry parity | B |
| ۸ | موجودی/رزرو/خروج | E3 | P1 | حفظ فرمول تعهد فروش باز؛ Residual فعلی صفر و projection refresh | C |
| ۹ | توزیع/تحویل | E3 | P1 | شاهد تحویل، عدم تحویل و Legacy path | C |
| ۱۰ | Receipt/Allocation/OpenInvoice | E3 | P1 | Parity مانده باز و چندابزاری/چندتخصیصی | D |
| ۱۱ | برگشت فروش/اعتبار | E4 | P1 | فرمول Gross→Net با Residual صفر اثبات شد؛ RDهای نهایی‌نشده و Golden command باقی است | D |
| ۱۲ | چک دریافتی/برگشتی | E4 | P1 | Cross-customer ۴۹/۴۹ و ۸ Master Pay gap توضیح‌پذیر؛ انتقال LegalType در تأیید گروهی و Golden command باقی است | D |
| ۱۳ | خرید/مرجوعی/بدهی | E3 | P1 | Receipt-only goods و Source lineهای گمشده | E |
| ۱۴ | Pay/چک پرداختنی | E4 | P1 | ۱۵۵ SOURCE_USED_UNLINKED توضیح‌پذیر؛ Provenance تاریخی، workflowهای خالی و approval | E |
| ۱۵ | کاردکس تأمین‌کننده | E4 | P1 | Parity موردی ۲۸ Branch و ManualVoucher جهت | E |
| ۱۶ | مجوز Legacy/NGT/Data scope | E4 | P1 | Crosswalk AccessNode↔Permission و role owner | A |
| ۱۷ | Config/Feature flags | E2/E3 | P1 | تقدم Scope و مقدار مؤثر کنترل‌شده | A/B |
| ۱۸ | PreVoucher/External/دفترکل | E4 | P1 | ۱٬۰۹۴ Pointer/history fork، status موقت/قطعی و closing | همه |

هیچ دامنه Command-ready یا Pilot-ready اعلام نشده است، چون هنوز Golden parity
روی Command واقعی، Role واقعی و UI واقعی انجام نشده. اما همه Foundationها برای
طراحی Schema مقصد و Import فقط‌خواندنی آماده‌اند.

## ترتیب اجرایی بدون بازطراحی دوباره

### مرحله ۱ — Target foundation

1. دیتابیس مقصد جدا و Migration versioning؛
2. `SourceSnapshot`, `SourceCrosswalk`, `MigrationRun`, `QuarantineFinding`؛
3. `AuditEvent`, `Outbox`, `IdempotencyRecord`؛
4. Organization/Fiscal/DC/Office/Warehouse؛
5. Unit/Document type و Product catalog؛
6. Party/Role/Personnel؛
7. Authorization principal/permission/data scope؛
8. Configuration definition/value/version/resolver.

تعریف Done: Import دوباره‌پذیر، Count/PK/FK parity، orphan report، هیچ Update
منبع، endpoint خواندنی مجاز و صفحه Review بدون PII اضافه.

### مرحله ۲ — Order slice

1. Pricing/Rule evaluator با Trace؛
2. Order aggregate/state و calculation snapshot؛
3. Sale conversion attempt با Idempotency؛
4. Source→PreVoucher→External→Journal projection آزمایشی؛
5. Golden replay روی Typeهای اصلی سه‌ماهه.

تعریف Done: نتیجه قیمت/Rule/State/Posting با Legacy برای fixtureهای منتخب برابر،
retry بدون Duplicate و هر عدم تطابق در Queue قابل توضیح.

### مرحله ۳ — Inventory/Distribution و سپس مالی

Inventory/Exit/Distribution قبل از وصول و برگشت؛ سپس Receipt/Allocation/Cheque/
Return؛ بعد Purchase/Payable/Supplier ledger. هر مرحله Projection و Rebuild خود
را دارد و به یک عدد مانده mutable تقلیل داده نمی‌شود.

## دسترسی‌های لازم، به ترتیب زمان

### برای ادامه تحلیل فعلی

دسترسی موجود کافی است: Clone محلی، `READ_ONLY`، `VIEW DEFINITION` و deny writer.
Plugin یا ابزار شخص ثالث جدید لازم نیست.

### پیش از شروع Slice A

1. دیتابیس مقصد و Credential جدا با کمترین دسترسی؛
2. Repository/branch رسمی مقصد و تصمیم Runtime/Deployment؛
3. Test fixture ماسک‌شده و مجوز PII محدود؛
4. مالک کسب‌وکار برای سازمان، کالا، مشتری و حسابداری؛
5. محیط تست مستقل و Backup/restore drill.

### پیش از Command و Pilot

1. کاربر آزمایشی برای هر Role و Data scope واقعی؛
2. دسترسی Read-only به UI وارانگار برای ضبط Golden workflow؛
3. خروجی کنترل‌شده Procedureهای گزارش رسمی یا EXEC محدود؛
4. تأیید حسابدار برای Closing، ManualVoucher و چک Certified؛
5. UAT فروشنده/انبار/توزیع/خزانه روی دستگاه و شبکه واقعی؛
6. Cutover owner، rollback plan و sign-off مکتوب هر دامنه.

## Definition of Done مشترک هر دامنه

- Source count، hash و زمان Snapshot ثبت شده؛
- PK/Business key/FK/implicit links و orphanها سنجیده؛
- State transition و current pointer صریح؛
- Rule/config version همراه تصمیم ثبت می‌شود؛
- Authorization هم عملیات و هم Data scope را enforce می‌کند؛
- Golden caseهای Happy/Cancel/Retry/Legacy anomaly پاس؛
- Import و projection rebuild دوباره‌پذیر؛
- اختلاف‌ها Queue و دلیل دارند، نه اصلاح حدسی؛
- PII/Secret در Log/Artifact/Frontend اضافه ظاهر نمی‌شود؛
- Audit/Approval/Outbox/Idempotency متناسب با ریسک؛
- هیچ Write مستقیم به وارانگار عملیاتی؛
- Business owner parity و UAT را تأیید کرده است.

## تخمین تثبیت‌شده

- اولین Slice خواندنی اطلاعات پایه: ۳ تا ۵ هفته؛
- Foundation قابل استفاده: ۵ تا ۸ هفته؛
- فروش/انبار/توزیع: ۶ تا ۹ هفته بعدی؛
- وصول/برگشت/خرید/خزانه: ۶ تا ۱۰ هفته بعدی؛
- Pilot/UAT/Cutover: ۴ تا ۶ هفته؛
- کل Production-grade: **۲۱ تا ۳۳ هفته** برای تیم کوچک با کمک AI و دسترسی
  منظم به کارشناسان.

این زمان برای محصول قابل حسابرسی است؛ Mockup ظاهری سریع‌تر است اما جای Workflow،
Migration parity و کنترل مالی را نمی‌گیرد.
