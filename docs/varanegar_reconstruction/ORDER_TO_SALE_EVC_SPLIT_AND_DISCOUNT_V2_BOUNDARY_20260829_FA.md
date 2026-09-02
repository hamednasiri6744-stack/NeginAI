# مرز EVC و Discount V2 در تبدیل سفارش به فروش

## نتیجه اجرایی

مسیر دسکتاپ `FormOrderToSale` یک callsite مستقیم به
`CreateSaleByOrderUsingDiscountV2` دارد؛ اما محاسبه‌ی V2 و تبدیل نهایی فروش در یک
connection و یک تراکنش مشترک نیستند. محاسبه‌ی V2 روی یک
`DataContext(Transaction.No)` انجام می‌شود و stagingهای محلی SQL را می‌سازد؛ تبدیل
نهایی از `OrderAdapter.CreateSaleByOrder` و یک `DataContext(Transaction.Begin)` جدا
عبور می‌کند.

این جدایی اکنون فقط یک ابهام معماری نیست. اسکن تمام ۵۹ اسمبلی managed نشان داد
propertyِ `CreateSaleByOrderHelper.CalcForDiscountV2` هیچ setter تایپ‌شده‌ای بعد از
constructor ندارد. constructor آن را روی صفر می‌گذارد. بنابراین در مسیر تایپ‌شده‌ی
موجود، wrapperِ `SLE.usp_sdsnet_CreateSaleByOrder` وارد شاخه‌ی
`@CalcForDiscountV2=0` می‌شود، staging را دوباره می‌سازد و
`SLE.usp_FillEVCByOrder` را دوباره اجرا می‌کند. نتیجه‌ی فروش عملاً از محاسبه‌ی SQL
این شاخه ساخته می‌شود، نه از staging محلی V2 که روی connection قبلی بوده است.

این رفتار را بهتر است «fallback دو محاسبه‌ای» بنامیم: ممکن است فروش موفق شود، اما
اعتبارسنجی/محاسبه‌ی V2 و محاسبه‌ی نهایی SQL می‌توانند دو پاسخ متفاوت بدهند. برای ERP
نگین نباید این الگو بازتولید شود؛ محاسبه‌ی قیمت و تخفیفِ تأییدشده باید همان snapshot
نسخه‌دار و همان unit of work مورد استفاده‌ی ثبت فروش باشد.

در snapshot فعلی clone دقیقاً یک کلید `IsDiscountV2Active` وجود دارد و enabled
count آن صفر است. پس مسیر V2 یک capability موجود در کد است، اما رفتار فعال فعلی
clone نیست؛ مقدار سرور عملیاتی بدون snapshot هم‌زمان جداگانه ادعا نمی‌شود.

## زنجیره‌ی اثبات‌شده

1. فرم `FormOrderToSale` تنها callsite تایپ‌شده‌ی ورودی
   `CreateSaleByOrderUsingDiscountV2` در inventory فعلی است.
2. `FillEVCUsingDiscountV2` این مراحل را صدا می‌زند:
   `InitialCalcData`، `ExtractCalcDataFromDB`، promotion، تبدیل به EVC entity و
   `SaveCommand`.
3. `CreateEVCSqlTempTableV2` روی همان context جدول‌های محلی
   `#tblTempEvc`، `#tblTempEvcItem`، جداول جایزه/قواعد، `#EvcItemFull` و
   `#SaleItemPaymentUsance` را می‌سازد.
4. context فوق transaction ندارد؛ Commit آن no-op است و Dispose connection را
   می‌بندد. جدول‌های `#` connection-local با بسته‌شدن آن قابل انتقال به connection
   تبدیل نیستند.
5. `OrderAdapter.CreateSaleByOrder` connection و تراکنش جدا می‌سازد و wrapper SQL
   را اجرا می‌کند.
6. پارامتر `@CalcForDiscountV2` در wrapper ورودی `int` با مقدار پیش‌فرض صفر است.
   شاخه‌ی صفر همه‌ی stagingها را می‌سازد، `usp_FillEVCByOrder` را اجرا می‌کند و
   `#SaleItemPaymentUsance` را از نتایج SQL پر می‌کند.
