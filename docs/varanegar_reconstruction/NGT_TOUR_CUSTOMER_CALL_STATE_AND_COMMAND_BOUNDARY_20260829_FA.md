# مرز وضعیت و فرمان Tour/CustomerCall در NGT

تاریخ استخراج: ۲۰۲۶-۰۸-۲۹  
وضعیت: `READ_ONLY / STATIC_IL / NO_COMMAND`

## پاسخ کوتاه

Tour و CustomerCall در وارانگار یک CRUD ساده با یک ستون Status نیستند. وضعیت‌ها
میان چند متد Business، چند مسیر SQL، یک Trigger و ۲۹ Endpoint تغییر وضعیت پخش
شده‌اند. `PreviousStatusUniqueId` نیز تاریخچه نیست؛ فقط در بخشی از مسیر
Deactivate/Activate به‌عنوان حافظه‌ی بازگشت استفاده می‌شود.

در مقصد باید چهار مفهوم جدا داشته باشیم: state machine تایپ‌شده‌ی Tour، نتیجه‌ی
Visit، وضعیت دریافت Call، و وضعیت Delivery. یک Event log immutable باید همه‌ی
Transitionها را نگه دارد و Commandهای تغییردهنده فقط با HTTP unsafe method،
authorization، expected version و idempotency اجرا شوند.

## مرز ایمنی و شواهد

- چهار DLL deployed فقط به‌شکل PE metadata و IL byte خوانده شدند؛ Assembly load
  یا execution صفر است.
- SQL فقط روی `NeginPakhsh_WebDev` محلی، `READ_ONLY` و login عضو
  `db_denydatawriter` اجرا شد.
- Stored procedure، Endpoint و Application command اجرا نشد.
- UUID، هویت مشتری/کاربر، مختصات، Comment، Host و مقدار تنظیم در Artifactها
  ذخیره نشد.
- تعریف SQL ذخیره نشده؛ فقط Hash، طول، token count و نام امن Objectها ثبت شده است.

منابع اصلی:

- `artifacts/varanegar_analysis/domains/ngt_tour_call_state_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_tour_call_runtime_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_authorization_endpoint_coverage_20260828.json`

## ساختار داده‌ی جاری

| سطح | تعداد جاری | نکته |
|---|---:|---|
| Tour | ۶۴٬۵۶۱ | همه `IsRemoved=0` |
| CustomerCall | ۲٬۴۷۱٬۲۵۰ | همه `IsRemoved=0` و orphan Tour صفر |
| ستون‌های چهار جدول هدف | ۱۶۲ | Tours، CustomerCalls، BaseValues، BaseTypes |
| PK/Unique روی Tour و Call | ۲ | فقط `Id`؛ زوج Tour+Customer یکتا نیست |
| ماژول SQL مرتبط | ۹۵ | تعریف‌ها فقط fingerprint شدند |

Scope خود CustomerCall با Tour در وضعیت جاری سازگار است: orphan، child فعال زیر
Tour حذف‌شده و اختلاف Application/DataOwner/Center همگی صفرند. Lookup وضعیت Tour
در ApplicationOwner و DataOwner مشترک است، ولی Center همه‌ی ۶۴٬۵۶۱ Tour با
BaseValue متفاوت است. این ساختار به‌تنهایی خطا نیست؛ BaseValue عملاً lookup
مشترک owner-level است و نباید به‌زور center-owned تفسیر شود.

## Taxonomy واقعی وضعیت

شش وضعیت جاری Tour مشاهده شد:

| وضعیت معنایی | تعداد |
|---|---:|
| خاتمه یافته | ۴۹٬۳۵۴ |
| دریافت شده | ۱۰٬۶۵۹ |
| انصراف داده | ۳٬۴۱۹ |
| غیرفعال | ۱٬۰۳۵ |
| در حال دریافت اطلاعات | ۷۸ |
| ارسال شده | ۱۶ |

CallStatus چهار مقدار جاری دارد: در انتظار دریافت، تأییدشده، ابطال‌شده و عدم
قطعی. VisitStatus علاوه بر قطعی، عدم قطعی، عدم ویزیت، عدم سفارش، برگشتی کامل و
تحویل کامل، ۷۷۲ ارجاع به مقدار «تحویل قسمتی» از BaseType مستقل
`DistributionDeliveryStatus` دارد. تفکیک آن:

- ۵۵۰ Call تأییدشده با Active Order؛
- ۲۲۲ Call با CallStatus «عدم قطعی» و Active Order.

پس فیلد VisitStatus در عمل union چند taxonomy است. این می‌تواند تصمیم legacy
عمدی باشد و رخداد کاربر ادعا نمی‌شود، ولی در مقصد نباید DeliveryStatus داخل
VisitOutcome پنهان بماند.

