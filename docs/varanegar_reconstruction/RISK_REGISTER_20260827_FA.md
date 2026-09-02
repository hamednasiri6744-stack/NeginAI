# دفتر ریسک بازسازی وارانگار و ERP شخصی نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۵۶ ریسک باز؛ ۳۱ بحرانی، ۲۲ بالا و ۳ متوسط؛ Validation برابر PASS**

## نتیجه

تمام چهارده ماژول حداقل یک ریسک با Control و Exit criterion دارند. Severity
اثر بالقوه را نشان می‌دهد؛ برای Likelihood عدد ساختگی تولید نشده است. هیچ ریسک
در این Artifact پذیرفته یا بسته نشده و بسته‌شدن فقط با شاهد تازه و برآورده‌شدن
همه Exit criterionها مجاز است.

## سی‌ویک ریسک بحرانی

1. `R-001`: Write ناخواسته به وارانگار عملیاتی؛
2. `R-003`: تبدیل حقوق تجمیعی Legacy به Grant اشخاص؛
3. `R-004`: نشت PII/Secret/Business value در Artifact، Log یا Browser؛
4. `R-005`: تکثیر CRUD و حذف Invariant/History/Ledger؛
5. `R-006`: ایجاد نتیجهٔ تکراری در Retry؛
6. `R-007`: Commit ناقص میان چند Aggregate؛
7. `R-008`: یکی‌گرفتن Snapshot/Ledger/Current pointer؛
8. `R-011`: اشتباه‌گرفتن کد mode-dependent مسیر توزیع با ID مستر یتیم؛
9. `R-012`: Rebuild موجودی از Cardex-only و حذف تعهد فروشِ بدون خروج؛
10. `R-013`: جایگزینی Gross برگشت فاکتور به‌جای Net رسمی و ایجاد اعتبار/ابطال غلط؛
11. `R-014`: یکی‌کردن مالک چک، Customer تخصیص و Customer فاکتور و از دست دادن
    تخصیص معتبر Cross-party و پایه‌های حسابداری مرتبط؛
12. `R-019`: Backup بدون Restore اثبات‌شده؛
13. `R-025`: پذیرش `blocking_unknown` برای رسیدن به زمان‌بندی.
14. `R-027`: پورت Receipt replication پرتراکم POS به‌عنوان Command مبهم و
    غیرقابل-Reconcile.
15. `R-032`: تخت‌کردن Viewهای قابل‌نوشتن خزانه و حذف اثر Trigger/Log/Accounting.
16. `R-033`: تبدیل مسیر درخواست/فروش/برگشت و ۷۳ Trigger فعال آن به CRUD صفحه.
17. `R-034`: تبدیل Draft/Confirm/Return سند انبار و توزیع تا خروج با ۸۷ Trigger
    فعال به CRUD مستقیم.
18. `R-035`: کپی خاموش/روشن‌کردن Trigger محافظ رابطهٔ فاکتور خرید و سند انبار.
19. `R-036`: تبدیل تولید سند حسابداری از سند مبدأ به ثبت دستی و CRUD دفتر کل.
20. `R-041`: تخت‌کردن چهار مرز تاریخ قطعی فروش/خرید/مالی/تنخواه در یک Setting
    و ازبین‌بردن Scope، Reopen، Validation و Audit.
21. `R-042`: یکی‌گرفتن Master `TblCheque.PayId` با مرجع Pay تأییدشده یا تکرار
    نقص مسیر تأیید گروهی که `LegalType` را به رخداد History منتقل نمی‌کند.
22. `R-043`: حل خاموش Fork وضعیت سند حسابداری با MAX/Delete یا تکرار Failure
    path تغییر وضعیت که CATCH آن Rollback صریح ندارد.
23. `R-045`: یکی‌کردن دو حالت NGT Return، بازسازی دوباره‌ی Result تاریخی با
    هدف جاری غایب، یا Commit سند رسمی پیش از Crosswalk پایدار و idempotent.
24. `R-046`: اعتماد به Validator برگشت از تأمین‌کننده که Goodsهای بدون Match را
    با `INNER JOIN` حذف می‌کند، تفاوت مسیر Desktop/SDSNET را نادیده می‌گیرد یا
    ۲۰ TollRef قدیمیِ قابل‌بازیابی از View رسمی را به‌اشتباه حذف می‌کند.
