# انتقال، Outbox و Receipt قواعد حسابداری

تاریخ شاهد: ۱۴۰۵/۰۶/۰۶ (2026-08-28)

## نتیجهٔ اصلی

تغییر `Article` و `ArticleComment` فقط در دیتابیس محلی نمی‌ماند. شش Trigger فعال
هر تغییر را به SQL اجرایی تبدیل و در `GNR.tblLog` ثبت می‌کنند. مالک انتقال در
بستهٔ اصلی `VN.SDS.Container` نبود؛ Deployment جداگانهٔ
`\\192.168.1.171\exe\Replication` آن را انجام می‌دهد.

سه فایل اصلی بدون Load یا اجرا Hash-pinned و IL آن‌ها parse شد:

- `VN.Replication.dll`؛
- `VN.ReplicationService.exe`؛
- `VaranegarMonitorReplication.exe`.

Artifact قابل بازتولید:

- `artifacts/varanegar_analysis/domains/rule_replication_transport_boundary_20260828.json`
- `scripts/sql/extract_varanegar_rule_replication_transport_boundary.py`
- `tests/test_varanegar_rule_replication_transport_boundary.py`

## مسیر ارسال

زنجیرهٔ ایستای IL این ترتیب را نشان می‌دهد:

1. `ReplicationServiceLibrary.Run` دریافت و ارسال دوره‌ای را Orchestrate می‌کند.
2. `ReplicationHelper.Replicate` تراکنش دیتابیس را باز می‌کند.
3. `SendLog` فایل بسته را می‌سازد.
4. فایل قبل از جلو بردن Watermark در `dbo.ReplicationFile` ذخیره می‌شود.
5. `dbo.ReplicationFile` ستون‌های `FileName`، `FileContent` و `InsertDate` دارد؛
   بنابراین یک Binary outbox پایدار است.
6. `dbo.ReplicationSend` Watermark مرکز را با `CenterId` و `SendId` نگه می‌دارد.
7. تراکنش Commit می‌شود.
8. `ReadAndUploadBinaryFile` Outbox را می‌خواند و سپس فایل را Upload می‌کند.

پس ترتیب Commit پیش از Upload به‌تنهایی شاهد گم‌شدن فایل نیست؛ Payload در Outbox
دیتابیسی مانده و مسیر Retry دارد. ادعای «Transport ناامن و بدون Outbox» رد شد.

مسیر Acknowledge نیز عمیق‌تر بررسی شد:

- در File-share، `SaveTolocal` ابتدا `File.Copy` و سپس Completion helper را صدا
  می‌زند؛ Completion با `File.Move` فایل را به نام/محل نهایی می‌برد؛
- در FTP، ابتدا `FtpClient.UploadFile`، سپس `GetFileSize`، Validation helper و
  در پایان `FtpClient.Rename` اجرا می‌شود؛
- در هر دو شاخه، Helper دیتابیسی پس از بازگشت Completion صدا زده می‌شود.

پس Completion marker قبل از Database acknowledgement helper تأیید شد. با این
حال متن Obfuscated آن Helper بازیابی نشد؛ فقط می‌دانیم یک فرمان دیتابیس اجرا
می‌کند، نه اینکه اثر دقیق آن قطعاً حذف چه Rowی است. مقایسهٔ اندازه نیز Hash
رمزنگاری‌شدهٔ محتوای مقصد نیست.

## مسیر دریافت و اجرا

دو مسیر Local-file و FTP جدا دیده شد، اما هر دو Contract یکسان مهمی دارند:

1. دریافت/Unzip و کنترل مقدماتی فایل؛
2. `DBConnector.BeginTransaction`؛
3. اجرای Script توسط `DatabaseHelper.Execute`؛
4. ثبت `LastExecLog` توسط `InsertLastExecutedlogIdUpdateLog`؛
5. Commit پس از ثبت Receipt؛
6. چند مسیر Rollback در خطا.

بنابراین اجرای Script و ثبت Watermark دریافت در یک Transaction boundary قرار
دارند. این شاهد فنی قوی است، ولی Result parity مالی را ثابت نمی‌کند.

