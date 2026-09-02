# مرز Template فاکتور Crystal و Audit چاپ فیزیکی

تاریخ شواهد: ۲۰۲۶-۰۸-۲۹

## جمع‌بندی

گزارش فاکتور در وارانگار Query معمول داخل DataAccess نیست. فرم نام Template را
از تنظیمات می‌گیرد، فایل Crystal Reports آن را Load می‌کند، پارامترها را تزریق
و اتصال دیتابیس جاری را روی Tableها و Subreportها اعمال می‌کند. پس SQL، Formula،
Layout و Parameter binding واقعی داخل فایل `.rpt` است، نه Assembly.

Preview/Print نیز فقط Read نیست: بعد از اعلام موفقیت چاپ توسط Engine، Business
برای هر Sale یک رخداد `GNR.tblPrintedDoc` می‌نویسد و Commit می‌کند. نسخهٔ وب باید
Query/Preview را از Command ثبت چاپ جدا نگه دارد.

هیچ Report، Template، Procedure، Form یا Print command اجرا نشد. Assemblyها فقط
با Metadata/IL خوانده شدند.

## مسیر Runtime اثبات‌شده

سه Assembly، نه Method و ۱٬۰۱۱ Instruction با Inventory باینری هم‌هش‌اند:

1. `FormReportFactor` فایل تنظیم‌شده را از `ReportFileEntity.FileName` می‌گیرد.
2. مسیر تک‌فاکتور و مجموعه، `frmPreviewPrint.ShowReportFact` را صدا می‌زند.
3. Engine فایل Crystal را Load و Parameterها را Set می‌کند.
4. `RefreshReport` اتصال جاری برنامه را روی Tableهای Report و Subreport اعمال و
   Location را بازنویسی می‌کند.
5. اگر نسخهٔ متناظر در `CustomReps` موجود باشد، مسیر `Report/Rep` می‌تواند Override
   شود.
6. فقط پس از `PrintedCompleted=true`، UI فرمان
   `SetLoginDrFactForVocherOrFactor` را اجرا می‌کند.
7. Business در یک DataContext برای هر سند یک رخداد `DocType=2` Save و در انتها
   Commit می‌کند. RollBack صریح در Method منتخب نیست؛ اتکا به Dispose نباید قرارداد
   مقصد باشد.

## شکاف Template

در `GNR.tblReportFile` شش Template نوع فاکتور وجود دارد: یک Default و شش نام فایل
یکتا. ۸۸ فایل `.rpt/.mrt` در سه ریشهٔ `Report`, `Rep`, `CustomReps` اسکن شد، ولی
هیچ‌یک از شش نام تنظیم‌شده در این ریشه‌ها نبود.

این نتیجه **اثبات خرابی Runtime نیست**؛ ممکن است Current directory، Cache یا
Distribution source دیگری وجود داشته باشد. نتیجهٔ قطعی این است که با شواهد فعلی
SQL/Formula/Layout و Result parity شش Template قابل استخراج نیست. بنابراین RPT-12
از L3 نام‌محور به implementation-ready ارتقا پیدا نمی‌کند.

## Audit چاپ

- کل رخداد چاپ: ۸۱۶٬۳۲۱
- کل کلید `(DocType,DocRef)`: ۱۹۷٬۵۸۶
- کلید دارای چاپ تکراری: ۵۵٬۷۹۲؛ بیشینه تکرار: ۸۸
- رخداد `DocType=2` فروش: ۳۰۸٬۴۳۲ روی ۱۴۴٬۸۴۷ Sale
- Sale دارای چاپ تکراری: ۳۴٬۸۴۰؛ بیشینه چاپ یک Sale: ۲۶
- ۶۸ شناسهٔ چاپ‌شدهٔ فروش دیگر Header جاری ندارند؛ attribution حذف ساخته نشد.

چاپ تکراری طبیعی است و Unique constraint روی Sale مناسب نیست. مقصد باید هر
Attempt را Event مستقل با `print_job_id`, template hash, actor, output hash و
outcome نگه دارد، ولی retry فنی همان Job نباید Event موفق مضاعف بسازد.

برای ۴۵ Sale که اکنون لغوشده‌اند، ۱۴۳ رخداد چاپ `DocType=2` پس از زمان آخرین
Detail پایانی دیده شد: ۵ رخداد تا پنج دقیقه، ۳۷ رخداد تا یک روز و ۱۰۱ رخداد بیش
از یک روز؛ فقط دو رخداد در پنجرهٔ سه‌ماهه‌اند. این ترتیب زمانی خرابی یا چاپ
غیرمجاز نام‌گذاری نمی‌شود—ممکن است نسخهٔ بایگانی/VOID باشد—اما خروجی مقصد باید
وضعیت لغو و watermark واضح داشته و Permission جدا برای reprint لغوشده بخواهد.

## دو شاخهٔ SQL Legacy

`dbo.USP_SDSNET_PrintedDoc_GetList` Dynamic SQL می‌سازد. در شاخهٔ KindPrint=0،
بازهٔ توزیع به‌جای `DistNo1..DistNo2` از `DistNo1..DistNo1` استفاده می‌کند؛ یعنی
upper bound ورودی نادیده گرفته می‌شود. این شاخهٔ sibling توزیع است و وقوع خطای
گزارش فاکتور RPT-12 از آن ادعا نمی‌شود.

`SLE.usp_SetPrintedDoc` نیز می‌تواند Audit چاپ درج کند، Transaction محلی ندارد و
در شاخهٔ KindPrint=0 مقادیر Scope قدیمی را hard-code کرده است. هیچ dependency
SQL و هیچ literal دقیق در باینری‌های مستقر برای آن پیدا نشد؛ بنابراین یک capability
دورمانده است، نه مسیر فعال یا رخداد منتسب‌شده.

## قرارداد پیشنهادی Negin ERP

1. `PreviewInvoice` Query خالص و `MarkInvoicePrinted` Command مستقل باشد.
2. Templateها immutable، versioned و دارای SHA-256، Rule/Schema version و مسیر
   انتشار امضاشده باشند؛ هر خروجی Template hash را ثبت کند.
3. Query/Formula/Parameter contract از فایل Template استخراج و در CI با Golden
   PDF/data snapshot تست شود.
4. Command چاپ فقط پس از Receipt قابل‌اعتماد spooler موفق شود؛ `PrintedCompleted`
   UI به‌تنهایی کافی نیست.
5. reprint، cancelled/VOID reprint و archive copy Permission و Watermark جدا
   داشته باشند.
6. یک PrintJob چندسندی یا کامل Commit شود یا هیچ Event موفقی نسازد؛ Rollback صریح
   و idempotency key لازم است.
7. شاخهٔ hard-coded دورمانده حذف/مسدود شود و range selection با تست چندتوزیعی
   اصلاح شود.

## بازتولید و حدود ادعا

- `scripts/sql/extract_varanegar_sale_invoice_print_audit_boundary.py`
- `scripts/sql/extract_varanegar_sale_invoice_print_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/sale_invoice_print_audit_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/sale_invoice_print_runtime_boundary_20260829.json`
- `tests/test_varanegar_sale_invoice_print_boundary.py`
- `scripts/windows/build_varanegar_sale_invoice_print_checkpoint_20260829.py`

نام خام Template، SQL/Formula Report، شناسه یا مقدار Sale/User/Host/Customer،
Connection string و نتیجهٔ گزارش ذخیره نشده است. ترتیب IL و زمان Audit، موفقیت
واقعی چاپ، محتوای خروجی، actor مجاز یا علت چاپ پس از لغو را ثابت نمی‌کند.
