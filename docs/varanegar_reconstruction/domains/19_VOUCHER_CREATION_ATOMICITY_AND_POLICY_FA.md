# دامنه ۱۹: مسیر واقعی ساخت سند، مرز تراکنش و نسخهٔ سیاست صدور

تاریخ استخراج: ۲۰۲۶-۰۸-۲۸  
وضعیت: **مسیر Desktop و Atomicity آن اثبات شد؛ بازتولید تاریخچه با تنظیم فعلی رد شد**

## نتیجهٔ کوتاه

مسیر مستقر فرم ساخت سند حسابداری این است:

```text
FormExternalVoucher.DoWorkSave
  -> ExternalVoucherHeaderHandler.DoExternalVoucher
  -> ExternalVoucherHeaderAdapter.DoExternalVoucher
  -> dbo.usp_DoExternalVoucher
  -> dbo.usp_DoPreVoucher
  -> PreVoucher + ExternalVoucherHeader + ExternalVoucher + TblExternalRelation
```

این مسیر به `dbo.DoExternalVoucher_Create` نمی‌رود. آن رویه و شاخهٔ
`DoExternalVoucher_Create_With_PreVoucher` مسیرهای قدیمی/جایگزین‌اند و نباید از
روی تشابه نام به‌عنوان Binding فرم فعلی معرفی شوند.

## منبع و مرز ایمنی

- Extractor:
  `scripts/sql/extract_varanegar_voucher_creation_atomicity_policy.py`
- Artifact:
  `artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json`
- باینری‌های مستقر با Inventory قبلی Hash-check شدند؛ Version هفت Assembly
  هدف `5.9.0.376` است.
- Assemblyها فقط با PE metadata/IL parser خوانده شدند و Load/Execute نشدند.
- دیتابیس فقط `127.0.0.1 / NeginPakhsh_WebDev`، `READ_ONLY`، با
  `can_update=0` و `db_denydatawriter=1` بود.
- هیچ Procedure عملیاتی یا Creator view اجرا نشد؛ فقط Definition، Catalog و
  Aggregateهای ناشناس خوانده شد.

## مرز تراکنش واقعی Desktop

فرم `DoWorkSave` هنگام صداکردن Business مقدار DataContext را `null` می‌فرستد.
Business سپس:

1. `new DataContext(Transaction.Begin)` می‌سازد؛ مقدار Enum `Begin=0` و `No=1`
   از خود Assembly اثبات شده است؛
2. همان Context را به Adapter می‌دهد؛
3. Adapter دقیقاً literal امن `dbo.usp_DoExternalVoucher` را با
   `DataContext.Query` فراخوانی می‌کند؛
4. `DefaultProvider.Open` برای mode صفر `BeginTransaction` می‌زند؛
5. هر Command همان `DbTransaction` را دریافت می‌کند؛
6. پس از تکمیل Adapter، Business `Commit` می‌زند؛
7. `Dispose` در Finally اجرا می‌شود.

پس در مسیر معمول Desktop، ساخت PreVoucher، Header، Line و Relation زیر یک
تراکنش بیرونی مشترک است. خود `dbo.usp_DoExternalVoucher` هیچ `BEGIN TRAN`،
`COMMIT`، `ROLLBACK` یا TRY/CATCH ندارد. نتیجه دقیقاً این است:

- Atomicity مسیر Desktop: **اثبات‌شده**؛
- Atomicity فراخوانی مستقیم SQL یا Caller غیرمعمول: **اثبات‌نشده**؛
- برای ERP مقصد، Transaction owner باید Command سمت Server باشد و به رفتار
  Caller وابسته نماند.

## پروتکل Result و زنجیرهٔ سه حالت Save

Enum مستقر سه حالت دقیق دارد:

| مقدار | حالت | زنجیره |
|---:|---|---|
| ۱ | `Issue` | فقط صدور |
| ۲ | `IssueAndConfirm` | صدور، سپس تأیید |
| ۳ | `IssueAndConfirmAndSend` | صدور، تأیید، سپس انتقال به دفترکل |

SQL پیام‌ها را با قرارداد عددی برمی‌گرداند: `0` شناسهٔ Header موفق، `1` خطای
کسب‌وکار، `2` هشدار نبود عملیات قابل صدور و `3` اطلاعات تعداد صدور. Business
وجود MessageType 1 را Validation failure می‌کند. UI فقط MessageType 0 را به ID
تبدیل می‌کند؛ بعد از خطای صدور پیش از Confirm و بعد از خطای Confirm پیش از
Transfer `return` دارد. بنابراین زنجیرهٔ استاندارد روی Validation failure جلو
نمی‌رود.

