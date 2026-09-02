# مرز SQL پویای قواعد و Snapshot منبع سند حسابداری

تاریخ شاهد: ۱۴۰۵/۰۶/۰۶ (2026-08-28)

این سند دو رفتار مستقل در مسیر فعال صدور سند را ثبت می‌کند:

1. `dbo.usp_DoPreVoucher` دادهٔ View سازنده را با `WITH(NOLOCK)` می‌خواند و حاصل را در staging مالی ماندگار می‌کند.
2. همان Procedure و `dbo.usp_DoExternalVoucherTypeValidation` بخش‌هایی از پیکربندی را به SQL قابل‌اجرا تبدیل می‌کنند.

شاهد اصلی، Artifact زیر است:

- `artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json`
- بخش `dynamic_rule_sql_and_source_snapshot_profile`

Extractor بازتولیدپذیر:

- `scripts/sql/extract_varanegar_voucher_creation_atomicity_policy.py`

## مسیر قطعی کد

مسیر فعال Desktop به این ترتیب است:

`FormExternalVoucher.DoWorkSave`
→ `ExternalVoucherHeaderHandler.DoExternalVoucher`
→ `ExternalVoucherHeaderAdapter.DoExternalVoucher`
→ `dbo.usp_DoExternalVoucher`
→ `dbo.usp_DoPreVoucher`

در `usp_DoPreVoucher` یک batch با متغیر `@StrCmd` ساخته و با `EXEC(@StrCmd)` اجرا می‌شود. ورودی‌های پیکربندی‌شدهٔ زیر در این batch نقش دارند:

- نام View سازنده؛
- نام فیلد تاریخ و مبلغ؛
- ابعاد حسابداری SL/DL/Fifth/Sixth/Seventh؛
- شرط Article و شرط پیش‌فرض نوع سند؛
- دستور ساخت شرح؛
- نام فیلدهای سازنده.

Validator نیز نام View و predicate را در یک `SELECT ... WHERE 1=2 AND (...)` پویا قرار می‌دهد. در این دو محل `sp_executesql` پارامتردار یا یک مدل Rule تایپ‌شده دیده نشد.

## Snapshot فعلی پیکربندی

اسکن فقط‌خواندنی ۱۱ دستهٔ fragment را شمرد و هیچ مقدار خامی ذخیره نکرد:

| دسته | ردیف دارای مقدار | مقدار متمایز |
|---|---:|---:|
| View name | 17 | 17 |
| Default where | 21 | 21 |
| Secondary where | 14 | 14 |
| Article predicate | 129 | 71 |
| Date field | 159 | 7 |
| Amount field | 159 | 20 |
| Ledger fragment | 459 | 80 |
| Comment constant | 353 | 82 |
| Default comment | 61 | 41 |
| Voucher type name | 78 | 78 |
| Creator field name | 597 | 313 |

در snapshot فعلی، شمار مقادیری که یکی از نشانه‌های سادهٔ زیر را دارند صفر است:

- `;`
- comment خطی یا block comment
- keywordهای واضح statement
- single quote
- control character

این نتیجه فقط می‌گوید در وضعیت فعلی نشانهٔ سادهٔ مشکوک ندیدیم. این نتیجه نه ایمنی معنایی Ruleها را ثابت می‌کند، نه انتساب دسترسی نوشتن پیکربندی را، و نه ریسک طراحی SQL پویا را حذف می‌کند.

## مرز ثبات منبع

View سازنده در batch صدور با `AS vw WITH(NOLOCK)` خوانده می‌شود. Transaction بیرونی Desktop می‌تواند writeهای خود صدور را اتمیک کند، اما `NOLOCK` تضمین نمی‌کند منبعی که staging از آن ساخته می‌شود committed و یکپارچه باشد. بنابراین از نظر مسیر کد، حالت‌های زیر ممکن‌اند:

- دیدن ردیف uncommitted که بعداً rollback می‌شود؛
- ندیدن ردیف در حال جابه‌جایی یا تغییر؛
- دیدن شکل ناسازگار از چند جدول منبع؛
- تبدیل مشاهدهٔ گذرا به `PreVoucher` و سپس سند مالی ماندگار.

هیچ creator view یا write هم‌زمانی اجرا نشد؛ پس این یک ریسک قطعیِ مسیر کد است، نه گزارش یک dirty-read تاریخی مشاهده‌شده.