7. `SLE.usp_CreateSaleByEVC` همین جدول موقت تک‌نام را می‌خواند و خروجی را در
   `SLE.tblSaleItemPaymentUsance` ثبت می‌کند.

## ناهماهنگی نام جدول پرداخت مدت‌دار

کد managed ابتدا `#SaleItemPaymentUsance` می‌سازد، اما
`SaleItemPaymentUsanceAdapter.SaveSharpSaleSaleItemPaymentUsanceV2` در
`#SaleSaleItemPaymentUsance` درج می‌کند. در تمام تعریف‌های SQL clone هیچ اشاره‌ای
به نام دوگانه وجود ندارد؛ همه‌ی مصرف‌کننده‌های SQL نام تک‌گانه را می‌خوانند. اسکن
literalهای managed نیز باید نبودن `CREATE TABLE #SaleSaleItemPaymentUsance` را
تثبیت کند.

نتیجه‌ی محافظه‌کارانه: شاخه‌ی درج `SharpSaleItemPaymentUsances` یک mismatch ساختاری
دارد و اگر collection غیرخالی شود، احتمال خطای `Invalid object name` بسیار بالاست.
این سند وقوع تاریخی خطا را ادعا نمی‌کند؛ clone فعلی برای
`SLE.tblSaleItemPaymentUsance` صفر ردیف دارد و رفتار reflection/plugin خارج از
inventory نیز با تحلیل static رد نمی‌شود.

## فرضیه‌ای که رد شد: `globalCalcData` سراسریِ process نیست

نام field گمراه‌کننده است. IL آن را فقط با `ldfld/stfld` دسترسی می‌دهد، نه
`ldsfld/stsfld`؛ پس field نمونه‌ای است، نه static. علاوه بر آن، `GetInstance` یک
`EVCHandler` تازه می‌سازد. بنابراین شواهد فعلی فرضیهٔ cache مشترک process و نشت
هم‌زمان داده بین کاربران را پشتیبانی نمی‌کنند. collectionهای مرجع از نمونهٔ
`globalCalcData` به CalcData محلی منتقل می‌شوند، اما این موضوع جدا از thread-safety
داخلی خود کتابخانهٔ DiscountV2 است و در این مرحله ادعایی دربارهٔ آن نمی‌شود.

## هزینهٔ خواندن در مسیر منتخب V2

در IL منتخب، `InitialCalcData` هفده `AllRawEntity` و یک `GetValue` دارد و
`ExtractCalcDataFromDB` نیز هفده `AllRawEntity` دیگر دارد؛ یعنی مسیر بارگذاری
منتخب تا ۳۵ call مستقیم DataContext پیش از هزینه‌های محاسبه، SaveCommand و تبدیل
نهایی دارد. این عدد count ایستای callsite است، نه latency اندازه‌گیری‌شده و بعضی
branchها ممکن است اجرا نشوند. با این حال، طراحی مقصد باید reference-data را با
نسخه و کلید DC/date cache کند، دادهٔ request-specific را جدا نگه دارد و بودجهٔ
query/latency قابل‌اندازه‌گیری داشته باشد.

`AcceptCommandDiscountV2` مستقیماً business method را صدا می‌زند، اما خودش از
`SodorFactor_BackgroundWorker_DoWork` فراخوانی می‌شود و `ReportProgress` و
`CancellationPending` دارد. بنابراین فرضیهٔ اجرای این بارگذاری روی thread اصلی UI
رد شد. همچنان latency عملیاتی و رفتار cancellation باید با telemetry واقعی سنجیده
شود؛ IL به‌تنهایی SLA یا responsiveness را ثابت نمی‌کند.

Cancellation نیز مرز batch دارد، نه command جاری. در Method منتخب، تنها
`CancellationPending` پیش از call تبدیل سفارش قرار دارد؛ `DbCommand.Cancel` یا
`CancellationToken` دیده نشد. پس درخواست توقف می‌تواند از شروع سفارش بعدی جلوگیری
کند، ولی تبدیل جاری و فروش‌های commitشدهٔ قبلی batch را rollback نمی‌کند. مقصد باید
Outcome هر قلم batch، آخرین cursor، command id و semantics صریح StopAfterCurrent را
ثبت کند؛ «لغو batch» نباید با rollback کل batch اشتباه شود.