Business نتیجه را قبل از Commit روی `VNValidationResult` می‌گذارد و حتی Result
خطای کسب‌وکار را Commit می‌کند. این برای صدور فعلی امن است چون تنها Select نوع ۱
پیش از `usp_DoPreVoucher` و همه Writeهای پایدار قرار دارد. این Safety به ترتیب
کد وابسته است؛ مقصد باید `Rejected` را Outcome غیرقابل‌Commit صریح کند. در مسیر
Exception فراخوانی `Rollback` صریح نیست، ولی Finally، Provider transaction را
Dispose و سپس Connection را Close می‌کند؛ مقصد نباید به Rollback ضمنی Dispose
به‌عنوان قرارداد دامنه تکیه کند.

## Guard تنظیمات و پنجرهٔ تغییر هم‌زمان

Business چهار مقدار نمایش‌داده‌شده در فرم—Issue mode و سه Setting گروه‌بندی—را
با مقدار جاری Server مقایسه و تغییر تنظیمات را رد می‌کند. این Guard مفید است،
اما هر چهار Read **پیش از** ساخت تراکنش صدور انجام می‌شوند. Procedure هیچ‌یک از
این چهار مقدار یا PolicyVersion را Parameter نمی‌گیرد و بعداً تنظیمات را دوباره
از DB می‌خواند. پس یک پنجرهٔ TOCTOU بین Preflight و اجرای SQL باقی است و Batch
نیز نسخهٔ اعمال‌شده را ذخیره نمی‌کند. `R-047` با Policy immutable/versioned این
شکاف را می‌بندد.

## ترتیب اثر روی داده

`dbo.usp_DoExternalVoucher` ابتدا پارامترها، سال مالی، نوع سند، مرکز، تاریخ،
OperationDate و سیاست گروه‌بندی را کنترل می‌کند. سپس:

1. `usp_DoPreVoucher` را صدا می‌زند؛
2. PreVoucherهای تازه را با سیاست مؤثر گروه‌بندی می‌کند؛
3. `ExternalVoucherHeader` می‌سازد؛
4. PreVoucher را به Header وصل می‌کند؛
5. خطوط متوازن `ExternalVoucher` را درج می‌کند؛
6. `TblExternalRelation` را می‌نویسد؛
7. نتیجه/پیام را به Business برمی‌گرداند.

سه حالت `ExternalVoucherIssueMode` در SQL:

| Mode | Grain اصلی صدور |
|---:|---|
| ۱ | به‌ازای Source reference |
| ۲ | به‌ازای روز کسب‌وکار |
| ۳ | به‌ازای ماه کسب‌وکار |

این Grain بعداً با سیاست ادغام DC، جداسازی ستاد و تفکیک SaleOffice ترکیب می‌شود.

## Idempotency و محدودیت Repair

`usp_DoPreVoucher` پیش از درج، وجود Source را در Grain
`(ReferenceName, ReferenceId, DCId)` کنترل می‌کند. Snapshot نشان داد:

- ۹۴۹٬۲۱۲ Source/DC group؛
- هیچ Group در چند FiscalYear، Creator یا ExternalVoucherType پخش نشده است؛
- همه Groupها چند Article دارند؛ بیشینه ۴۶۲ Line؛
- Unique index فعال روی Signature کامل
  `(VoucherCreatorId, ReferenceId, ArticleId, SL, DL, Fifth, Sixth, Seventh, Comment)`؛
- Duplicate دقیق این Signature: صفر.

بنابراین تا وقتی Batch صادرشده برقرار است، Source عملاً Snapshot immutable تلقی
می‌شود. این قرارداد یک Upsert/Repair خط‌به‌خط نیست: تغییر Article یا Mapping بعدی
نباید بی‌صدا روی Source قبلی اعمال شود. بااین‌حال «حذف» رسمیِ Batch تأییدنشده و
ارسال‌نشده، `PreVoucher` و کل Header/Line/Relation آن را پاک می‌کند و Source را
برای صدور دوباره آزاد می‌گذارد؛ پس immutability دائمی نیست و مرز آن خود Batch
صادرشده است. مقصد باید Rule version را همراه Draft ذخیره و Correction/Reissue را
Command مستقل و Audit‌شده کند.

