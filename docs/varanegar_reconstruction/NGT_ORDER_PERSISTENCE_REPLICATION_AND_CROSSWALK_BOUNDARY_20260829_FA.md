# مرز ذخیره، Replication و Crosswalk سفارش NGT

تاریخ بررسی: ۲۰۲۶-۰۸-۲۹  
وضعیت: تحلیل فقط‌خواندنی و static؛ هیچ endpoint، Stored Procedure یا فرمان تجاری اجرا نشد.

## پرسش این خوشه

برای بازسازی ERP باید بدانیم سفارش موبایل چگونه وارد NGT می‌شود، کدام مسیر آن را
ذخیره یا ویرایش می‌کند، چگونه به BackOffice می‌رسد و شناسه‌های دو طرف در چه
دانه‌ای به هم متصل می‌شوند. وجود ستون‌هایی با نام BackOffice روی Header به‌تنهایی
برای تعریف Crosswalk مقصد کافی نیست.

## مرز ایمنی و منابع

- چهار DLL استقرار‌یافته‌ی `NGT.Common`، `NGT.Business`، `NGT.DataAccess` و
  `NGT.WebApi` فقط از طریق PE metadata و IL خوانده شدند؛ Assembly load/execute صفر است.
- SQL فقط روی Clone محلی `READ_ONLY` با `can_update=0` اجرا شد.
- Stored Procedure، endpoint و application command اجرا نشد.
- هیچ ردیف خام سفارش، مشتری، کاربر، UUID، تنظیم، رمز، SQL definition یا مقدار
  شناسه در Artifact جدید ذخیره نشد؛ تنها نام‌های امن Catalog، هش Definition و
  Aggregateهای ناشناس نگه‌داری شده‌اند.

## مسیرهای ورودی WebApi

چهار بدنه‌ی WebApi مستقیماً `TourDomain.SaveTourData` را صدا می‌زنند:

1. `OrderController.RequestSaveTourData`؛
2. `TourController.SaveTourData`؛
3. `TourController.SaveSupervisorTourData`؛
4. `TourController.RequestSaveTourData`.

چهار endpoint جدا برای Replication تورهای PreSale، HotSale، Distribution و
VanSale نیز به `TourDomain.ReplicateTour` می‌رسند. یک caller دیگر در
`CustomerCallDomain.ReplicateCall` و caller ششم داخل `SaveTourData` دیده شد.

در Metadata مجوز، POST مربوط به `OrderController.RequestSaveTourData` هیچ
`NGTAuthorize`، `Authorize` استاندارد، ClaimsAuthorize یا AllowAnonymous اعلام‌شده
ندارد. تحلیل بدنه‌ی async فقط مصرف CurrentUserId را نشان داد و تصمیم مجوز نام‌دار
پیدا نکرد. این همان موردی از `R-057` است؛ anonymous reachability یا رخداد واقعی
اثبات نشده، چون middleware/host/delegation مبهم هنوز کاملاً رد نشده است.

## تراکنش مسیر Save و Replication

بدنه‌ی async `TourDomain.SaveTourData` دارای ۸٬۹۶۰ دستور IL است:

- یک `BeginTransaction`، یک `Commit` و دو مسیر `Rollback`؛
- چهار call به `ReplicateTour` در branchهای مختلف؛
- اجرای `NGT.NGT_TourValidation` و `dbo.USP_NGT_SaveRecomendationResult`؛
- ساخت/به‌روزرسانی Header، Line، مقدار واحد، Batch، Promotion، Prize، Payment و Return.

در هر چهار پنجره‌ی فراخوانی Replicate، فیلد transaction محلی `SaveTourData`
بلافاصله پیش از call بارگذاری می‌شود. این شاهد قوی است که مسیر Save قصد دارد
Replication را در مالکیت تراکنش بالادست اجرا کند؛ موفقیت runtime یا اتمیک‌بودن
adapter خارجی صرفاً از IL نتیجه گرفته نمی‌شود.

بدنه‌ی `ReplicateTour` ۱۵٬۵۳۲ دستور دارد و:

- یک بار `NewReplicateTour`؛
- دو بار `ReplicateToBackOffice`؛
- سه Commit، یک Rollback، یک `FinishTour` و یک `RollBackTour` دارد؛
- اگر transaction ورودی وجود داشته باشد آن را می‌گیرد، وگرنه transaction محلی
  می‌سازد.