25. `R-047`: بازسازی یا Replay صدور سند با Policy جاری و تغییر Grain تاریخی؛
    سال ۱۴۰۵ اکنون Mode 1 است، اما ۳۶۶ از ۳۸۲ Header چندمنبعی‌اند. مسیر Desktop
    Transaction بیرونی دارد، ولی خود `usp_DoExternalVoucher` Transaction owner
    نیست.
26. `R-049`: اتکا به دسترسی کلی صفحه برای صدور، تأیید، برگشت تأیید، حذف و انتقال
    سند؛ برای این پنج عمل مجوز مستقل سمت Server یا Scope سال/DC/نوع/Header پیدا
    نشد. دسترسی کلی منو ممکن است بیرون این مسیر باشد و باید جداگانه اثبات شود.
27. `R-050`: صدور خرید از `MIN(DefeniteDate)` فقط روی ردیف‌های موجود ICA استفاده
    می‌کند و completeness همهٔ StockDCها را نمی‌سنجد؛ سال ۱۴۰۵ دو ردیف از ده
    انبار Scope موجود نیست. استثنای حقوق نیز دو نوع و صفر نمونهٔ تاریخی دارد.
28. `R-052`: View سازندهٔ staging مالی با `WITH(NOLOCK)` خوانده می‌شود؛ Transaction
    بیرونی writeهای صدور را اتمیک می‌کند اما snapshot committed منبع را تضمین
    نمی‌کند. رخداد dirty-read اجرا یا مشاهده نشده است.
29. `R-053`: نام View، Fieldها، Predicateها و recipe شرح از پیکربندی به SQL الحاقی
    تبدیل و در دو محل اجرا می‌شوند. اسکن فعلی ۱۱ دسته fragment پاک است، ولی این
    پاکی ریسک طراحی executable configuration را حذف نمی‌کند.
30. `R-054`: دو Procedure بدون پارامتر انتقال Template، Viewهای سازنده و پنج جدول
    Rule را با پنج محل SQL پویا و شش Trigger فعال تغییر می‌دهند، اما Transaction،
    TRY/CATCH، Authorization یا نسخهٔ انتشار ندارند. Child نیز دو ستون حذف‌شدهٔ
    `VoucherCreatorId` و `ArticleCaption` را نام می‌برد و در Schema جاری هنگام
    Dynamic INSERT شکست می‌خورد، پس Parent می‌تواند پیش از شکست بخشی از Ruleها را
    تغییر داده باشد. Application Caller/Form صفر و دسترسی حساب تحلیل نیز صفر است؛
    Authority ادمینی و فراوانی اجرا نامعلوم است.
31. `R-056`: Receiver بستهٔ Password-protected شامل SQL اجرایی را اجرا می‌کند،
    اما شاخهٔ FTP مستقر `FluentFTP 32.4.3` را با EncryptionMode پیش‌فرض `None`
    و بدون Certificate validation به کار می‌گیرد و Package نیز Hash/HMAC/Signature
    ندارد. File-share هم موجود است و Mode فعال Production خوانده نشده؛ پس این
    ریسک Capability شاخهٔ FTP است، نه ادعای استفادهٔ مرکز مشخص.

این ریسک‌ها با «کد وجود دارد» بسته نمی‌شوند. Deny test، Fault injection،
Reconciliation، Restore drill، Readback و تأیید مسئول لازم است.

## ریسک‌های دادهٔ شناخته‌شده

- فاصلهٔ ۱٬۵۹۴ کلیدی Cardex-only نباید به‌اشتباه خرابی تلقی یا با Overwrite «اصلاح» شود؛ این فاصله دقیقاً تعهد فروشِ هنوز خارج‌نشده است و Residual فرمول رسمی صفر است؛
- ۶۹۶ اختلاف فعال Gross/Net فساد داده نیست؛ قرارداد رسمی Net در ۱۴٬۰۹۱ سند
  Residual صفر دارد. ریسک، استفاده از Gross به‌جای Net یا حذف Provenance اجزاست؛
- ۴۹ Settlement میان مشتری‌ها همگی تخصیص اولیه‌ی دقیق دارند و فساد داده نیستند؛
  ریسک واقعی، یکی‌کردن مالک چک با Customer تخصیص/فاکتور و از دست دادن پایه‌های
  حسابداری Cross-party است؛