## سلامت کامل Snapshot

در کل Clone:

| کنترل | نتیجه |
|---|---:|
| PreVoucher line | ۲٬۳۷۰٬۵۶۹ |
| Line بدون Header | ۰ |
| Line متصل ولی علامت‌نخورده | ۰ |
| Header بدون External line | ۰ |
| External line بدون Header | ۰ |
| PreVoucher link بدون Header | ۰ |
| Header بدون PreVoucher | ۰ |
| Header نامتوازن | ۰ |
| Header total / Line total mismatch | ۰ |
| بیشینه اختلاف بدهکار/بستانکار | ۰ |

در پنجره `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` نیز همه همین کنترل‌ها صفر است: ۱۰۹٬۴۲۸
PreVoucher line و ۲۰۴ Header بدون هیچ Partial state یا اختلاف مبلغ.

این شاهد Aggregate قوی است، اما جای Fault injection و تست هم‌زمانی مقصد را
نمی‌گیرد.

## کشف بحرانی: تنظیم فعلی تاریخچه را توضیح نمی‌دهد

تنظیم فعلی:

- `DoExternalVoucher_Create_All = 0`؛
- `SeparateSetadCreateVoucher = 0`؛
- `SeparateSaleOfficeCreateVoucher = 1`؛
- سال ۱۴۰۵ اکنون `ExternalVoucherIssueMode = 1` دارد.

Mode 1 یعنی هر Header باید در Grain اصلی فقط یک Source reference داشته باشد،
اما تاریخچهٔ ذخیره‌شده چنین نیست:

| سال | Mode فعلی | Header | تک‌منبعی | چندمنبعی | Source group |
|---:|---:|---:|---:|---:|---:|
| ۱۴۰۳ | ۲ | ۴٬۷۵۵ | ۵۶۳ | ۴٬۱۹۲ | ۷۱۰٬۳۱۲ |
| ۱۴۰۴ | ۱ | ۱۹۲٬۳۸۱ | ۱۹۲٬۳۸۱ | ۰ | ۱۹۲٬۳۸۱ |
| ۱۴۰۵ | ۱ | ۳۸۲ | ۱۶ | ۳۶۶ | ۴۶٬۵۱۹ |

فقط در سه ماه منتخب، ۲۷٬۱۷۷ Source group در ۲۰۴ Header قرار گرفته و ۱۹۶ Header
چندمنبعی است. هر ۲۰۴ Header سه‌ماهه دقیقاً یک تاریخ، یک نوع خارجی، یک DC و یک
SaleOffice دارد و ۱۹۶ مورد چندمنبعی است؛ این شکل دقیقاً با Mode 2 روزانه سازگار
و با Mode 1 فعلی در Procedure مستقر ناسازگار است. پس رفتار مؤثر صدور تغییر کرده،
ولی شاهد موجود میان تغییر Config و تغییر نسخهٔ Procedure تمایز نمی‌گذارد. نسخه/
مقدار مؤثر روی Header ذخیره نشده و زمان و Actor تغییر از Snapshot قابل بازیابی
نیست.

نتیجهٔ طراحی:

- تاریخچه را با تنظیم فعلی Regenerate نکن؛
- `VoucherIssuancePolicyVersion` immutable بساز؛
- روی هر Batch، Mode، DC grouping، Setad grouping، SaleOffice grouping، Fiscal
  mapping، Creator/View hash و Article rule version مؤثر را Snapshot کن؛
- Explain باید بگوید چرا چند Source در یک Batch قرار گرفته‌اند؛
- تغییر Policy فقط Version تازه تولید کند و Result قبلی را تغییر ندهد.

این موضوع به‌عنوان Risk بحرانی `R-047` ثبت شد.

## ۱۱ Creator فعال و پیچیدگی Rule

هر ۱۱ View فعال قرارداد پنج ستون پایه
`VoucherId/VoucherNo/DCName/DCId/SaleOfficeId` را با مقایسهٔ case-insensitive
دارند. ۱۴۹ Article فعال ساختار زیر را می‌سازند:

| Creator | Reference role | Article | Debit/Credit | Where rule | Line سه‌ماهه |
|---|---|---:|---:|---:|---:|
| Settlement | PaymentId | ۴ | ۲/۲ | ۴ | ۰ |
| Inventory | VocherHdrId | ۲۴ | ۱۲/۱۲ | ۲۴ | ۰ |
| Pay | PayId | ۱۲ | ۵/۷ | ۱۲ | ۶٬۳۳۳ |
| Payable cheque history | PChequeHistoryId | ۴ | ۲/۲ | ۴ | ۰ |
| Received cheque history | RChequeHistoryId | ۳۸ | ۱۹/۱۹ | ۳۸ | ۰ |
| Receipt | ReceiptId | ۱۰ | ۴/۶ | ۱۰ | ۳۰٬۶۵۰ |
| Sales return | RetSaleId | ۷ | ۳/۴ | ۰ | ۱٬۵۵۲ |
| Supplier return | RetSupInvoiceHdrId | ۵ | ۲/۳ | ۲ | ۰ |
| Sale | SaleId | ۸ | ۵/۳ | ۰ | ۷۰٬۸۹۳ |
| Supplier invoice | SupInvoiceHdrId | ۵ | ۲/۳ | ۳ | ۰ |
| Transfer | TransferId | ۳۲ | ۱۶/۱۶ | ۳۲ | ۰ |

نبود Line در سه ماه منتخب به معنی غیرفعال‌بودن Capability نیست. همه ۱۱ View
Definition hash، ستون خروجی و Dependency profile دارند. مرحلهٔ بعد، Golden
amount/dimension/source-lineage هر Creator است؛ Structural PASS جای UAT مالی را
نمی‌گیرد.

### شکل Redacted تمام ۱۴۹ Rule

Ruleها بدون ذخیره Account code، Predicate خام یا Comment خام fingerprint شدند:

- Amount source در هر ۱۴۹ Rule یک Field از View است؛
- Date source در هر ۱۴۹ Rule یک Field از View است؛
- Sixth dimension در هر ۱۴۹ Rule از View می‌آید؛
- SL در ۱۲۸ Rule ثابت/Expression و در ۲۱ Rule Field پویاست؛ مقدار ثابت فقط Hash شد؛
- DL در ۹۲ Rule پویا و در ۵۷ Rule تهی است؛
- Fifth فقط در ۱۱ Rule و Seventh در ۲۰ Rule Field پویا دارد؛
- Article predicate در ۱۲۹ Rule، Default predicate نوع سند در ۳۸ Rule و
  Predicate ثانویه در ۲۴ Rule حاضر است؛ فقط Hash/Length/Operator count ذخیره شد؛
- هر ۱۴۹ Rule Comment recipe دارد، ولی `Article.ArticleComment` مستقیم در همه
  آن‌ها تهی است؛ Recipe از Constant componentهای Redacted و Fieldهای مجاز ساخته
  می‌شود؛
- ۱۴۹ Rule hash یکتا ثبت شد.

این الگو برای طراحی Rule engine مقصد مهم است: Amount/Date/Dimensionها Projection
از Source view هستند، در حالی که بخش عمده SL یک Mapping ثابت و نسخه‌دار است.
کپی‌کردن Result نهایی بدون Rule snapshot قابلیت Explain و Rebuild را از بین می‌برد.

### پوشش واقعی ۱۴۹ Rule

ساختاری‌بودن Rule به معنی اجراشدن آن نیست. Crosswalk امن Article ordinal به
PreVoucher نگه‌داری‌شده نشان داد:

| معیار | تعداد |
|---|---:|
| Rule فعال پیکربندی‌شده | ۱۴۹ |
| دارای حداقل یک نمونه در کل تاریخچه | ۱۰۱ |
| بدون هیچ نمونه در کل تاریخچه | ۴۸ |
| دارای نمونه در پنجره سه‌ماهه | ۳۱ |
| بدون نمونه در پنجره سه‌ماهه | ۱۱۸ |

هر ۱۱ Creator در کل تاریخچه فعالیت دارد، اما ۴۸ Branch هیچ شاهد Runtime در
Snapshot ندارند. نبود نمونه دلیل Obsolete بودن نیست. Artifact برای هر Creator
فقط ordinal Ruleهای مشاهده‌نشده و تعداد Aggregate را نگه می‌دارد؛ هیچ کد حساب، ID
سند یا مقدار ردیف ذخیره نشده است. هر ۴۸ Branch یک Golden case مصنوعی، Predicate
true/false و تأیید حسابدار می‌خواهد.