`NewReplicateTour` با ۱٬۲۷۴ دستور IL سه BeginTransaction، سه CustomCommit و چهار
CustomRollback دارد و شناسه‌ی SQL امن استخراج‌شده‌ی آن
`dbo.NGT_DoReplicateTour` است. این شمارش callها مدل کنترل جریان را ثابت می‌کند،
نه تعداد تراکنش موفق در یک اجرای واقعی.

## مسیر ویرایش جداگانه

`TourDomain.UpdateTour` به `CustomerCallOrderDomain.UpdateFromNGT` می‌رسد.
بدنه‌ی دوم ۲٬۴۰۷ دستور دارد، IsRemoved را تغییر می‌دهد و پنج بار
`SaveChangesAsync` فراخوانی می‌کند. در هیچ‌یک از دو بدنه `BeginTransaction` دیده
نشد.

نتیجه‌ی محدود این است که مالک transaction در همین دو بدنه اثبات نشده است. ممکن
است DbContext، caller خارجی یا ambient transaction این مرز را پوشش دهد؛ بنابراین
partial-write فعلی ادعا نمی‌شود. مقصد باید با fault injection پس از هر پنج stage
ثابت کند که هیچ حالت پذیرفته‌شده‌ی نیمه‌کاره باقی نمی‌ماند.

## قرارداد SQL Replication

`dbo.NGT_DoReplicateTour`:

- Definition با طول ۶۱٬۰۲۰ کاراکتر و SHA-256 ثبت‌شده دارد؛ متن SQL ذخیره نشده؛
- پنج پارامتر امن Catalog دارد: Tour، DataOwnerCenter، AppUser، PreviewOrderMode
  و OrderGuid؛
- خانواده‌های Order، Line، Qty، Payment، Return، Tour، Product و تنظیمات را لمس
  می‌کند؛
- یک token شروع transaction، یک rollback و چهار `THROW/RAISERROR` دارد؛ Commit
  صریح در متن دیده نشد، و callerهای IL CustomCommit/transaction دارند؛
- قرارداد result-set به دلیل خطای مجوز ۲۲۹ توصیف نشد؛ Procedure اجرا نشده است.

پس commit ownership باید در مقصد صریحاً بین Procedure replacement و Application
command تعیین شود و نباید از نبود واژه‌ی Commit در Procedure نتیجه‌ی شکست گرفت.

## مدل فعلی Header

۲۲۸٬۲۸۴ Header همگی `IsRemoved=0` هستند و ۲۷۳ مورد `IsCanceled=1` دارند. شش
ترکیب حالت ناشناس مشاهده شد. دو خوشه‌ی اصلی کاملاً جدا هستند:

- ۲۱۸٬۴۸۹ Header دارای `SendToConsoleDate` و فاقد شناسه‌ی عددی مثبت BackOffice؛
- ۹٬۷۹۵ Header فاقد `SendToConsoleDate` و دارای OrderId و InvoiceId عددی مثبت.

هر ۹٬۷۹۵ Header دوم UUID سفارش BackOffice ندارند؛ Invoice UUID فقط برای ۳٬۵۹۳
مورد موجود است. نام `SendToConsoleDate` به‌تنهایی جهت یا موفقیت انتقال را ثابت
نمی‌کند؛ دو خوشه می‌توانند مسیر یا نسخه‌ی متفاوت باشند.

هیچ unique index روی شناسه‌های BackOffice نیست. در snapshot فعلی:

- ۱٬۱۲۵ OrderId عددی در بیش از یک Header NGT تکرار شده‌اند؛
- این گروه‌ها ۳٬۳۸۵ Header را پوشش می‌دهند؛
- بیشترین Header متصل به یک OrderId برابر ۱۳ است؛
- InvoiceId عددی همان ۱٬۱۲۵ گروه تکراری را دارد؛
- Invoice UUID تکراری نیست.

پس رابطه‌ی Header به BackOffice الزاماً یک‌به‌یک نیست.

## مدل فعلی Line و دو راه Crosswalk

از ۱٬۲۳۹٬۹۹۸ Line، تعداد ۱٬۲۲۰٬۸۴۰ فعال است. یتیم، Line فعال زیر Header
حذف‌شده و اختلاف ApplicationOwner/DataOwner/DataOwnerCenter با Parent صفر است.