رفتار خطای Executor نیز روشن شد: `DatabaseHelper.Execute` خروجی Boolean دارد،
مسیر موفق `true` و مسیر رد اولیه و Tail استثنا `false` برمی‌گردانند. Local و FTP
بلافاصله پس از Call روی `brtrue` Branch می‌کنند؛ مسیر `false` پیش از
`InsertLastExecutedlogIdUpdateLog`، `RollBackTransaction` دارد. پس فرض «خطای
Executor بلعیده می‌شود و همان Package Receipt موفق می‌گیرد» با مسیر Hash-pinned
فعلی رد شد. این هنوز اثبات نمی‌کند هر SQL موفق، اثر مالی درست و کامل دارد.

در لایهٔ پایین‌تر، `DBConnector.Execute` در Catch اتصال را می‌بندد و دوباره
`throw` می‌کند؛ Failure در Commit نیز Throw می‌شود. اما `RollBackTransaction`
یک Exception handler دارد و هیچ `throw/rethrow` در آن نیست. پس Rollback عادی
در مسیر خطا صدا زده می‌شود، ولی شکست خود Rollback به Caller یا Audit پایدار
اثبات‌شده‌ای نمی‌رسد. این Unknown-outcome boundary به `R-007` متصل شد.

یک مرز Cross-resource جدا نیز قطعی است. بعد از ثبت Receipt و پیش از Commit:

- Local یک Archive copy می‌سازد و چند File delete دارد؛
- FTP چند فایل محلی و خود فایل Remote را حذف می‌کند؛
- سپس Commit دیتابیس فراخوانی می‌شود.

اگر Commit Throw کند، SQL قابل Rollback است اما File/FTP در همان Transaction
شرکت ندارند. نسخهٔ Archive محلی شاهد مثبتی است، ولی Retry خودکار و قطعی از آن پس
از Commit failure اثبات نشد؛ در FTP نیز Remote package پیش از Commit حذف شده است.
رخداد Runtime مشاهده نشده، اما Failure window ترتیب کد قطعی و در `R-007` است.

در Local یک مرحلهٔ دیگر پس از Commit اصلی دیده شد:
`ResetReplicationSendTable` در تراکنش مستقل دو فرمان دیتابیس اجرا می‌کند، Commit/
Rollback دارد و Boolean موفق/ناموفق برمی‌گرداند؛ Caller نتیجه را بلافاصله `pop`
می‌کند. متن SQL Obfuscated بازیابی نشد، پس اثر دقیق Reset ادعا نمی‌شود و Failure
Runtime نیز دیده نشده است. نتیجهٔ قطعی فقط این است که شکست این Maintenance نتیجهٔ
Orchestration محلی را تغییر نمی‌دهد و به `R-007` اضافه شد.

## Receipt چه چیزی را ثابت می‌کند؟

`GNR.tblLogRcv` این Shape را دارد:

- Source/Site؛
- `StartLog` و `EndLog`؛
- `LastExecLog`؛
- زمان و نام فایل.

اما هیچ ستون صریح برای موارد زیر ندارد:

- Rule/Policy version؛
- Publisher و Approver؛
- Content hash/checksum؛
- Success/business-effect reconciliation.

پس Receipt می‌تواند بگوید مصرف تا کدام Watermark پیش رفته، اما نمی‌تواند اثبات
کند کدام نسخهٔ immutable و تأییدشدهٔ Rule فعال شده یا خروجی مالی آن با مبدأ برابر
است.

## Retry، ترتیب و هم‌زمانی Receipt

کاتالوگ Index و متن ایستای Trigger رسید نشان می‌دهد:

- `ReplicationFile.FileName` قید یکتا ندارد؛
- `ReplicationSend.CenterId` قید یکتا ندارد؛
- `tblLogRcv` فقط روی `ID` کلید اصلی دارد و Indexهای Site/range/file غیر‌یکتا هستند؛
- Trigger بازهٔ معکوس و کاهش `EndLog`/`LastExecLog` را رد می‌کند؛
- برابری Watermark، یعنی Replay همان مرز، رد نمی‌شود؛
- `StartLog = previous EndLog + 1` الزام نشده است؛
- Trigger از `inserted` انتساب Scalar دارد و برای درج چندردیفی Set-safe اثبات نشد؛
- History درج/حذف وجود دارد، اما جای قید یکتایی و Idempotency receipt را نمی‌گیرد.

