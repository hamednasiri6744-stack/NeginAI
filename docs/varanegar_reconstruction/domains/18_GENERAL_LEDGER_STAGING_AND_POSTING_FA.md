# دامنه ۱۸: PreVoucher، سند خارجی و دفترکل دوبل

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **زنجیره Posting و تراز عددی تأیید شد؛ معنای وضعیت قطعی و برخی شناسه‌های Legacy باز است**

## مرز حریم و منبع

- Extractor: `scripts/sql/extract_varanegar_general_ledger_domain.py`
- Artifact: `artifacts/varanegar_analysis/domains/general_ledger_staging_and_posting_20260826.json`
- ۱۳ جدول، ۴۰ FK رسمی، ۵۳۰ Consumer، ۳۵ Link candidate و ۱۲ قرارداد
  انتخابی بررسی شد.
- هیچ شرح سند/آرتیکل، شماره مرجع، کد حساب، هویت User/Device/Party یا ردیف
  منفرد Journal در Artifact ذخیره نشده است.

## نتیجه اصلی: سه لایه Posting وجود دارد

```text
Domain event / source document
          │
          ▼
dbo.PreVoucher             staging line + source discriminator
          │  balanced by creator/reference/fiscal/DC
          ▼
dbo.ExternalVoucherHeader  confirmed batch
dbo.ExternalVoucher        balanced external lines
          │  canonical link: Voucher.ExternalVoucherHeaderId
          ▼
dbo.Voucher                ledger journal + fiscal/DC numbering
dbo.VoucherItem            double-entry lines + SL/DL/dimensions
dbo.VoucherStatusHistory   explicit current pointer on Voucher
```

`PreVoucher` یک جدول موقت ساده نیست؛ Bus حسابداری بین فروش، برگشت، خزانه، چک،
انبار، خرید و دفترکل است. حذف آن یا تبدیل مستقیم هر دامنه به Journal بدون قرارداد
Source و Idempotency، ردیابی و Reconciliation را می‌شکند.

## دفترکل نهایی

| شاخص | مقدار |
|---|---:|
| Voucher header | ۲۰۵٬۹۴۴ |
| Header فعال / حذف‌شده | ۲۰۵٬۹۴۲ / ۲ |
| Header دستی | ۸٬۴۲۶ |
| Header متصل به External batch | ۱۹۷٬۵۱۸ |
| VoucherItem | ۱٬۳۸۵٬۶۹۴ |
| بازه تاریخ کسب‌وکار | ۱۴۰۳/۰۱/۰۱ تا ۱۴۰۵/۰۵/۳۱ |

هر ۲۰۵٬۹۴۲ سند فعال تراز است و هیچ سند فعال نامتوازن نیست:

- بدهکار فعال = بستانکار فعال = `150,593,312,715,430`؛
- بیشینه اختلاف مطلق = صفر؛
- یک Header خط فعال ندارد؛
- Item منفی، دوطرفه یا صفر/صفر وجود ندارد؛
- تمام Itemها `SixthLedgerId` دارند، ۵٬۴۹۲ مورد Fifth دارند و Seventh در Snapshot
  مصرف نشده است.

تفکیک مبدأ:

| مبدأ | Header دارای خط | Line | بدهکار = بستانکار |
|---|---:|---:|---:|
| External/سیستمی | ۱۹۷٬۵۱۸ | ۱٬۲۸۷٬۸۷۴ | ۱۴۱٬۷۳۱٬۹۷۴٬۲۶۵٬۶۸۴ |
| Manual | ۸٬۴۲۳ | ۹۷٬۸۱۵ | ۸٬۸۶۱٬۳۳۸٬۴۴۹٬۷۴۶ |

پس اختلاف مجموع دفترکل با Pipeline خارجی دقیقاً بخش Manual است. سه Header دستی
خط فعال ندارند یا حذف‌شده‌اند و یک Header فعال بدون خط باید Review شود.

شماره‌گذاری در `(FiscalYearId, DCId)` معنا دارد. هر سه سال مالی در DC=1 دیده
شدند؛ `VoucherNo` از ۱ در هر Scope شروع می‌شود، در حالی که `SerialNo` ترتیب دیگری
دارد. مقصد نباید شماره سند را Global PK فرض کند.

## وضعیت سند و Current pointer