- هشت Master `PayId` خالی لینک مفقود نیستند: هر هشت `History.PayId2` معتبر و
  تأییدشده دارند. ۳۵ `LegalType` تهی نیز باید `UNKNOWN_SOURCE` بماند؛ ریسک واقعی
  گم‌شدن نوع ارجاع در مسیر تأیید گروهی است. ۱۵۵ برگ دسته‌چک Used بدون Cheque
  حالت پشتیبانی‌شده‌ی `SOURCE_USED_UNLINKED` هستند؛ علت تاریخی‌شان به‌دلیل نبود
  Actor/Time نامعلوم است و نباید پاک، مصنوعی یا «دستیِ قطعی» نام‌گذاری شوند؛
- ۲۶٬۰۸۶ Distribution دارای کد عددی معتبرِ mode-dependent هستند؛ نباید آن‌ها
  را FK یتیم دانست، به `tblDistPath.ID` وصل کرد یا به Default path برد؛
- Barcode/Party/Routeهای ambiguous فقط با Crosswalk کیفیت‌دار و Review حل می‌شوند.
- ۱٬۰۹۴ سند حسابداری دارای ۱۴٬۹۴۶ رخداد بعد از Current pointer هستند؛ ۱٬۰۹۱
  Fork وضعیت متفاوت دارند. Pointer و رخدادهای detached هر دو باید تا تصمیم
  حسابدار حفظ شوند؛ MAX و حذف خودکار ممنوع است.
- یک Header فعالِ بدون قلم، Draft دستی با اثر مالی صفر اما دارای شماره منبع است؛
  Line مصنوعی، Posting یا reuse خاموش شماره ممنوع و با `R-044` کنترل شده است.
- دو NGT Return بدون سند رسمی جاری دو وضعیت مستقل‌اند: یکی بدون Result تاریخی
  و دیگری دارای Result دقیق `TourHistory` ولی هدف جاری غایب. `R-045` ساخت
  خودکار سند، Join مستقیم UUID مدل NGT به ID عددی FRU/SLE و Retry بدون
  Reconciliation را منع می‌کند.
- ۱۵۶ گروه سندی مرجوعی دارای Source در Grain تجمعی Validator به ۱۱۵ گروه
  `(SupInvoiceRef,Goods)` می‌رسند؛ هفت Goods در قلم فاکتور منبع نیستند، ولی هر
  هفت با خروج نوع ۵۵ دقیق و Price/Amount غیرصفرند؛ Invoice فقط Hint اختیاری است.
  Unique index `(HdrRef,GoodsRef)` و Duplicate صفر، یکتایی سمت Source را ثابت
  می‌کند؛ مقصد باید این Invariant را حفظ یا تجمیع را صریح کند.
  در Matchها Over-return صفر است، اما SQL مستقر Guard یکسان و قابل اتکا نیست.
  `R-046` کپی Validator و Reassign/Reprice حدسی را منع می‌کند.
- ۲۰ Explicit TollRef در یک برگشت به ID جاری وصل نیستند، ولی هر ۲۰ با قاعدهٔ
  رسمی Same-header TollRef یکتا Resolve و در View سازگاری دیده می‌شوند؛ Missing
  و Ambiguous صفر است. Provenance خام حفظ و فقط Mapping مؤثر جدا ثبت شود.
- ۲٬۳۷۰٬۵۶۹ PreVoucher line همگی به Header معتبر و Marked وصل‌اند؛ Header بدون
  Line، Orphan و عدم تراز صفر است. این سلامت، مسیر Desktop را تأیید می‌کند اما
  نسخهٔ Policy تاریخی را برنمی‌گرداند. در سه ماه منتخب ۲۷٬۱۷۷ Source group در
  فقط ۲۰۴ Header قرار دارد، در حالی که Mode فعلی ۱۴۰۵ تک‌Source است. `R-047`
  ذخیرهٔ immutable Policy snapshot روی هر Batch و Transaction owner سمت Server
  را اجباری می‌کند.
- همین ۲٬۳۷۰٬۵۶۹ Stage line در تاریخچه به ۱٬۲۸۷٬۸۷۴ قلم رسمی تجمیع شده‌اند؛
  Cardinality هر ۱۱ Creator دقیقاً با Grain قدیمیِ بدون ReferenceNo/debit-side
  تطبیق دارد، ولی Procedure فعلی از همان Stageها ۱٬۴۲۴٬۰۳۹ قلم می‌سازد. Replay
  با کد امروز ۱۳۶٬۱۶۵ قلم اضافی می‌دهد، هرچند Total مالی برابر بماند. همچنین ۴۸
  Rule از ۱۴۹ Rule فعال هیچ نمونهٔ تاریخی ندارند. `R-047` حفظ Line grouping
  version و Golden case مستقل آن ۴۸ Branch را نیز اجباری می‌کند.