### کشف بحرانی دوم: Grain قلم تاریخی با Procedure فعلی فرق دارد

در کل Snapshot، مبلغ و Header هر ۱۱ Creator در
`PreVoucher -> ExternalVoucher -> Journal` دقیقاً برابر است و خط‌های
`ExternalVoucher -> Journal` نیز یک‌به‌یک‌اند. اما تعداد خط Stage و External یکی
نیست:

| معیار | تعداد |
|---|---:|
| PreVoucher line | ۲٬۳۷۰٬۵۶۹ |
| ExternalVoucher / Journal line | ۱٬۲۸۷٬۸۷۴ |
| Stage line تجمیع‌شده | ۱٬۰۸۲٬۶۹۵ |
| گروه دارای بیش از یک Stage line | ۹٬۶۲۴ |
| بیشینه Stage line در یک قلم تجمیعی | ۶٬۲۵۷ |

Cardinality واقعی هر ۱۱ Creator **دقیقاً** با Grain موجود در
`DoExternalVoucher_Create_With_PreVoucher` سازگار است:

```text
Header + Date + Article + SL/DL/Fifth/Sixth/Seventh + Comment
```

این Grain `ReferenceNo` و جداسازی Debit-side را وارد Group key نمی‌کند و Debit/
Credit را خالص می‌کند. در مقابل `usp_DoExternalVoucher` مستقر فعلی ReferenceNo و
Debit-side را هم وارد Group می‌کند. Replay همه Stageهای تاریخی با Grain فعلی
۱٬۴۲۴٬۰۳۹ خط می‌سازد، یعنی ۱۳۶٬۱۶۵ خط بیشتر از ۱٬۲۸۷٬۸۷۴ خط رسمی نگه‌داری‌شده.
فقط ۸ Creator از ۱۱ Creator در هر دو Grain همان Cardinality را دارند؛ سه Creator
تفاوت را آشکار می‌کنند.

این تطبیق دقیق، **معنای تاریخی معادل** را اثبات می‌کند، نه اینکه حتماً همین نسخه
از Procedure قدیمی برای هر Batch اجرا شده باشد. زمان تغییر و نام نسخهٔ مولد روی
Header ذخیره نشده است. نتیجهٔ مقصد:

- `LineGroupingPolicyVersion` باید کنار `VoucherIssuancePolicyVersion` ذخیره شود؛
- Migration باید قلم رسمی موجود را Preserve کند، نه اینکه از PreVoucher با کد
  امروز Regenerate کند؛
- Explain باید Stage→consolidated-line crosswalk و netting grain را نشان دهد؛
- Golden parity فقط Total نیست؛ Line count، grouping key، ReferenceNo و side
  separation نیز باید مقایسه شوند.

### Parity سه‌لایه به تفکیک Creator

فقط چهار Creator در پنجره سه‌ماهه فعالیت دارند و برای هر چهار، تعداد Line، Header
و مبلغ بدهکار/بستانکار در هر سه لایه `PreVoucher -> ExternalVoucher -> Journal`
دقیقاً برابر است:

| Creator | Source group | Header | Line | بدهکار = بستانکار |
|---|---:|---:|---:|---:|
| Pay | ۲٬۰۸۵ | ۵۵ | ۶٬۳۳۳ | ۵٬۷۳۸٬۷۰۶٬۶۲۹٬۵۰۷ |
| Receipt | ۴٬۳۲۷ | ۵۲ | ۳۰٬۶۵۰ | ۳٬۷۳۰٬۸۸۳٬۹۰۵٬۶۱۸ |
| Sales return | ۷۴۴ | ۴۸ | ۱٬۵۵۲ | ۱۴۰٬۰۷۲٬۴۴۸٬۱۴۶ |
| Sale | ۲۰٬۰۲۱ | ۴۹ | ۷۰٬۸۹۳ | ۴٬۹۲۵٬۳۲۹٬۵۹۳٬۵۷۷ |

مجموع: ۲۷٬۱۷۷ Source group، ۲۰۴ Header و ۱۰۹٬۴۲۸ Line. هفت Creator بدون
فعالیت سه‌ماهه برای پذیرش نیازمند Fixture مصنوعی و Golden case تأییدشدهٔ مالک‌اند؛
از صفر بودن فعالیت حذف Capability نتیجه نمی‌شود.