پس Guard موجود **Monotonic** است، نه اثبات کامل Unique/Replay-safe/Gapless. چون
`tblLogRcv` در Clone صفر ردیف دارد، وقوع Duplicate یا Gap در Production ادعا
نمی‌شود. این شاهد به ریسک عمومی Retry یعنی `R-006` متصل شد.

Concurrency فرستنده نیز Gate قطعی ندارد. Start و Run یک `ControlLock` نام‌دار
را صدا می‌زنند، اما گراف بررسی‌شدهٔ آن صفر Mutex، صفر Monitor و صفر DBConnector
call دارد و فقط یک `File.Exists` دیده شد؛ پس این نام به‌تنهایی قفل Cross-process
یا DB lease را ثابت نمی‌کند. Watermark ارسال با Queryهای concatenated خوانده و
به‌روزرسانی می‌شود و `ReplicationSend.CenterId` نیز Unique نیست. در نتیجه
Serialization یک Sender برای هر مرکز اثبات نشد. جدول خالی Snapshot وقوع Race
واقعی را نشان نمی‌دهد. Connector نیز Overload تک‌رشته‌ایِ نام Transaction را
صدا می‌زند و IsolationLevel صریح در این Call اثبات نشد؛ پس این Transaction به
تنهایی جای قید Unique یا Lock دارای fencing را نمی‌گیرد.

ترتیب ورودی نیز تضمین صریح ندارد: مسیر Local از `Directory.GetFiles` و مسیر FTP
از `FtpClient.GetListing` استفاده می‌کنند، اما در Receiverها و Helper Listing
هیچ `Sort`/`OrderBy` نام‌داری دیده نشد. نبود این Call به‌تنهایی وقوع پردازش
خارج‌ترتیب را ثابت نمی‌کند، ولی همراه با نبود Guard پیوستگی Range، ترتیب قطعی پیش
از Execute را اثبات‌نشده می‌گذارد. Snapshot خالی Receipt نیز Incident واقعی را
نشان نمی‌دهد.

## Timer و Single-flight اجرای سرویس

`InitTimer` یک `System.Timers.Timer` با Constructor بدون آرگومان می‌سازد، Interval
را تنظیم می‌کند، Handler رخداد `Elapsed` را متصل و Timer را Enabled می‌کند. در
همین متد Setterهای `AutoReset` و `SynchronizingObject` دیده نشدند. `Run` نیز یک
`Thread.Sleep` دارد، اما در Call graph آن Mutex، Monitor، Interlocked، Semaphore
یا ReaderWriterLock دیده نشد. `ControlLock` نام‌دار ابتدای Run، در گراف
بررسی‌شده Mutex/Monitor/DB lease ندارد و بنابراین از روی نام آن نمی‌توان
Single-flight را نتیجه گرفت. مقدارهای ثابت `Timer.Enabled` در `InitTimer` و `Run`
فقط `true` هستند؛ `Run` هیچ تنظیم صریح `false` ندارد، درحالی‌که `Stop` مقدار
`false` می‌گذارد.

نتیجهٔ دقیق این است که non-reentrant بودن callback دوره‌ای **اثبات نشد**؛ نه
این‌که هم‌پوشانی حتماً در Production رخ داده باشد. Config زمان‌بندی خوانده نشد و
هیچ نمونهٔ Runtime overlap مشاهده نشد. مقصد باید هر Tick را با lease دارای fencing
یا single-flight صریح اجرا کند، Tick هم‌زمان را coalesce کند و تست «اجرای طولانی‌تر
از Interval» داشته باشد. این مرز به `R-006` متصل شد.

در خود Executor بسته نیز سه ثابت واردشده به `CommandTimeout` برابر ۰، ۶۰۰ و
۳۰۰۰۰ دیده شد؛ Connector عمومی ثابت ۶۰۰ دارد. این اعداد از IL هستند و SQL خام یا
Config خوانده نشده است. چون حداقل یک شاخه مقدار صفر می‌فرستد و Cancellation/
Deadline سراسری در گراف اثبات نشد، «مهلت مثبت و محدود برای همهٔ مسیرها» پذیرفته
نشد. این شاهد ثابت نمی‌کند کدام بستهٔ واقعی وارد کدام شاخه شده یا اجرای طولانی در
Production رخ داده است. مقصد باید Deadline محدود، cancellation propagation و
Quarantine جداگانه برای Timeout داشته باشد.

## سرنوشت Package ردشده