| Status | History row | سند دارای سابقه | جاری |
|---|---:|---:|---:|
| پیش‌نویس | ۳٬۰۳۳ | ۱٬۳۴۷ | ۴ |
| موقت | ۳۱۲٬۳۷۱ | ۲۰۵٬۹۴۳ | ۲۰۵٬۹۴۰ |
| در حال بررسی | ۷٬۱۷۲ | ۱٬۱۵۸ | ۰ |
| قطعی | ۰ | ۰ | ۰ |

Pointer جاری، Ref یتیم یا متعلق به سند دیگر ندارد. بااین‌حال در ۱٬۰۹۴ سند، Pointer
جاری برابر بیشترین HistoryId نیست. تحلیل تکمیلی ۱۴٬۹۴۶ رخداد بعدی را نشان داد؛
۱٬۰۹۱ سند رخداد بعدی با وضعیت متفاوت دارند و Pointer در ۱٬۰۹۰ مورد هنوز روی
رخداد اول است. بنابراین اختلاف «Rollback سالم» اثبات‌شده نیست؛
`CURRENT_POINTER_HISTORY_FORK` با `UNKNOWN_OUTCOME` است. Pointer مرجع Read model
Legacy می‌ماند، اما رخدادهای بعدی نیز حذف یا با MAX جایگزین نمی‌شوند.

نبود Status قطعی در این Clone به معنی نبود Posting مالی نیست؛ همه اسناد فعلی عمدتاً
«موقت» و ترازند. معنای Business/Legal قطعی باید با کارشناس حسابداری و Procedureهای
Closing تأیید شود.

## External Voucher pipeline

- ۱۹۷٬۵۱۸ Header، همگی Confirmed؛
- ۱٬۲۸۷٬۸۷۴ Line؛
- Header بدون Line صفر؛
- Batch نامتوازن صفر؛
- مجموع بدهکار/بستانکار `141,731,974,265,684`؛
- Header total mismatch صفر؛
- نوع خارجی/Line/پیوند canonical یتیم صفر؛
- هر ۱۹۷٬۵۱۸ Header دقیقاً از `Voucher.ExternalVoucherHeaderId` به دفترکل می‌رسد.

### دام شناسه Legacy

`ExternalVoucherHeader.VoucherId` در ۱۹۲٬۳۸۱ Header مقدار دارد، اما:

- با `Voucher.VoucherId` متناظر canonical در هیچ مورد برابر نیست؛
- با `Voucher.VoucherNo` متناظر نیز در هیچ مورد برابر نیست؛
- ۱۸۹٬۷۱۱ مقدار حتی PK موجود در Voucher نیست.

پس این ستون را نباید FK یا شماره سند تفسیر کرد. رابطه اثبات‌شده جهت معکوس
`Voucher.ExternalVoucherHeaderId -> ExternalVoucherHeader.ExternalVoucherHeaderId`
است؛ در آن Ref یتیم یا Batch چندسندی فعال صفر است.

## PreVoucher و پوشش دامنه‌ها

`PreVoucher` دارای ۲٬۳۷۰٬۵۶۹ Line، ۱۱ VoucherCreator، ۳۱ نوع خارجی و ۳۱ نوع
دفترکل است. هر ۹۴۹٬۲۱۲ گروه `(creator, reference, fiscal year, DC)` تراز است؛
بیشینه ۴۶۲ Line در یک گروه و اختلاف مطلق همه گروه‌ها صفر است. **مجموع مبلغ**
دقیقاً با ExternalVoucher برابر است؛ تعداد Line یکسان نیست، چون Grain تاریخی
۱٬۰۸۲٬۶۹۵ Stage line را تجمیع کرده و ۱٬۲۸۷٬۸۷۴ قلم رسمی ساخته است. جزئیات و
اختلاف آن با Grain Procedure فعلی در دامنه ۱۹ ثبت شده است.

پوشش Source discriminator بدون ذخیره شناسه‌ها:

| منبع | Line |
|---|---:|
| Inventory voucher | ۱٬۰۱۳٬۷۹۲ |
| Sale | ۶۲۵٬۸۳۹ |
| Receipt | ۳۴۸٬۴۵۴ |
| Payment allocation | ۱۳۵٬۳۴۴ |
| Received-cheque history | ۱۰۹٬۴۳۲ |
| Pay | ۹۰٬۹۶۷ |
| Return sale | ۲۷٬۵۰۷ |
| Transfer | ۱۱٬۰۲۶ |
| Payable-cheque history | ۵٬۲۳۰ |
| Supplier invoice | ۲٬۳۵۲ |
| Supplier return | ۶۲۶ |