همچنین ۲٬۸۳۳ Call «در انتظار دریافت / عدم قطعی» Active Order دارند و یک Call
«تأییدشده / قطعی» بدون Active Order است. این‌ها anomaly قطعی نام‌گذاری نشده‌اند؛
Golden case و تعریف مالک کسب‌وکار لازم است.

## State machine استاتیک Tour

| فرمان | Guard/حالت‌های دیده‌شده در IL | اثرهای اصلی دیده‌شده |
|---|---|---|
| `CancelTour` | Canceled، Deactivated، Sent و ReadyToSend بررسی می‌شوند | Status→Canceled، EndTime، Update+Save |
| `DeactivateTour` | ReadyToSend/Sent/InProgress/Received، Call confirmed و approvalها بررسی می‌شوند | PreviousStatus←Current، Status→Deactivated، Update+Save و direct non-query |
| `ActivateTour` | وضعیت فعلی و PreviousStatus بررسی می‌شوند | Status←PreviousStatus، Update+Save |
| `TourReceived` | Deactivated/Sent/InProgress بررسی می‌شوند | Status→Received یا Finished، EndTime، outline closing، Update+Save |
| `TourSentOld` | ReadyToSend | Status→Sent، StartTime، Update+Save |
| `TourSent` | مقدار SQL پویا redacted است | BeginTransaction→ExecuteNonQuery→Commit |
| `backToReadySendStatusTour` | مقدار SQL پویا redacted است | BeginTransaction→ExecuteNonQuery→Commit |
| `CloseTour` | ReadyToSend | Status→Deactivated، Start/End، Update+Save و direct non-query |
| `FinishTour` | Finished بررسی/تنظیم می‌شود | direct non-query→SaveChanges |
| `ConfirmTourReceived` | bulk expression | Status→Received و EndTime با UpdateBatch+Save |
| `ConfirmTourPayments` | Received بررسی می‌شود | approval و Save |
| `ConfirmDistTour` | تاریخ برگشت، کاربر BO و تنظیم third-party بررسی می‌شود | PaymentApproved و UpdateBatch+Save |

این جدول «تمام Transitionهای ممکن در هر branch» را ادعا نمی‌کند؛ نام getter/
setter و ترتیب Callهای compiled را ثبت می‌کند. سه خطای خواندن IL وجود داشت، ولی
هیچ‌کدام نام‌دار این مرز نبود و هر ۲۰ بدنه‌ی lifecycle هدف resolve شدند.

## PreviousStatus تاریخچه نیست

فقط ۴۵۵ Tour از ۶۴٬۵۶۱ مقدار PreviousStatus دارند. Current/Previous فعلی ۱۴
گروه می‌سازد و بیشتر Tourهای Finished، Received و Canceled مقدار Previous ندارند.
تنها جدول NGT که نام آن برای Tour/CustomerCall علامت Status/History دارد
`CustomerCallOrderStatus` است؛ همان جدول در Snapshot جاری صفر ردیف و بدون key
است.

نتیجه: `PreviousStatusUniqueId` را نمی‌توان audit log، chronology یا منبع rebuild
دانست. مقصد باید Transition event مستقل داشته باشد و PreviousStatus را فقط
reactivation pointer بداند، اگر مالک کسب‌وکار همین معنا را تأیید کند.

## مرز زمان

- Tour شروع‌شده: ۶۴٬۳۱۱؛ پایان‌یافته: ۶۳٬۸۴۹؛ هر دو: ۶۳٬۸۲۳.
- دو Tour در Snapshot جاری `EndTime < StartTime` دارند.
- CustomerCall شروع/پایان‌دار هرکدام ۱٬۰۹۲٬۶۲۸ و `EndTime < StartTime` صفر است.
- سه CustomerCall `VisitDuration < 0` دارند.
- ManualStart/ManualEnd در Snapshot جاری صفر است.
- ۱۶٬۰۳۹ Call فاقد CallDate هستند؛ بیشتر آن‌ها در stateهای تحویل یا عدم ویزیت/
  عدم قطعیت قرار دارند، بنابراین NULL به‌تنهایی corruption اعلام نشد.

هیچ هویت ردیفی ذخیره نشده است. دو و سه مورد زمانی باید در یک مرحله‌ی جداگانه‌ی
owner-approved reconciliation یا quarantine بررسی شوند.

## CustomerCall یک رخداد یکتا برای Tour+Customer نیست

۲۶٬۶۱۳ زوج Tour+Customer تکراری‌اند و ۵۷٬۳۹۱ Call داخل این گروه‌ها قرار دارند؛
بیشینه ۱۴ Call برای یک زوج است. پس در مقصد کلید یکتای `TourId+CustomerId`
اشتباه است. هر Call باید identity مستقل، sequence/version و رابطه با Visit attempt،
Order، Return، Payment و Delivery را حفظ کند.