مسیر استاندارد Local از Overload سه‌پارامتری `ExecuteLocalFile` می‌گذرد؛ Wrapper
به Overload اصلی با Flag ثابت `false` Delegate می‌کند و Caller خروجی آن را `pop`
می‌کند. وقتی Executor مقدار false برگرداند، Rollback پیش از پنج Call حذف فایل
قرار دارد، سپس مرکز به فهرست `addDefectiveCenter` افزوده می‌شود. در همین بازه
`File.Move` برای Quarantine دیده نشد. نقش دقیق هر پنج Path به‌علت Redaction و
نخواندن Config ادعا نمی‌شود.

در شاخهٔ FTP، false نیز ابتدا Rollback و سپس سه حذف فایل محلی دارد؛ در همین بلوک
`FtpClient.DeleteFile` صفر است. این به‌تنهایی حفظ قطعی Remote در همهٔ مسیرهای
بعدی را ثابت نمی‌کند. نتیجهٔ امن این است که Quarantine پایدار و Retry parity میان
Local و FTP اثبات نشده است. هیچ Package ردشدهٔ Runtime مشاهده نشد. مقصد باید
`RECEIVED → VALIDATING → QUARANTINED/RETRYABLE → APPLIED → ACKED` را با Receipt
پایدار و Payload immutable پیاده کند.

## امنیت شاخهٔ FTP و اصالت Package

نسخهٔ `FluentFTP.dll` مستقر `32.4.3.0` و Hash آن نیز Pin شد. IL مسیر
`ConnectToFtpServer` نشان می‌دهد:

- `FtpClient` با Constructor پیش‌فرض ساخته می‌شود؛
- Credential تنظیم می‌شود؛
- `EncryptionMode` تنظیم نمی‌شود؛
- `SslProtocols` تنظیم نمی‌شود؛
- Certificate validation تنظیم نمی‌شود؛
- Constructor کتابخانه نیز `m_encryptionmode` را مقداردهی نمی‌کند و مقدار صفر
  Enum برابر `None` است.

Package هنگام ساخت و Extract دارای Zip password است، اما در Call graph نام‌دار
Send/Receive هیچ `ComputeHash`، HMAC، Signature یا Verify call وجود ندارد. Password
به‌تنهایی هویت فرستنده و یکپارچگی نسخهٔ Rule را اثبات نمی‌کند.

خود Executor نیز متن را به `SqlCommand.CommandText` می‌دهد و `ExecuteNonQuery`
صدا می‌زند. متد Executor، Validator نام‌دار `ISValidRecordToInsert` را صدا نمی‌زند؛
در هر دو مسیر Local و FTP نیز یک فراخوانی Executor پیش از فراخوانی بعدی همین
Validator قرار دارد. پس یک Allowlist تایپ‌شده و همگانی پیش از اجرای تمام Scriptها
از مسیر کد اثبات نشد. این نتیجه به معنی بی‌اثر بودن همه کنترل‌های متنی داخلی
نیست؛ متن Obfuscated بازسازی یا اجرا نشد.

Lookup مرکز/Site پیش از Unzip انجام می‌شود، اما دو Helper مربوط هرکدام یک ورودی
`string` می‌گیرند، آن را با `String.Concat` وارد Query کرده و `ExecuteScalar`
می‌زنند. Parameterization و Dataflow دقیق Validation نویسه‌های File-name تا Lookup
اثبات نشد. این به‌تنهایی SQL injection جاری را ثابت نمی‌کند؛ نوع نهایی خروجی
`int32` است و ممکن است Guardهای غیرنام‌دار وجود داشته باشند. نتیجهٔ محدود این است
که Lookup مرکز، امضای رمزنگاری‌شدهٔ Center/Package نیست و باید در مقصد با Parser
تایپ‌شده و Query پارامتری جایگزین شود.

این نتیجه دربارهٔ **شاخهٔ FTP قابل‌فعال‌سازی** است. File-share نیز پشتیبانی می‌شود
و Config فعال Production عمداً خوانده نشد؛ بنابراین استفادهٔ واقعی یک مرکز مشخص
از FTP ادعا نشده است.

## Hook پس از دریافت و مرز Authority