### Isolation واقعی Provider و ظرفیت Versioning

تحلیل ایستای Hash-pinned `Application.DataAccess.dll` نشان داد
`Thunderstruck.Provider.DefaultProvider.Open` دقیقاً یک بار overload بدون پارامتر
`IDbConnection.BeginTransaction()` را فراخوانی می‌کند. آرگومان Isolation صریح و
marker متنی Isolation در Binary وجود ندارد.

گزینه‌های Clone فقط‌خواندنی فعلی:

- `READ_COMMITTED_SNAPSHOT = ON`
- `ALLOW_SNAPSHOT_ISOLATION = ON`

بنابراین Database ظرفیت committed row-versioned read را دارد، اما دو محدودیت باقی
است: `NOLOCK` در Query سازنده این حفاظت را دور می‌زند، و تنظیم Clone لزوماً معادل
Production نیست.

Dependency graph بازگشتی بدون اجرای Viewها چنین است:

| Scope | Creator | Base table | View | بیشینه عمق | دارای rowversion | Temporal | Change Tracking |
|---|---:|---:|---:|---:|---:|---:|---:|
| تمام Creatorهای فعال تاریخی | 11 | 72 | 32 | 6 | 7 | 0 | 0 |
| چهار Creator فعال سه‌ماهه | 4 | 54 | 19 | 6 | 6 | 0 | 0 |

در هر دو Scope، dependency حل‌نشده و external صفر است. نام‌های شبیه Modified/
Version فقط heuristic هستند و watermark پایدار محسوب نشده‌اند. شش جدول دارای
`rowversion` از ۵۴ جدول اخیر برای بازتولید cross-table snapshot کافی نیست.

## قرارداد لازم برای ERP نگین

نسخهٔ مقصد باید این قواعد را رعایت کند:

- منبع مالی فقط از snapshot committed و بازتولیدپذیر خوانده شود؛
- Isolation در Command مالی صریح و testable باشد و به default Provider/Database
  واگذار نشود؛
- watermark یا version منبع همراه با نسخهٔ policy/rule در تصمیم صدور ثبت شود؛
- هیچ fragment پیکربندی مستقیماً SQL قابل‌اجرا نباشد؛
- Ruleها DSL تایپ‌شده، versioned، validate‌شده و immutable پس از publish باشند؛
- identifierها فقط از mapping allowlisted انتخاب شوند و scalarها parameter باشند؛
- publish قواعد مالی نیازمند جداسازی publisher/approver و audit readback باشد؛
- Golden Caseهای ۷۱ predicate مشاهده‌شده پیش از فعال‌سازی Rule مقصد تکمیل شوند؛
- تست هم‌زمانی ثابت کند rollback یا تغییر منبع موجب سند ghost، missing یا duplicate نمی‌شود.

## ریسک‌های ثبت‌شده

- `R-052` — خواندن ناسازگار creator view و ماندگارشدن آن در staging مالی — `CRITICAL`
- `R-053` — اجرای پیکربندی مورداعتماد به‌صورت SQL الحاقی — `CRITICAL`

## محدودیت شاهد

- هیچ Procedure عملیاتی یا View سازنده اجرا نشد.
- هیچ Assembly بارگذاری یا اجرا نشد؛ IL فقط به‌صورت ایستا خوانده شد.
- هیچ مقدار خام predicate، شرح، کد حساب یا دادهٔ کسب‌وکار در Artifact ذخیره نشد.
- دسترسی نویسندگان پیکربندی هنوز به actor/role مشخص منتسب نشده است.
- تنظیم RCSI/Snapshot فقط برای Clone اثبات شده و Production parity نامعلوم است.
- ستون‌های نام‌مشابه Version/Modified، قرارداد Versioning تلقی نشده‌اند.

بررسی کامل سطح نوشتن نشان داد Application مستقر Form/Caller فعالی برای این Ruleها
ندارد و SaveCommand نام‌دار write-disabled است؛ در مقابل دو Procedure ادمینی
Template transfer بدون publish transaction وجود دارد. جزئیات در
`24_VOUCHER_RULE_TEMPLATE_TRANSFER_AND_PUBLISH_FA.md` ثبت شده است.
- Snapshot تمیز فعلی، جایگزین تست adversarial و concurrency در محیط جدا نیست.
