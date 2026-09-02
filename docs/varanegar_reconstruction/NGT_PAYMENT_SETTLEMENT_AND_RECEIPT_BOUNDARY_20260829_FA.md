# مرز پرداخت، تخصیص، تأیید و رسید NGT — ۱۴۰۵/۰۶/۰۷

## نتیجهٔ اجرایی

پرداخت در وارانگار یک سطر مستقل و هم‌معنی با «رسید» نیست. مدل فعلی حداقل پنج مفهوم جدا دارد:

1. `NGT.CustomerCallPayments`: سربرگ مبلغ و نوع تسویهٔ ثبت‌شده در ویزیت؛
2. `NGT.CustomerCallPaymentDetails`: تخصیص مبلغ به سفارش جاری NGT یا فاکتور قدیمی BackOffice؛
3. `NGT.Tours.PaymentApproved`: تصمیم گردش‌کار دربارهٔ تأیید پرداخت‌های یک تور؛
4. `dbo.Receipt`: رسید رسمی BackOffice که ممکن است چند پرداخت یا دانه‌بندی متفاوتی را پوشش دهد؛
5. `NGT.PaymentTypeOrders` و `NGT.DealerPaymentTypes`: سیاست مجازبودن روش پرداخت برای عامل/مشتری.

نسخهٔ وب نباید این پنج مفهوم را در یک جدول CRUD ادغام کند. مرز هدف باید «دستور پرداخت»، «تخصیص»، «تأیید تور» و «صدور/اتصال رسید» را جدا و در عین حال قابل آشتی‌دادن نگه دارد.

## دامنه و ایمنی شواهد

دو منبع بازتولیدپذیر ساخته شد:

- `ngt_payment_settlement_boundary_20260829.json`: فقط Catalog، برچسب‌های معنایی و تجمیع‌های بدون شناسه از Clone محلی `READ_ONLY`؛
- `ngt_payment_runtime_boundary_20260829.json`: خواندن ایستای PE metadata و IL چهار DLL مستقر، بدون Load یا Execute کردن Assembly.

هیچ Stored Procedure، endpoint یا فرمان عملیاتی اجرا نشد. هیچ دادهٔ مشتری، کاربر، چک، صیاد، حساب، سریال دستگاه، توضیح، مقدار تنظیمات، credential یا UUID در Artifactها نگهداری نشده است. متن SQL ماژول‌ها نیز ذخیره نشده و فقط نام، طول و SHA-256 آن‌ها ثبت شده است.

## مدل دادهٔ قطعی

در پنج جدول هدف ۸۲ ستون دیده شد. جمعیت فعلی:

- ۳٬۵۲۳ سربرگ پرداخت فعال؛
- ۳٬۹۱۷ ریزتخصیص فعال؛
- هیچ سربرگ یا ریز حذف‌شده در Snapshot فعلی؛
- ۴ نوع تسویهٔ استفاده‌شده که همگی به BaseType صحیح `SettlementType` resolve می‌شوند:
  - کارت‌خوان: ۳٬۱۷۹؛
  - نقد: ۱۸۰؛
  - چک: ۱۵۹؛
  - رسید: ۵.

همهٔ ۲۴ FK مرتبط فعال‌اند، ولی همگی `NOT TRUSTED` هستند. روی پنج جدول هیچ Unique Index تجاری غیر از Primary Key شناسه وجود ندارد و هیچ Trigger هدفی هم وجود ندارد. Snapshot فعلی خوشبختانه گروه تکراری exact برای fingerprint انتخاب‌شدهٔ سربرگ، UUID رسید یا ریزتخصیص ندارد؛ این مشاهده جای Constraint را نمی‌گیرد.

## قاعدهٔ مبلغ و تخصیص

مقایسه با تلرانس یک صدم نشان می‌دهد:

- ۳٬۴۶۶ سربرگ با جمع ریزتخصیص برابرند؛
- ۵۷ سربرگ کم‌تخصیص‌اند؛
- هیچ سربرگ بیش‌تخصیص نیست؛
- ۱۴ مورد از ۵۷ مورد هیچ ریزی ندارند؛
- ۴۳ مورد ریز دارند، ولی جمع ریز کمتر از مبلغ سربرگ است.

توزیع ۵۷ مورد:

| نوع تسویه | کل | بدون ریز | کم‌تخصیص |
|---|---:|---:|---:|
| کارت‌خوان | ۳٬۱۷۹ | ۷ | ۲۴ |
| نقد | ۱۸۰ | ۲ | ۷ |
| چک | ۱۵۹ | ۰ | ۲۱ |
| رسید | ۵ | ۵ | ۵ |

هر دو ستون `Amount` و `PaidAmount` از نوع `float` هستند. در ERP جدید باید fixed precision و یک سیاست rounding واحد داشته باشیم. اگر تخصیص جزئی مجاز است، «ماندهٔ تخصیص‌نیافته» باید فیلد/موجودیت صریح باشد؛ اگر مجاز نیست، برابری باید داخل همان تراکنش Persistence enforce شود.