## ذخیره‌ی چندمرحله‌ای Call

`SaveTourData` تنها direct caller استاتیک
`CustomerCallDomain.AddOrUpdateCustomerCallFromDevice` است. بدنه‌ی آن ۱۹ Call
نوشتنی دارد: چند Add/UpdateBatch، دو Update و یک SaveChanges؛ BeginTransaction
محلی ندارد، اما از مسیر SaveTourData که transaction بیرونی دارد فراخوانی می‌شود.
پس وقوع partial-write فعلی ادعا نمی‌شود؛ قرارداد مقصد باید transaction owner را
در signature فرمان صریح و testable کند.

`CustomerCallDomain.UpdateFromNGT` نیز UpdateBatch، child Order/Return update و
SaveChanges دارد. `CancelCallCancelation` وضعیت Confirmed را به Unconfirmed
برمی‌گرداند و هم bulk update و هم update/save دارد.

## Stored counterها Snapshot مشتق‌شده‌اند، نه تعریف قطعی

برابری‌های کاندید با فرزندان یکسان نیستند:

- CustomerCount با تعداد Call فقط در ۱۷٬۹۲۶ Tour؛
- CustomerCount با مشتری متمایز فقط در ۱۹٬۴۹۳ Tour؛
- VisitCount با Start/End در ۳۳٬۷۴۵ Tour؛
- OrderCount با Call دارای Active Order در ۶۳٬۰۷۳ Tour؛
- InvoiceCount با Call دارای Active Invoice در ۶۴٬۱۳۶ Tour.

این اختلاف‌ها corruption را ثابت نمی‌کنند، چون filter وضعیت، removal، نوع فروش یا
زمان snapshot ممکن است متفاوت باشد. تا تعریف مالک کسب‌وکار، این فیلدها باید
`legacy_snapshot_counter` باقی بمانند و از روی حدس rebuild نشوند.

## HTTP contract و ریسک GET

۲۹ Endpoint تغییر lifecycle Tour با caller/نام فرمان مشخص شد:

- ۲۴ Endpoint با HTTP `GET`؛
- پنج Endpoint با HTTP `POST`؛
- هر ۲۹ مورد دقیقاً یک NGT authorization declaration دارند؛
- ۲۵ مورد Resource/Action و چهار مورد Roles-or-empty هستند.

پس anonymous reachability و رخداد unauthorized ادعا نمی‌شود. بااین‌حال GET برای
mutation امن نیست: prefetch مرورگر، link scanner، retry/cache واسط، navigation
ناخواسته یا CSRF می‌تواند فرمان را بدون submit صریح تکرار کند. `R-062` این مرز را
با شدت High ثبت می‌کند.

## قرارداد مقصد

1. `TourState` تایپ‌شده و مستقل از `CallReceiptState`، `VisitOutcome` و
   `DeliveryOutcome`.
2. `TourStateEvent` و `CustomerCallStateEvent` immutable با previous/next، actor،
   owner scope، command id، expected version، reason و policy version.
3. Commandهای POST-only برای Send/Receive/Cancel/Deactivate/Activate/Finish/
   Confirm/Withdraw/Replicate؛ GET و HEAD هیچ اثر state/audit نداشته باشند.
4. `VisitAttempt` identity مستقل؛ uniqueness روی Tour+Customer ممنوع مگر با
   sequence صریح.
5. Approval state و Distribution return date به‌صورت transition guard نسخه‌دار.
6. Counterها projection قابل rebuild با تعریف owner-approved و snapshot version.
7. Quarantine برای taxonomy cross-type، time reversal، negative duration و
   transition بدون event.
8. Outbox پس از commit و command receipt یکتا برای retry/replay.

## Artifact و بازتولید

- `scripts/sql/extract_varanegar_ngt_tour_call_state_boundary.py`
- `scripts/sql/extract_varanegar_ngt_tour_call_runtime_boundary.py`
- `scripts/windows/build_varanegar_ngt_tour_call_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/varanegar_ngt_tour_call_checkpoint_20260829.json`
- `tests/test_varanegar_ngt_tour_call_state_boundary.py`

`R-008` با شواهد state/history توسعه یافت و `R-062` برای mutating GET اضافه شد.
رجیستر فعلی ۶۲ ریسک و Traceability فعلی ۲۴۴ اتصال دارد؛ صفر ماژول Command-ready
است. این صفر یعنی شناخت به اجرا مجوز نمی‌دهد تا Golden case، authorization،
idempotency، fault injection و reconciliation تکمیل شوند.