## ماتریس Verification

| نیاز/ریسک | شاهد | نتیجه | Gap |
|---|---|---|---|
| Binding دقیق فرم تا SQL | IL مستقر و Hash-pinned | PASS | ندارد |
| Atomicity مسیر Desktop | Begin/attach/commit/finally | PASS | Caller مستقیم نامعلوم |
| نبود Partial state | Aggregate کامل Clone | PASS | Fault test اجرا نشده |
| بازتولید Policy تاریخی | Mode فعلی در برابر Header history | FAIL | Policy snapshot غایب |
| قرارداد ساختاری ۱۱ Creator | Catalog و View hash | PASS | Golden business parity باز |
| Parity چهار Creator مشاهده‌شده | Aggregate سه‌لایهٔ سه‌ماهه | PASS | هفت Creator بدون نمونه |
| Parity مالی تمام ۱۱ Creator در تاریخچه | Aggregate سه‌لایهٔ کامل | PASS | Line consolidation جداست |
| پوشش همه ۱۴۹ Rule | Article ordinal→PreVoucher usage | FAIL | ۴۸ Rule بدون نمونه |
| بازتولید Line grain تاریخی با Procedure فعلی | Cardinality دو Grain | FAIL | ۳ Creator متفاوت؛ ۱۳۶٬۱۶۵ خط اضافه |
| Line grain تاریخی معادل | Grain قدیمی در برابر Cardinality رسمی | PASS | Procedure/version دقیق تاریخی نامعلوم |
| مسیر تأیید/حذف/انتقال | IL مستقر + Definition SQL | PASS | تراکنش به Caller استاندارد وابسته است |
| Validation بدون Side effect در انتقال | ترتیب SQL + Commit در Business | FAIL | پاک‌سازی شماره قبل از Validation است |
| Finality خرید برای همهٔ StockDCها | MIN موجود در برابر coverage انبار | FAIL | سال ۱۴۰۵: ۱۰ انبار، ۸ ردیف تاریخ |
| استثنای Finality حقوق | OperationId=5 و تاریخچه | FAIL شواهد | دو نوع تنظیم‌شده، صفر Header |
| توقف chain روی Validation failure | UI IL بین Issue/Confirm/Transfer | PASS | Render Runtime اجرا نشد |
| تفکیک پیام ۰/۱/۲/۳ | SQL + Business/UI IL | PASS | مقصد باید Result typed داشته باشد |
| Policy preflight و apply در یک Snapshot | Getterها، آغاز تراکنش و Parameterها | FAIL | Getterها قبل Transaction؛ نسخه‌ای پاس نمی‌شود |
| Snapshot committed منبع staging | `AS vw WITH(NOLOCK)` در `usp_DoPreVoucher` | FAIL | رخداد dirty-read اجرا/مشاهده نشد |
| Isolation صریح Transaction | IL متد `DefaultProvider.Open` | FAIL | `BeginTransaction()` بدون آرگومان است |
| ظرفیت committed row-versioned read در Clone | RCSI و Snapshot database options | PASS | `NOLOCK` آن را دور می‌زند؛ Production نامعلوم |
| Version پوشا برای منبعهای سه‌ماهه | Graph چهار Creator تا ۵۴ جدول پایه | FAIL | ۶ rowversion، صفر Temporal/Change Tracking |
| پیکربندی غیرقابل‌اجرا | دو محل SQL پویا و ۱۱ دسته fragment | FAIL | مقادیر فعلی در اسکن token ساده پاک‌اند |
| نبود token مشکوک واضح در snapshot فعلی | شمار تجمیعی بدون ذخیرهٔ مقدار خام | PASS | ایمنی معنایی و authority نویسنده را ثابت نمی‌کند |
| انتساب نویسندهٔ Rule به Form/Permission مستقر | اسکن ۶۲ Assembly و SaveCommand | FAIL | Form/Caller صفر؛ سطح ادمینی SQL جداست |
| Template publish اتمیک/نسخه‌دار | دو Procedure انتقال و پنج جدول Rule | FAIL | Transaction/TRY/CATCH/Version صفر |
| منع اجرای Transfer برای حساب تحلیل | Permission introspection | PASS | دربارهٔ DBA/db_owner نتیجه نمی‌دهد |
| تطبیق Dynamic INSERT قدیمی Article با Schema جاری | Column list در برابر `sys.columns` | FAIL | دو ستون حذف‌شده و شش ستون اختیاری جدید |
| پوشش ستون‌های Trigger replication جاری | Trigger INSERT در برابر Schema | PASS | فقط Shape؛ Delivery/Parity جداست |
| Outbox پایدار پیش از Upload | IL سرویس Replication + Schema | PASS | Production delivery اجرا نشد |
| اجرای دریافتی و Receipt در یک Transaction | IL مسیر Local و FTP | PASS | Business-effect parity جداست |
| Receipt دارای Rule version/Approval/Hash | Schema `tblLog/tblLogRcv` | FAIL | فقط Runtime context و Watermark |
| FTP صریحاً encrypted و certificate-validated | IL `ConnectToFtpServer` + FluentFTP default | FAIL | Mode فعال Production خوانده نشد |
| Package پیش از Execute دارای Signature/Hash است | Call graph نام‌دار Send/Receive | FAIL | Zip password، اصالت محتوا نیست |

