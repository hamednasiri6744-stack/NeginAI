# قرارداد مهاجرت وارانگار به ERP شخصی نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **قرارداد طراحی Offline؛ هیچ Snapshot داده یا Import اجرا نشده است**

## اصل راهنما

مهاجرت «کپی جدول‌ها» نیست. هر اجرای مهاجرت باید چهار شیء مستقل و قابل Audit
داشته باشد: Source Snapshot تغییرناپذیر، Crosswalk نسخه‌دار، Quarantine
توضیح‌پذیر و Reconciliation چندسطحی. وارانگار در تمام مسیر منبع فقط‌خواندنی
می‌ماند و هیچ اختلافی با Write-back به Legacy اصلاح نمی‌شود.

## Source Snapshot

هر Capture حداقل شناسه منبع و دیتابیس، Hash قرارداد و Query/Extractor، زمان شروع
و پایان، Business cutoff، مرز Consistency/Isolation، جدول یا Projection، تعداد
ردیف، بازه مرتب کلید، Aggregate checksum و PII classification دارد.

Snapshot تکمیل‌شده Append-only است. Delta با Watermark و Tie-breaker تغییرناپذیر
گرفته می‌شود؛ داده Late-arriving یک Capture جدید است. Ledgerهای مرتبط نباید از
مرزهای Consistency متفاوت در یک Slice مخلوط شوند. داده خام PII فقط در Staging
رمزشده و محدود می‌ماند؛ Manifest عمومی پروژه فقط Hash و Aggregate نگه می‌دارد.

## Crosswalk

کلید Crosswalk ترکیب زیر است:

`source_system + source_database_fingerprint + entity_type + source_key`

مقصد UUID مستقل دارد و شناسه عددی Legacy هویت Aggregate مقصد نمی‌شود. وضعیت
نگاشت یکی از `exact`، `derived`، `ambiguous`، `quarantined` یا `retired` است.
Merge چند Source به یک Target بدون رکورد حل Duplicate و Approval ممنوع است؛
نگاشت مبهم یا قرنطینه‌شده نیز اجازه فعال شدن Command مقصد را نمی‌دهد.

## Quarantine

Finding قرنطینه Reason، Severity، Evidence، وضعیت، Resolution و Approval دارد.
برای Stock، Ledger، Payment، Cheque و Journal حذف خودکار ممنوع است. شش کلاس
چهارده کلاس شناخته‌شده از شواهد فعلی به‌عنوان Baseline ثبت شده‌اند:

| کلاس | تعداد مشاهده‌شده | برخورد |
|---|---:|---|
| تعدیل Gross→Net برگشت فعال ـ خطا نیست | ۶۹۶ | اجزای Gross/Discount/Addition/Net حفظ شود؛ صرف اختلاف Gross و Net قرنطینه نشود |
| فاصلهٔ Cardex-only ناشی از تعهد فروشِ بدون خروج | ۱٬۵۹۴ | Source semantics پذیرفته؛ فرمول کامل صفر Residual دارد و باید عیناً نسخه‌دار شود |
| Master PayId تهی با History PayId2 معتبر ـ خطا نیست | ۸ | هر هشت Approved link معتبر دارند؛ History authority حفظ و Pay مصنوعی ساخته نشود |
| LegalType نامشخص چک حقوقی | ۳۵ | به `UNKNOWN_SOURCE` مهاجرت کند؛ از Personnel یا تاریخ، نوع ۱/۲ حدس زده نشود |
| تخصیص معتبر چک برگشتی Cross-customer ـ خطا نیست | ۴۹ | تطبیق دقیق تخصیص اولیه ۴۹/۴۹ و Over-settlement صفر؛ مالک چک، Customer تخصیص و Customer فاکتور جدا حفظ شوند؛ Review فقط برای Provenance ناقص/ناسازگار |
| برگ دسته‌چک `SOURCE_USED_UNLINKED` | ۱۵۵ | State معتبر با UNKNOWN_SOURCE؛ پیش از reuse بازبینی و چک ساختگی/پاک‌کردن ممنوع |
| Fork وضعیت سند حسابداری | ۱٬۰۹۴ سند / ۱۴٬۹۴۶ رخداد | Blocking reconciliation؛ Pointer و رخدادهای detached با UNKNOWN_OUTCOME حفظ شوند |
| Shell شماره‌دار بدون قلم | ۱ | Draft غیرposted؛ Line نساز و شماره منبع را بدون تصمیم حسابدار reuse نکن |
| برگشت موبایلی بدون Result تاریخی | ۱ | Pending/Unattempted؛ Reject یا سند رسمی حدس زده نشود |
| برگشت موبایلی با Result تاریخی و هدف جاری غایب | ۱ | Blocking reconciliation؛ TourHistory/Crosswalk حفظ و سند خودکار بازسازی نشود |
| Receipt-only کاذب در سنجش per-invoice خرید | ۵ | Relation N:M پذیرفته؛ هر پنج در Component توضیح داده شد و Item مالی/حذف Receipt ممنوع |
| Supplier-return با Item غایب از Source Invoice ـ خطای موجودی نیست | ۷ | هر هفت با خروج نوع ۵۵ دقیق و Price/Amount غیرصفرند؛ Invoice اختیاری است؛ Reassign/Reprice خودکار ممنوع |
| Supplier-return با Explicit TollRef قدیمی ولی Mapping رسمی قابل‌بازیابی | ۲۰ | Ref خام به‌عنوان Provenance حفظ؛ هر ۲۰ فقط از Same-header `TollRef` به‌طور یکتا Resolve و در View رسمی دیده می‌شوند؛ Missing/Ambiguous قرنطینه شود |
| کد عددی مسیر توزیع بدون Label master | ۲۶٬۰۸۶ | Source semantics پذیرفته؛ عدد و Mode دقیق حفظ شود و Label فقط با Crosswalk معتبر افزوده شود |

این تعداد Baseline همان Snapshot تحلیلی است و نباید به‌عنوان شمارش زنده امروز
تلقی شود.

## ترتیب ۱۲ Slice

1. Context سازمانی و سال/مرکز/دفتر/انبار؛
2. Namespaceهای مستقل Unit و Document/Stock type؛
3. Geography و Route با جدایی Legacy/NGT؛
4. Product/Barcode/Package/Brand؛
5. Party و نقش‌های Customer/Supplier/Personnel؛
6. Authorization و Configuration؛
7. Pricing/Discount/Prize rules؛
8. Order/Sale/Return؛
9. Inventory/Exit/Distribution؛
10. Receipt/Allocation/Open invoice/Received cheque؛
11. Purchase/Pay/Supplier cardex/Payable cheque؛
12. PreVoucher/Voucher/Journal/Posting.

Import هر Slice با کلید
`capture_id + slice + mapping_version + importer_version` تکرارپذیر است و از
Checkpoint ناقص Resume نمی‌شود. Partial write باید Rollback یا کاملاً Compensate
شود.

## Reconciliation و Gate

Reconciliation شش سطح دارد: Hash فایل/Schema، Count و کلید، FK/State
distribution، Quantity/Amount، Ledger/Projection/Double-entry و Golden cases.
هر اختلاف باید `zero`، `known_accepted`، `mapped`، `quarantined` یا
`blocking_unknown` باشد. وجود حتی یک `blocking_unknown` مانع پذیرش Slice است.

Slice فقط وقتی Ready است که قرارداد منبع Freeze، Schema مقصد Review، سیاست
کلید/PII تصویب، Fixtureهای orphan/duplicate/ambiguous/retry آماده و Rollback و
Rerun روی Target test DB ایزوله اثبات شده باشند.

## مرز فعلی

این Artifact هیچ ردیف کسب‌وکاری را نخوانده یا ذخیره نکرده، هیچ DB مقصدی نساخته،
هیچ Import/Repair انجام نداده و Dual-write/Pilot/Cutover را مجاز نکرده است.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/negin_erp_varanegar_migration_contract_20260827.json`
- `scripts/windows/build_varanegar_migration_contract.py`
- `tests/test_varanegar_ui_evidence.py`