- مسیر انتقال سند، `SetVoucherNo` مانده را پیش از Validator پاک می‌کند و خطای
  کسب‌وکار Validator با `RETURN` عادی می‌تواند همان Cleanup را Commit کند. Clone
  فعلی ۱۹۷٬۵۱۸ Crosswalk سالم و صفر Orphan/Duplicate دارد، پس `R-048` ریسک مسیر
  کد است نه خرابی مشاهده‌شده؛ Validation مقصد باید کاملاً بدون Side effect باشد.

## ریسک‌های شناخت و Runtime

`R-002` Drift نسخه/Schema، `R-016` حذف سه فرم Root حل‌نشده، `R-023` تلقی Clone
به‌عنوان Live truth و `R-024` تعمیم Session چهار فرم باز به همه نقش‌ها ثبت شده‌اند.
این‌ها مرز مهمی هستند: Static absence یا Snapshot فعلی به‌تنهایی رفتار کامل را
اثبات نمی‌کند.

## ریسک‌های معماری و عملیات

`R-037` فعال‌کردن زودهنگام Write مشتری/کالا با ۶۲ ورودی بدون Label قابل اتکا و
Goldenهای طراحی‌شده ولی اجرا‌نشده را High نگه می‌دارد. `R-038` نیز تخت‌کردن
تأمین‌کننده به Party CRUD و حذف Guardهای پرداخت/حسابداری/Contact/Cardex را منع
می‌کند؛ Slice اول هر سه Master فقط‌خواندنی است.

`R-039` یکی‌گرفتن سال عملیاتی/مالی و تخت‌کردن DC/دفتر فروش/انبار/نوع موجودی/
PriceMethod را منع می‌کند؛ Context پایه پیش از هر Write باید Owner-approved و
با کاردکس/دفترکل Reconcile شود.

`R-040` تخت‌کردن قیمت زمینه‌ای و تخفیف را منع می‌کند؛ Version، Effective window،
Priority، Scope relations، Condition/Arrange، Prize و Explain trace باید حفظ شوند.

`R-041` تاریخ قطعی را چهار Command مستقل و نسخه‌دار با Scope مرکز/سال مالی
می‌داند. پنج Route پیکربندی‌شده، سه Form runtime-unmatched، چهار Update لایه
Business/DataAccess و ۱۱ یافتهٔ SQL/IL داریم؛ Transaction parity مقصد و UAT
واقعی هنوز صفر است.

- Commandها باید Transaction owner واحد، Idempotency receipt و Outbox داشته باشند؛
- `R-007` شکست خود Rollback را نیز Unknown outcome می‌داند. Connector Replication
  خطای Execute/Commit را Throw می‌کند، اما Catch متد Rollback بدون Re-throw است؛
  مقصد باید Rollback failure را پایدار ثبت، Connection را قرنطینه و تا
  Reconciliation هیچ Success receipt صادر نکند؛
  همچنین Local/FTP cleanup پس از Receipt ولی پیش از Commit انجام می‌شود؛ Input
  immutable باید تا Commit حفظ و Delete/Ack فقط در state بعدی و قابل Retry باشد؛
  روی false فنی نیز Local پنج حذف فایل و FTP سه حذف فایل محلی پس از Rollback
  دارند، بدون Quarantine receipt اثبات‌شده؛ State machine قرنطینه باید Payload،
  علت، attempt و تصمیم Retry/Reject را پایدار کند؛
  Reset پس از Commit محلی نیز نتیجهٔ Boolean دارد که Caller نادیده می‌گیرد؛ هر
  Maintenance failure باید Outcome و Incident receipt مستقل و Retryable بسازد؛