## قرارداد مقصد

1. `IssueAccountingBatch` یک Command سمت Server و Transaction owner یکتا باشد.
2. `CommandId + payload hash` Retry را به همان Result برگرداند.
3. `PostingDraft` بعد از ساخت immutable باشد؛ Correction نسخه/Command جدا دارد.
4. `VoucherIssuancePolicyVersion` و `CreatorRuleVersion` روی Batch ثبت شوند.
5. Unique constraintهای Semantic علاوه بر PK فنی وجود داشته باشند.
6. Source → Draft → Batch → Journal Crosswalk حذف یا بازسازی حدسی نشود.
7. Fault injection بعد از هر مرحلهٔ Draft/Header/Line/Relation همه اثرها را
   Rollback کند.
8. Parallel retry فقط یک Batch بسازد.
9. ۱۱ Golden case مبلغ، بدهکار/بستانکار، Ledger dimension، Scope و Source lineage
   را با Snapshot تأییدشدهٔ مالک تطبیق دهند.
10. Validation انتقال Query خالص باشد؛ Cleanup شماره‌گذاری فقط پس از PASS و داخل
    Command انتقال انجام شود.
11. Finality خرید ابتدا completeness تمام StockDCهای applicable را اثبات کند و
    استثنای حقوق Policy versioned و تأییدشدهٔ مالک باشد.
12. Result مقصد `Created/NoEligibleSource/Rejected` typed باشد و تنها `Created`
    بتواند Confirm/Transfer بعدی را فعال کند.
13. Source view مالی بدون `NOLOCK` و تحت snapshot committed/versioned خوانده شود؛
    source watermark همراه تصمیم صدور ماندگار شود.
14. Predicate/Field/Comment پیکربندی به DSL تایپ‌شده و versioned تبدیل شود؛ هیچ
    fragment تنظیمات مستقیماً SQL قابل‌اجرا نباشد.
15. Replication از Rule version مصوب و Manifest hash استفاده کند؛ `LastExecLog`
    به‌تنهایی Approval یا Parity تلقی نشود.
16. Transport امن و certificate-validated و Package با کلید نامتقارن امضا شود؛
    Receiver مقصد Arbitrary SQL را اجرا نکند.

جزئیات چرخهٔ `Confirm / Unconfirm / Delete / Transfer` در
`20_EXTERNAL_VOUCHER_LIFECYCLE_FA.md` ثبت شده است.
مرز دقیق Finality و شکاف پوشش خرید در
`21_ACCOUNTING_ISSUANCE_FINALITY_BOUNDARY_FA.md` ثبت شده است.
مرز Snapshot منبع و SQL پویای Ruleها در
`23_DYNAMIC_RULE_SQL_AND_SOURCE_SNAPSHOT_FA.md` ثبت شده است.
مرز انتقال Template و انتشار Rule در
`24_VOUCHER_RULE_TEMPLATE_TRANSFER_AND_PUBLISH_FA.md` ثبت شده است.
مرز Outbox، Transport و Receipt Rule در
`25_RULE_REPLICATION_TRANSPORT_AND_RECEIPT_FA.md` ثبت شده است.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_voucher_creation_atomicity_policy.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\voucher_creation_atomicity_and_policy_20260828.json

G:\NeginAI\.venv\Scripts\python.exe -m pytest -q `
  G:\NeginAI\tests\test_varanegar_voucher_creation_atomicity_policy.py
```