تمام PreVoucherها External header معتبر، External/Voucher type معتبر، FiscalYear
و DC معتبر دارند. ستون‌های Fund، Guarantee، ManualVoucher و Party dimension در
Snapshot فعلی صفرند، ولی Capability از Schema/consumerها حذف نمی‌شود.

## Crosswalk رسمی VoucherCreator

۱۷ Creator تعریف شده‌اند؛ ۱۱ مورد داده دارند و شش مورد فعلاً بدون PreVoucher
هستند. Field definitionها ۵۹۷ ردیف‌اند و Creator/Field یتیم صفر است.

| Creator | PreVoucher line | Source reference |
|---|---:|---:|
| حسابداری انبار | ۱٬۰۱۳٬۷۹۲ | ۵۰۶٬۸۹۶ |
| فروش | ۶۲۵٬۸۳۹ | ۲۰۲٬۶۳۶ |
| دریافت | ۳۴۸٬۴۵۴ | ۶۵٬۶۰۳ |
| سایر اسناد/Settlement | ۱۳۵٬۳۴۴ | ۶۷٬۶۷۲ |
| پیگیری چک دریافتی | ۱۰۹٬۴۳۲ | ۵۴٬۷۱۶ |
| پرداخت | ۹۰٬۹۶۷ | ۲۸٬۷۵۹ |
| برگشت از فروش | ۲۷٬۵۰۷ | ۱۳٬۴۱۱ |
| انتقال | ۱۱٬۰۲۶ | ۵٬۵۱۳ |
| پیگیری چک پرداختنی | ۵٬۲۳۰ | ۲٬۶۱۵ |
| حسابداری خرید | ۲٬۳۵۲ | ۱٬۱۷۵ |
| حسابداری برگشت خرید | ۶۲۶ | ۲۱۶ |

Creatorهای بدون داده: پیگیری چک انتظامی، حقوق و دستمزد، عیدی و سنوات، تنخواه،
دریافت انتظامی و اعلامیه حسابداری. خالی‌بودن Snapshot مجوز حذف Capability نیست.
`ViewName` و `ReferenceObjectName` Contract کد را معرفی می‌کنند؛ متن `SimpleQuery`
و ردیف Source در Artifact وارد نشده است.

هر ۱۱ View فعال resolve شد و Definition آن قابل مشاهده است؛ View رمزگذاری‌شده
یا مفقود صفر است. در مجموع:

- ۲۰۲٬۹۹۰ بایت Definition با SHA-256 جدا برای هر View؛
- ۵۶۱ ستون خروجی، بین ۲۹ تا ۷۶ ستون برای هر Creator؛
- ۱۸۶ dependency یکتا، بین ۷ تا ۲۲ dependency برای هر Creator.

متن Definition ذخیره نشده؛ فقط Fingerprint، اندازه، زمان تغییر، Schema خروجی و
نام dependencyها ثبت شده است. تغییر Hash هر View باید Golden parity همان Creator
را دوباره اجباری کند.

## تطبیق سه ماه تجاری

در `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱`، تعداد ۲۷٬۱۷۷ گروه Source و ۱۰۹٬۴۲۸ PreVoucher
line با ۲۰۴ External batch و دقیقاً همان ۱۰۹٬۴۲۸ External line از نظر مبلغ
`14,534,992,576,848` در هر سمت برابر است.

دفترکل ۸۸۷ Header و ۱۱۸٬۵۴۳ Line دارد: ۲۰۴ Header سیستمی و ۶۸۳ Header دستی.
مجموع Journal `15,483,659,612,388` و سهم Manual دقیقاً `948,667,035,540` در
هر سمت است؛ بنابراین اختلاف با External به‌طور کامل با Manual origin توضیح داده
می‌شود و خطای تراز نیست.

## قرارداد مدل مقصد

- `AccountingSourceEvent`: domain، source key/crosswalk، rule version؛
- `PostingDraft` و `PostingDraftLine`: immutable و idempotent تا بقای Batch؛ حذف/
  Reissue فقط Command صریح با Tombstone، Reason و Rule/Grouping version؛