ترتیب IL در `ReplicationServiceLibrary.Run` نشان می‌دهد `Receive` برمی‌گردد و
بعد سرویس یک Script فعال را از تنظیمات می‌گیرد و با `DBConnector.Execute` اجرا
می‌کند. خود `Run` یک Transaction دیتابیس مشترک دور Receive و این Hook ندارد.

در SQL مستقر، Wrapper نام‌دار `usp_ReplicationAfterReciveAll` دو Hook دارد:

- `USP_VSA_SortTblLog`: روی `tblLog`، `tblLogRcv` و `ReplicationError` کار
  Update/Delete دارد و Transaction + TRY/CATCH + Rollback خودش را دارد؛
- `GNR.uspSetIdentityColValue`: از تنظیمات Server/Column استفاده می‌کند، Insert و
  Dynamic execute شامل DBCC `CHECKIDENT` دارد، اما Transaction و TRY/CATCH خودش
  دیده نشد.

Wrapper نیز Transaction/TRY/CATCH ندارد. بنابراین اگر این Wrapper همان Script
فعال باشد، Receipt فایل می‌تواند Commit شده باشد و Maintenance بعدی مسیر شکست
جدا داشته باشد. اما نگاشت دقیق Script فعال از Config عمداً خوانده نشد؛ پس
فعال‌بودن این Wrapper در Production یا وقوع شکست ادعا نمی‌شود.

`GNR.uspSetIdentityColValue` نام جدول/ستون را از `dbo.ColvalueTable` می‌گیرد و
در متن مستقر `QUOTENAME` ندارد. با این حال Clone فعلی در این جدول **صفر Row**
دارد؛ پس هیچ هدف Identity جاری، Token نامعتبر یا Mutation مشاهده‌شده‌ای ادعا
نمی‌شود. Config فعال Production و برابری آن با Clone همچنان نامعلوم است.

برای ۹ ماژول Scoped، Execute-as و مالک Object اختصاصی صفر و Permission صریح
Object-level نیز صفر بود. این **به معنی نداشتن دسترسی سرویس نیست**؛ Role membership،
Ownership chaining و Principal واقعی سرویس می‌توانند Authority بدهند و چون Config
هویت سرویس خوانده نشد، Effective authority اثبات‌نشده باقی می‌ماند.

## Snapshot فعلی Clone

- `GNR.tblLog`: ۴۶٬۰۲۳٬۸۰۹ ردیف؛
- رویدادهای Article/ArticleComment نگه‌داری‌شده: ۱٬۱۳۲؛
- رویداد Article در بازهٔ سه‌ماهه: ۴ Update؛
- `dbo.ReplicationFile`: صفر؛
- `dbo.ReplicationSend`: صفر؛
- `GNR.tblLogRcv`: صفر؛
- `GNR.tblLogSnd`: صفر.

این صفرها ممکن است حاصل Clone/sanitization یا پاک‌سازی تاریخی باشند؛ استفاده‌نشدن
Replication در Production را ثابت نمی‌کنند. فقط می‌گویند Snapshot حاضر شاهد
Delivery همان چهار تغییر اخیر را نگه نداشته است.

این Caveat اکنون شاهد فنی هم دارد: سرویس پیش از Receive و نیز مسیر Replicate یک
Helper پاک‌سازی Receipt را صدا می‌زند. Procedure مستقر
`usp_Replication_ClearReplicationReceive` با `LastExecLog` و `MAX` کار می‌کند و
از `tblLogRcv` حذف دارد؛ Transaction و TRY/CATCH داخلی در آن دیده نشد. اتصال
دقیق Helper مبهم به همین Procedure به‌علت متن Obfuscated اثبات نشد، اما وجود
مسیر Cleanup و Procedure سازگار باعث می‌شود Receiptهای باقی‌مانده تاریخچهٔ کامل
تلقی نشوند.

این Procedure از `tblLog` اصلی حذف ندارد. با این حال سه Procedure مستقل ایجاد
مرکز، حذف/Truncate دقیق `tblLog` دارند و Transaction/TRY-CATCH داخلی‌شان دیده
نشد. اجرای آن‌ها یا علت وضعیت فعلی ادعا نشده است؛ نتیجهٔ محدود این است که
۱٬۱۳۲ Log Rule نگه‌داری‌شده نیز Audit immutable و کامل تاریخ سیستم نیست.

## قرارداد مقصد نگین ERP