## مقصد ریزتخصیص

دو حالت جاری کاملاً از هم جدا هستند:

- ۳٬۷۴۵ ریز جاری به `CustomerCallOrderUniqueId` اشاره می‌کنند؛
- ۱۷۲ ریز `IsOldInvoice=1` با `BackOfficeSaleId` و شناسهٔ عددی فاکتور قدیمی resolve می‌شوند؛
- هیچ ریز بدون مقصد، هیچ ریز با هر دو نوع مقصد و هیچ orphan فعلی وجود ندارد.

یک ریز به سفارشی متعلق به CustomerCall دیگری اشاره دارد؛ اما آن دو Call در همان Tour و برای همان Customer هستند، سفارش فعال است و رسید BackOffice هم ندارد. بنابراین آن را فساد قطعی نمی‌نامیم. مدل هدف باید «هدف تخصیص» را مستقل و typed طراحی کند تا تخصیص بین دو Call همان مشتری/تور، در صورت تأیید مالک فرایند، قابل بیان باشد.

## اتصال به رسید BackOffice

۲۷۴ سربرگ به رسید رسمی متصل‌اند:

- UUID و شناسهٔ عددی در هر ۲۷۴ مورد به همان Receipt می‌رسند؛
- شمارهٔ رسید نیز در هر ۲۷۴ مورد برابر است؛
- هر ۲۷۴ رسید وضعیت تأییدشده دارند؛
- هیچ UUID یا Ref بی‌پاسخ و هیچ حالت یکی‌ازدو وجود ندارد؛
- فقط ۴ مبلغ NGT با مبلغ Receipt برابر است و ۲۷۰ مبلغ متفاوت است.

نتیجه: Crosswalk هویتی قوی است، ولی برابری مبلغ یک invariant معتبر نیست. Receipt احتمالاً دانه‌بندی یا Scope تجمیعی دیگری دارد. ERP جدید باید identity parity را enforce کند و amount reconciliation را با policy جدا توضیح دهد.

## رفتار واقعی Runtime

از ۲۷٬۷۸۸ بدنهٔ IL، ۱۷ متد اصلی پرداخت/تنظیمات/POS بدون فقدان resolve شدند. سه خطای Parser مربوط به بدنه‌های غیرسیگنال‌اند و هیچ متد نام‌دار این دامنه از دست نرفته است.

### `CustomerCallPaymentDomain.SaveTourPaymentChanges`

بدنهٔ Async دارای ۴۶۲ دستور است و این توالی را دارد:

1. `BeginTransaction`؛
2. انتخاب پرداخت‌های قبلی Cash همان Tour؛
3. soft-remove گروه قبلی با `UpdateBatchAsync`؛
4. Map کردن `TourViewModel.Payments`؛
5. جمع‌کردن Amount سربرگ‌ها و PaidAmount ریزهای موجود؛
6. `BulkMergeListAsync`؛
7. `SaveChangesAsync`؛
8. `Commit`؛
9. `Rollback` در مسیر exception.

این تراکنش برای خود پرداخت مناسب است، ولی Snapshot فعلی ثابت می‌کند برابری سربرگ/ریز یک invariant عمومیِ durable در همهٔ مسیرها نبوده است.

### مرز `UpdateTour`

تنها Caller ایستای مستقیم ذخیرهٔ پرداخت، `TourDomain.UpdateTour` است. این بدنه به‌ترتیب سه فرزند مستقل را صدا می‌زند:

- `SaveTourPaymentChanges`؛
- `SaveTourStockLevelChanges`؛
- `CustomerCallOrderDomain.UpdateFromNGT`.

در خود بدنهٔ `UpdateTour` هیچ `BeginTransaction/Commit/Rollback` دیده نشد. ذخیرهٔ پرداخت تراکنش خود را Commit می‌کند و مسیر سفارش نیز طبق بررسی قبلی چند `SaveChangesAsync` مستقل دارد. وجود Ambient Transaction بیرون از بدنه‌ها رد نشده، اما اثبات هم نشده است. بنابراین ERP هدف باید یا یک Transaction Owner واحد داشته باشد یا Saga/receipt قابل بازیابی که «پرداخت Commit شد ولی موجودی/سفارش شکست خورد» را success اعلام نکند.

### تأیید و برگشت تأیید پرداخت تور

`ConfirmTourPayments` و `WithdrawTourPayments` هر دو:

- وضعیت `Received` تور را در guard خود ارجاع می‌دهند؛
- `PaymentApproved` را تغییر می‌دهند؛
- `UpdateBatchAsync` و `SaveChangesAsync` دارند.

این Flag معادل «وجود پرداخت» نیست. در Snapshot:

- ۳۴۵ تور PaymentApproved هستند؛
- ۴۵۸ تور حداقل یک پرداخت فعال دارند؛
- ۲۶ تور تأییدشده بدون پرداخت‌اند؛
- ۱۳۹ تور پرداخت دارند ولی تأیید نشده‌اند؛
- ۳۱۹ تور هم پرداخت دارند و هم تأیید شده‌اند.