## خروجی تشخیصی full-calculation

وقتی `IsDiscountV2Active` روشن باشد، فرم بدون Permission/Authorize call نام‌دار یک
checkbox با عنوان «ذخیره محاسبات تخفیف و جوائز» به toolbar اضافه می‌کند. checkbox
به‌صورت پیش‌فرض خاموش است. در صورت انتخاب، مسیر از parentِ
`Application.ExecutablePath` به `VN.SDS.Container\TestDataDiscountV2\` ساخته
می‌شود و کل `CalcData` با `JsonConvert.SerializeObject`، UTF-8 و GZip به وسیلهٔ
`File.WriteAllBytes` ذخیره می‌شود. نام فایل OrderNo و OprDate دارد و پسوند `.zip`
است، هرچند stream واقعاً GZip است.

در contract منتخب هیچ encryption call دیده نشد. CalcData شامل reference data،
قیمت/تخفیف، کالا، سفارش و EVC است؛ بنابراین مقصد این قابلیت را فقط با مجوز تشخیصی،
redaction، encryption، مسیر خارج از deployment، retention/cleanup و audit مجاز
می‌داند. مسیر بررسی‌شده روی share فعلی `TestDataDiscountV2` وجود نداشت؛ پس وجود
فایل تاریخی یا leakage جاری ادعا نمی‌شود.

این checkbox صرفاً observer نیست. non-empty شدن path باعث می‌شود
`GenerateOldSDSData` پیش از `CalcOrderPromotion` اجرا شود؛ آن متد
`exec SLE.usp_DoEVC` را روی همان staging connection اجرا و خروجی قدیمی را در
`SDSEvcItems` قرار می‌دهد. بنابراین روشن‌کردن ابزار تشخیصی، علاوه بر I/O فایل، یک
محاسبهٔ legacy و mutation جدول‌های موقت را وارد مسیر می‌کند. اثر نهایی آن بر خروجی
فروش بدون integration test قطعی نام‌گذاری نمی‌شود، اما ابزار تشخیصی باید در مقصد
observational باشد و هیچ business procedure اضافه‌ای اجرا نکند.

## شاخه‌ی پنهان و پرخطر مقدار ۱

اگر یک binder یا plugin بیرونی `CalcForDiscountV2=1` بگذارد، wrapper شاخه‌ی ساخت
staging و محاسبه‌ی legacy را رد می‌کند؛ ولی connection تبدیل به جدول‌های محلی
connection قبلی دسترسی ندارد. بنابراین فعال‌کردن واقعی فلگ ۱، بدون اصلاح ownership
connection/context، یک قابلیت امن نیست. قبل از هر استفاده باید با یک integration
test کنترل‌شده روی clone اثبات شود، نه روی دیتابیس عملیاتی.

## قرارداد هدف برای ERP نگین

- یک `PricingSnapshotId` immutable و versioned برای قیمت، تخفیف، جایزه، مالیات و
  payment-usance ساخته شود.
- همان snapshot در همان transaction تبدیل مصرف شود؛ محاسبه‌ی دوباره بین validation
  و commit ممنوع باشد.
- staging به connection محلی UI وابسته نباشد؛ یا TVP/JSON صریح به command داده شود
  یا staging پایدار با correlation id و TTL کنترل‌شده استفاده شود.
- نام جدول/contract باید یک منبع تولید داشته باشد و با contract test بین runtime و
  SQL تطبیق داده شود.
- failure injection بین محاسبه، ثبت sale header/item، payment-usance و outbox باید
  atomicity و idempotency را اثبات کند.

## منابع قابل بازتولید

- `artifacts/varanegar_analysis/domains/order_sale_evc_runtime_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/order_sale_evc_sql_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/datacontext_transaction_runtime_20260829.json`

هیچ فرم، procedure عملیاتی یا اسمبلی اجرا/Load نشد؛ تحلیل managed فقط PE metadata/IL
hash-pinned و تحلیل SQL فقط catalog و aggregateهای read-only بوده است.