- `PostingBatch`: confirmed/rejected/transferred با aggregate hash؛
- `Journal` و `JournalLine`: fiscal/DC scoped numbering و double entry؛
- `JournalStatusEvent` و current pointer صریح؛
- `LedgerDimension`: SL/DL/Fifth/Sixth/Seventh با validation مستقل؛
- `PostingCrosswalk`: Source → Draft → Batch → Journal؛
- `ReconciliationRun`: count، debit، credit و orphan parity در هر مرحله؛
- `AccountingApproval`: Human approval برای Manual/Closing/Correction؛
- `Outbox`: انتشار نتیجه Posting پس از Commit.

هر مرحله باید با Idempotency key ثابت دوباره‌پذیر باشد. ساخت Journal قبل از تراز
Batch یا بدون Fiscal/DC scope ممنوع است. شرح‌ها و کد حساب فقط با سطح دسترسی لازم
نمایش داده شوند و در Log تحلیلی ذخیره نشوند.

## Golden Caseهای لازم

1. Sale → PreVoucher → External → Journal؛
2. Return sale و جهت معکوس؛
3. Receipt و Pay چندابزاری؛
4. انتقال وضعیت چک دریافتی/پرداختنی؛
5. Inventory voucher و COGS؛
6. Supplier invoice/return؛
7. Manual journal متوازن با Approval؛
8. Batch نامتوازن و رد قبل Posting؛
9. Retry همان Source بدون Journal تکراری؛
10. Current status pointer که MAX history نیست؛
11. Header.VoucherId گمراه‌کننده در برابر canonical reverse link؛
12. شماره ۱ در دو FiscalYear متفاوت؛
13. Void/Delete با حفظ Audit؛
14. Closing/Initial/Conclusive fiscal-year voucher؛
15. Rebuild کامل و برابری count/debit/credit هر سه لایه.

## ابهام‌های باز

1. معنای تاریخی `ExternalVoucherHeader.VoucherId`؛ شواهد فعلی PK/No بودن را رد کرد.
2. Disposition حسابداری ۱٬۰۹۴ Fork و تعیین Outcome رخدادهای جداشده؛ از داده قابل استنتاج نیست.
3. معنای حقوقی/عملی «موقت» در حالی که تقریباً همه اسناد در همین وضعیت‌اند.
4. Header فعال بدون Line یک `DRAFT_EMPTY_NUMBERED_SHELL` با اثر مالی صفر است؛
   شماره منبع آن پیش از reuse نیازمند Accountant disposition است. دو Header حذف‌شده جدا هستند.
5. Rule ساختاری هر ۱۱ VoucherCreator، Binding واقعی فرم و مرز تراکنش در
   `19_VOUCHER_CREATION_ATOMICITY_AND_POLICY_FA.md` تکمیل شد؛ Golden parity
   مالی/Dimension و UAT مالک برای هر Creator هنوز باز است.
6. نحوه فعال‌شدن Fifth/Seventh dimension و الزامات ترکیب Ledgerها.
7. Procedureهای Closing و کنترل دسترسی/Approval آن‌ها.

## تصحیح مسیر فعال و کشف تکمیلی ۲۰۲۶-۰۸-۲۸

تحلیل Hash-pinned IL ثابت کرد فرم فعلی از مسیر
`Form -> Business -> DataAccess -> dbo.usp_DoExternalVoucher -> usp_DoPreVoucher`
می‌رود، نه `DoExternalVoucher_Create`. Business برای فراخوانی معمول فرم یک
`DataContext(Transaction.Begin)` می‌سازد و پس از پایان Adapter Commit می‌کند؛
پس Atomicity مسیر Desktop اثبات شد، هرچند خود Procedure تراکنش داخلی ندارد.

همچنین Policy فعلی سال ۱۴۰۵ (Mode 1، تک‌Source) تاریخچه را توضیح نمی‌دهد: ۳۶۶
از ۳۸۲ Header همان سال چند Source دارند. نسخهٔ مؤثر Policy روی Header ذخیره نشده
و بازسازی تاریخی از Current config ممنوع است. جزئیات، Artifact و Risk `R-047`
در سند دامنه ۱۹ ثبت شده است.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_general_ledger_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\general_ledger_staging_and_posting_20260826.json
```