این اختلاف می‌تواند حاصل وضعیت‌های قانونی مانند بدون‌وصول، لغو یا مرحلهٔ انتظار تأیید باشد؛ پس به‌تنهایی anomaly نیست. Flag گردش‌کار، تخصیص و رسید باید جدا باقی بمانند.

## HTTP و مجوز

چهار endpoint تأیید پرداخت PreSale/HotSale/Distribution/VanSale با `POST` و چهار endpoint برگشت تأیید با `GET` منتشر شده‌اند. هر هشت endpoint یک اعلان مجوز NGT دارند. استفاده از GET برای Mutation قبلاً در R-062 ثبت شده و این خوشه شاهد دقیق مالی آن است؛ anonymous بودن ادعا نمی‌شود.

POS از نظر Verb بهتر است: `Save=POST`، `Put=PUT` و `Delete=DELETE` و هر سه Resource/Action authorization دارند.

## سیاست روش پرداخت

در Clone:

- ۴۰۴ PaymentTypeOrder وجود دارد؛ فقط ۱۵ مورد فعال و enabled هستند؛
- ۱۲ مورد فعال `AllowReceipt` دارند؛
- ۲٬۵۲۱ DealerPaymentType همگی فعال‌اند؛
- ۴۸۲ Bridge فعال به PaymentTypeOrder حذف‌شده اشاره می‌کنند؛
- ۴۷ POS وجود دارد که ۴۶ مورد فعال است؛ مقدار سریال یا حساب در Artifact ذخیره نشده است.

بدنهٔ `GetDealerCustomerPaymentTypes` joinهای لازم را دارد، ولی ارجاع صریح `IsRemoved` یا `IsEnabled` در همان بدنه دیده نشد. احتمال فیلتر Repository رد نشده و exposure واقعی کاربر ادعا نمی‌شود. R-061 توسعه یافت تا Resolver هدف حتماً active/enabled/effective-date را به‌صورت fail-closed اعمال کند.

## اثر روی ریسک و طراحی ERP

- R-007 با شکست جزئی میان پرداخت، موجودی و سفارش در `UpdateTour` توسعه یافت؛
- R-061 با ۴۸۲ اتصال فعال به روش پرداخت حذف‌شده توسعه یافت؛
- R-063 جدید و Critical است: واگرایی سربرگ/ریز پرداخت بدون invariant durable؛
- Risk Register اکنون ۶۳ ریسک دارد: ۳۵ Critical، ۲۵ High و ۳ Medium؛
- Traceability دارای ۲۴۸ تخصیص ریسک و همچنان صفر ماژول Command-ready است.

## قرارداد پیشنهادی برای ERP شخصی

حداقل موجودیت‌ها/مفاهیم هدف:

- `CollectionCommand` با idempotency key، actor/owner scope، expected version و business date؛
- `PaymentHeader` با مبلغ fixed precision، نوع تسویه و وضعیت immutable/reversal؛
- `PaymentAllocation` با target typed (`CURRENT_ORDER`، `LEGACY_SALE` یا حالت مصوب دیگر)؛
- `UnallocatedBalance` صریح، اگر تخصیص جزئی مجاز باشد؛
- `TourPaymentApprovalEvent` جدا از Presence پرداخت؛
- `BackOfficeReceiptCrosswalk` با identity/version و بدون فرض برابری مبلغ؛
- `PaymentTermEligibility` با effective date و نسخهٔ policy؛
- Outbox/receipt برای انتشار اثرات پس از Commit.

هیچ Write مربوط به این دامنه قبل از بسته‌شدن R-007 و R-063 و عبور Golden Caseهای Cash، POS، Cheque، Receipt، partial allocation، old invoice، retry، rollback و concurrent update نباید Command-ready شود.

تکمیل Replication در
`NGT_PAYMENT_REPLICATION_AND_CROSSWALK_IDEMPOTENCY_BOUNDARY_20260829_FA.md`
نشان می‌دهد ۷۰ Payment دارای History تکراری نوع ۱۰ فقط شماره‌ی رسید را در Header
جاری دارند و UUID/Ref آن‌ها خالی است. بنابراین `R-064` و Gate مستقل idempotency،
current crosswalk و reconciliation نیز پیش‌شرط هر Write/Retry است.

## محدودیت‌ها

- داده از Clone فقط‌خواندنی است و وقوع خطای کاربر در Production را اثبات نمی‌کند؛
- IL مسیر کامپایل‌شده را ثابت می‌کند، نه فراوانی اجرای branchها؛
- نبود تراکنش در بدنهٔ `UpdateTour` نبود Ambient Transaction در لایهٔ بیرونی را قطعی نمی‌کند؛
- ۵۷ mismatch باید با مالک فرایند تعیین تکلیف شود: خطا، تخصیص ناقص قانونی یا تفاوت Scope؛
- ۲۷۰ اختلاف مبلغ Receipt نباید خودکار repair یا forced-equality شود.