- `R-006` علاوه بر Commandهای کسب‌وکار، Retry انتقال را هم پوشش می‌دهد. در Schema
  فعلی `ReplicationFile.FileName`، `ReplicationSend.CenterId` و بازهٔ
  `tblLogRcv(SiteRef,StartLog,EndLog)` قید یکتا ندارند. Trigger رسید عقب‌گرد را
  رد می‌کند، اما Watermark برابر را رد نمی‌کند، پیوستگی بازه را الزام نمی‌کند و
  از `inserted` مقدار Scalar می‌گیرد. مقصد باید Inbox/Outbox یکتای
  `center+package+version`، Validation مجموعه‌ای و تست Replay/Concurrent داشته باشد؛
  همچنین Timer سرویس بدون شاهد Single-flight صریح است؛ Tickهای هم‌زمان باید با
  lease دارای fencing یا guard درون‌پردازه‌ای coalesce شوند و اجرای طولانی‌تر از
  Interval در fault-injection آزموده شود؛ `Run` فقط `Timer.Enabled=true` دارد و
  disable صریح تنها در `Stop` دیده شد؛ Executor بسته نیز ثابت‌های Timeout
  صفر/۶۰۰/۳۰۰۰۰ و بدون Cancellation سراسری دارد، پس Deadline مثبت و محدود باید
  در Command envelope مقصد اجباری باشد؛ همچنین دو Trigger باینری Voucher خروجی
  `IDENT_CURRENT` از `InsertToLog` را در Mappingهای بدون Index/FK مصرف می‌کنند؛
  LogId باید با `OUTPUT inserted.ID`/`SCOPE_IDENTITY` و قید ارتباطی اتمیک شود؛
  Reader SQL و literal مستقیم در ۶۲ Assembly اصلی صفر است، پس اثر Downstream
  جاری ادعا نمی‌شود و مصرف Dynamic/External باید جدا Telemetry شود؛
- Business date، Effective date، Posting date و Import timestamp مستقل می‌مانند؛
- Stateful print یک Read ساده نیست؛ Preview/Export نباید Mutation داشته باشد؛
- Configuration precedence و نسخهٔ Setting باید همراه هر تصمیم قابل توضیح باشد؛
- Modular monolith برای جلوگیری از Shared-table writer و Distributed transaction
  زودرس حفظ می‌شود؛
- Performance و Restore با حجم نماینده و محیط ایزوله اثبات می‌شوند.
- `R-028` کپی `MAX(Id)+1` از LinearDiscount را منع می‌کند؛ Identity/Sequence/UUID،
  Unique constraint و تست parallel writer لازم است.
- `R-029` Import مبتنی بر `PSessionId` بدون Snapshot/hash و با FKهای not-trusted
  را منع می‌کند؛ Orphan و Payload conflict باید Quarantine شوند.
- `R-030` دوازده جدول خالی POS در Clone را شاهد «استفاده‌نشدن» یا حجم پایین
  نمی‌داند؛ برای Sizing/UAT شاهد Aggregate از منبع مجاز لازم است.
- `R-031` Method signal یا کاندید نامی یکتای SQL را Result parity تلقی نمی‌کند؛
  Exact binding، Snapshot، Golden value مالک، Scope و تطبیق Row/Total/Date لازم است.
- `R-032` کپی `RCheque/RCashDraft` به شکل CRUD table را منع می‌کند؛ دو View با
  Trigger `INSTEAD OF` به جداول حسابداری، Receipt/Log و Guardهای متعدد وصل‌اند.
- `R-033` نوشتن مستقیم Order/Sale/Return header/item از Web را منع می‌کند؛ گراف
  ۷۳ Trigger در سقف ۵۰۰ Node هنوز ۱۸۴ Frontier گسترش‌نیافته دارد و تا تکمیل
  disposition، Fault test و Reconciliation مانع فعال‌سازی Command است.
- `R-048` انتقال ردشده با Cleanup جزئی را High نگه می‌دارد؛ پاک‌سازی شماره فقط
  بعد از PASS و در همان تراکنش Server-owned انتقال مجاز است.
- `R-049` مجوزهای Issue/Confirm/Unconfirm/Delete/Transfer را پنج Action مستقل
  می‌داند؛ User id ارسالی Client Actor قابل اعتماد نیست و Deny-first scope، SoD،
  Audit تصمیم مجوز و آزمون Cross-DC/Cross-year/Cross-type الزامی است.
- `R-050` Finality خرید را Fail-closed بر completeness همهٔ StockDCهای applicable
  می‌کند و استثنای `OperationId=5` را به Policy نسخه‌دار و Golden case مصوب مالک
  تبدیل می‌کند؛ `MIN` روی زیرمجموعهٔ موجود کافی نیست.
- `R-051` اجازه نمی‌دهد ۶۵ Row تنظیمی به ۶۵ Capability فعال تبدیل شوند: فقط ۴۵
  نوع کاندید ساختاری‌اند؛ ۲۰ نوع بدون Article و ۱۳ مورد از آن‌ها بدون View باید
  با State صریح Dormant/Repair/Retire و تأیید مالک مدیریت شوند.