1. Rule به‌صورت نسخهٔ immutable منتشر شود، نه SQL ردیفی دلخواه.
2. Outbox و Inbox هر دو Content-addressed و دارای Manifest hash باشند.
3. Publisher، Approver، Policy version و Scope به Payload امضاشده متصل باشند.
4. Apply فقط با Command نسخه‌دار و idempotent انجام شود.
5. Payload خارج‌ترتیب، دست‌کاری‌شده یا بدون Approval پیش از Activation قرنطینه شود.
   Token مرکز/DC نیز پیش از Lookup به نوع محدود تبدیل و Query کاملاً پارامتری باشد.
6. Receipt مرکز مقصد شامل Version، Hash، Apply result و زمان باشد.
7. Reconciliation نسخهٔ فعال و اثرهای مالی Golden مستقل از Watermark انتقال باشد.
8. `LastExecLog` به‌تنهایی هرگز Publish approval یا Business parity تلقی نشود.
9. Inbox/Outbox با کلید یکتای `center+package+version` ساخته و Replay همان کلید
   به نتیجهٔ قبلی متصل شود؛ بازهٔ خارج‌ترتیب یا دارای Gap فقط با Policy صریح
   پذیرفته شود.
   Packageها پیش از Execute از Metadata تایپ‌شدهٔ Range مرتب شوند و تست Listing
   درهم‌ریخته، Gap و Overlap پیش از هر Mutation Fail-closed باشد.
   Sender نیز Lease/DB application lock دارای fencing token برای هر Center داشته
   باشد و دو Instance نتوانند Range هم‌پوشان تخصیص دهند.
10. Receipt بسته و Receipt عملیات پس از دریافت جدا اما به یک Package/version
    متصل باشند؛ شکست Maintenance قابل مشاهده، idempotent و قابل Retry باشد.
11. هویت سرویس Least-privilege باشد و Effective permission آن با Readback و
    Deny test اثبات شود؛ نبود Grant صریح Object به‌تنهایی شاهد Deny نیست.
12. Audit انتشار/اعمال Rule خارج از جدول‌های قابل Cleanup و به‌صورت append-only
    و externally anchored نگه‌داری شود.

## ریسک و سطح اطمینان

- `R-055` — اشتباه‌گرفتن Watermark انتقال با Provenance نسخهٔ مصوب Rule — `HIGH`.
- `R-056` — حمل SQL اجرایی در شاخهٔ FTP بدون Encryption/Certificate validation
  صریح و بدون Content signature — `CRITICAL`.
- `R-006` — تکرار اثر در Retry؛ Receipt فعلی Unique/Replay-safe/Gapless اثبات
  نشده است — `CRITICAL`.
- Outbox باینری و Transaction دریافت: **تأییدشده از IL Hash-pinned و Schema**.
- جلوگیری از Receipt پس از `false`/Exception Executor: **تأییدشده**.
- مشاهده‌پذیری/Propagation شکست خود Rollback: **اثبات‌نشده**.
- بازیابی خودکار Package پس از Commit failure در فاصلهٔ Cleanup: **اثبات‌نشده**.
- Propagation نتیجهٔ ناموفق Reset پس از Commit محلی: **ردشده**.
- Completion محلی/FTP پیش از Database acknowledgement helper: **تأییدشده**.
- اثر دقیق Database acknowledgement helper و Hash محتوای Remote: **اثبات‌نشده**.
- موفقیت Delivery چهار تغییر اخیر در Production: **اثبات‌نشده**.
- اتمیک‌بودن Maintenance پس از دریافت با Receipt فایل: **اثبات‌نشده**.
- Principal و Effective authority سرویس: **اثبات‌نشده**.
- کامل‌بودن تاریخچهٔ Receipt/Log باقی‌مانده: **ردشده به‌عنوان فرض قابل اتکا**.
- گم‌شدن قطعی فایل یا شکست مشاهده‌شده: **ادعا نشده**.
- فعال‌بودن FTP در مرکز مشخص Production: **اثبات‌نشده**.

## ایمنی

- هیچ EXE/DLL Load یا اجرا نشد؛ فقط PE metadata و IL parse شد.
- هیچ Config، Archive، ZIP، Log یا Credential خوانده نشد.
- هیچ Script تولیدشده یا Procedure عملیاتی اجرا نشد.
- هیچ مقدار خام SQL، Connection string یا Business row در Artifact ذخیره نشد.