۱٬۱۱۸٬۲۴۴ Line هم OrderRef عددی و هم Order UUID دارند و هیچ Ref عددی بدون UUID
نیست. اما توزیع Parent خلاف یک FK ساده است:

| راه Crosswalk | سفارش | Line فعال | Line فعال نگاشت‌شده |
|---|---:|---:|---:|
| فقط تمام Lineهای فعال | ۲۱۲٬۲۳۱ | ۱٬۱۱۸٬۲۳۸ | ۱٬۱۱۸٬۲۳۸ |
| بدون Crosswalk عددی | ۶٬۲۵۷ | ۳۹٬۹۴۰ | ۰ |
| فقط بخشی از Lineها | ۱ | ۷ | ۶ |
| فقط Header عددی | ۹٬۷۹۵ | ۶۲٬۶۵۵ | ۰ |

هفت سفارش NGT به دو Order BackOffice شکسته‌اند. هم‌زمان، ۱٬۱۲۵ OrderId Header
چند Header NGT را جمع می‌کنند. در نتیجه Split و Merge/Many-to-one هر دو در داده
فعلی دیده می‌شوند.

هر دو راه `ALL_ACTIVE_LINES_ONLY` و `HEADER_NUMERIC_ONLY` در ماه‌های ژوئن، ژوئیه
و اوت ۲۰۲۶ کنار هم وجود دارند؛ بنابراین صرفاً «نسخه قدیمی در برابر نسخه جدید»
اثبات نشده و احتمال تفاوت subsystem/path جدی است.

## Quantity و FK

- ۱٬۲۹۰٬۰۴۷ ردیف مقدار سفارشی و ۳۲٬۶۴۲ ردیف مقدار فاکتورشده وجود دارد؛
- یتیم، Detail فعال زیر Line حذف‌شده و اختلاف owner scope در هر دو جدول صفر است؛
- هر ۶۱ FK مرتبط فعال ولی `is_not_trusted=1` است؛ سلامت snapshot فعلی، اعتماد
  ساختاری FK را جایگزین نمی‌کند.

## Status history

`NGT.CustomerCallOrderStatus` در Clone صفر ردیف و هیچ PK/unique index ندارد. یک
مسیر مستقیم static از `CustomerCallController.AddToCustomerCallOrderStatus` به
writer transaction‌دار آن وجود دارد، ولی صفر ردیف فعلی نشان نمی‌دهد این مسیر در
عملیات حاضر فعال یا retained است. این جدول نباید به‌عنوان audit history کامل
فرض شود.

## قرارداد مقصد

مدل مقصد باید حداقل این اجزا را جدا کند:

- `MobileOrder` و `MobileOrderLine` با source UUID مستقل؛
- `OrderReplicationAttempt` با command id، source snapshot hash، transaction
  owner، stage و outcome؛
- `ExternalOrderLink` چندبه‌چند با grain صریح `HEADER` یا `LINE`، source version،
  valid-from/to و علت Split/Merge؛
- `OrderStateEvent` immutable برای Created/Edited/Canceled/Validated/Replicated/
  Finished/RolledBack؛
- `OrderQuantitySnapshot` برای Requested و Invoiced به‌جای overwrite؛
- Quarantine برای partial line map، no-map و تعارض crosswalk؛
- Outbox پس از commit برای اثرهای بیرونی.

`R-033` با این شواهد تقویت شد و ریسک تکراری جدید ساخته نشد. خروج از gate نیازمند
Golden case برای Header-only، Line-only، Partial، Split، Many-to-one و fault پس
از هر stage مسیر Update است.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/domains/ngt_order_persistence_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_order_runtime_boundary_20260829.json`
- `scripts/sql/extract_varanegar_ngt_order_persistence_boundary.py`
- `scripts/sql/extract_varanegar_ngt_order_runtime_boundary.py`
- `scripts/windows/build_varanegar_ngt_order_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/varanegar_ngt_order_checkpoint_20260829.json`
- `tests/test_varanegar_ngt_order_boundary.py`

SQL extractor فقط روی Clone مجاز READ_ONLY و IL extractor فقط روی DLLهای hash-pinned
اجرا می‌شود. هر اختلاف هش، شمارنده یا مسیر باید پیش از استفاده در طراحی مقصد
بازبینی شود. Checkpoint نیز فقط از Artifactهای redact‌شده و فایل‌های محلی هش‌دار
ساخته می‌شود و هیچ اتصال Database/Network/UI یا اجرای Assembly/Command ندارد.