- `R-052` `NOLOCK` را از source مالی منع می‌کند؛ Provider مستقر Isolation صریح
  ندارد. Clone دارای RCSI/Snapshot است، ولی از ۵۴ جدول پایهٔ چهار Creator اخیر فقط
  شش جدول rowversion و صفر جدول Temporal/Change Tracking دارد. watermark/version
  منبع، snapshot committed، تطبیق پس از staging و تست concurrent rollback لازم‌اند.
- `R-053` Ruleهای حسابداری را DSL تایپ‌شده، versioned و immutable می‌کند؛ direct
  production edit، SQL fragment اجرایی و publish بدون جداسازی approver ممنوع است.
- `R-054` انتقال Template را به staging کامل، validate/compile همه Ruleها و یک
  atomic active-version swap تبدیل می‌کند؛ Failure هیچ نسخهٔ نیمه‌منتشرشده‌ای را
  برای صدور قابل مشاهده نمی‌کند و Triggerهای replication disposition صریح دارند.
- `R-055` اجازه نمی‌دهد Watermark سرویس Replication به‌عنوان Provenance انتشار
  پذیرفته شود. سرویس Hash-pinned دارای Binary outbox و Transaction دریافت است،
  ولی `tblLog/tblLogRcv` Rule version، Approval و Content hash ندارند. چهار تغییر
  Article اخیر ثبت شده، اما Clone هیچ Receipt/Outbox نگه نداشته است؛ مقصد باید
  نسخهٔ immutable مصوب، Manifest hash، Inbox idempotent و Reconciliation اثر مالی
  مستقل از `LastExecLog` داشته باشد. همچنین Hook تنظیمی پس از برگشت Receive خارج
  از Transaction فایل اجرا می‌شود؛ Wrapper موجود Log-sort و Dynamic identity
  maintenance را با مرزهای تراکنشی متفاوت ترکیب می‌کند. Mapping فعال و Authority
  سرویس اثبات نشده، بنابراین Receipt جدا و Retry/Reconciliation مرحلهٔ Maintenance
  نیز الزامی است. Footprint منبع ۱۱۴۲ Trigger فعال روی ۳۷۶ جدول در شش Schema را
  نشان می‌دهد؛ ۱۱۴۰ تعریف نشانهٔ Cursor، صفر `TRY/CATCH`، سه نشانهٔ
  `XACT_ABORT` و صفر `NOT FOR REPLICATION` دارند. پس Outbox مقصد باید
  write-amplification، multi-row/bulk، failure و replay این Side effect فراگیر را
  صریح پوشش دهد. توزیع آن Cross-domain است: `dbo=426/140`، `GNR=321/107`،
  `SLE=282/92`، `Acc=53/17`، `inv=45/15` و `ICA=15/5` Trigger/Table؛
  ۱۱۴۰ Trigger تک‌رویدادی Cursor-based و دو Trigger سه‌رویدادی بدون Cursor هستند.
  Golden caseهای مقصد باید multi-row/multi-event را پوشش دهند. این Aggregate وقوع
  Incident یا فعالیت اخیر همهٔ جدول‌ها نیست.
- `R-056` حمل Rule را به Secure authenticated transport و Package امضاشده محدود
  می‌کند. Payload بدون Signature، تغییرکرده، Replay، منقضی یا Wrong-center باید
  پیش از Unzip/Transaction/Execute قرنطینه شود و Receiver مقصد هرگز Arbitrary SQL
  را Capability مجاز نداند.

## سیاست خروج

هر Risk تنها زمانی بسته است که همه Exit criterionهای Artifact اجرا و Readback
شوند. Risk acceptance تصمیم جداگانهٔ کاربر/مالک کسب‌وکار است و این تحلیل آن را
اعطا نمی‌کند. ریسک‌های بحرانی مانع Gate مرحلهٔ متناظرند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260827.json`
- `scripts/windows/build_negin_erp_risk_register.py`
- `tests/test_varanegar_ui_evidence.py`
- `artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json`
- `scripts/sql/extract_varanegar_voucher_creation_atomicity_policy.py`
- `tests/test_varanegar_voucher_creation_atomicity_policy.py`
- `artifacts/varanegar_analysis/domains/rule_replication_transport_boundary_20260828.json`
- `scripts/sql/extract_varanegar_rule_replication_transport_boundary.py`
- `tests/test_varanegar_rule_replication_transport_boundary.py`

این Riskها در `REQUIREMENTS_TRACEABILITY_MATRIX_20260827_FA.md` به ماژول، P0 و
Golden caseها متصل شده‌اند.
