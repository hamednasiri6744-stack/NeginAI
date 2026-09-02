# مرز علّی Delete Log برای Targetهای مفقود NGT — ۲۰۲۶-۰۸-۲۹

## نتیجهٔ قطعی جدید

هر ۱٬۰۲۴ جفت Target مفقود Type=1 دقیقاً یک رکورد `DELETE` در `GNR.tblLog` با
همان `OperationId` دارد. این ۱٬۰۲۴ حذف تمام ۵٬۵۳۳ History خط و تمام جمعیت
Target مفقود را پوشش می‌دهد؛ تعداد Target بدون Delete log صفر است.

ترتیب زمانی نیز یک‌دست است: هر ۱٬۰۲۴ حذف بعد از آخرین `TourHistory.CreatedDate`
همان Target رخ داده است. بنابراین Target ابتدا در Replication ساخته و ثبت شده و
بعداً حذف شده است. این نتیجه جای فرض قبلی «ممکن است حذف شده باشد» را می‌گیرد.

## فاصلهٔ History تا حذف

| فاصله از آخرین History | Target |
|---|---:|
| همان روز | ۲۹۸ |
| ۱ تا ۷ روز | ۵۳۴ |
| ۸ تا ۳۰ روز | ۱۹۲ |
| بیش از ۳۰ روز | ۰ |
| حذف قبل از اولین History | ۰ |

کمترین فاصله صفر دقیقه و بیشترین ۳۵٬۷۸۳ دقیقه، حدود ۲۵ روز است. ۱۱۵ Target
مفقود در June–August 2026 حذف شده‌اند. این ۱۱۵ Target به ۱۱۴ والد سه‌ماهه مربوط
می‌شوند، چون یک والد می‌تواند بیش از یک Target داشته باشد.

## دامنهٔ لاگ موجود

در کل ۱٬۹۰۷ Delete log یکتای Header سفارش از ۲۰۲۴-۰۴-۰۱ تا ۲۰۲۶-۰۸-۲۲ باقی
مانده است. همه Script canonical و همه OperationIdها متمایزند؛ هیچ‌یک از این
۱٬۹۰۷ ID اکنون در جدول سفارش موجود نیست. ۱٬۰۲۴ مورد همان Targetهای Type=1 مفقود
و ۸۸۳ مورد حذف‌های دیگری هستند.

Trigger حذف:

- ID را از pseudo-table `deleted` می‌خواند؛
- `OperationType=DELETE` و `OperationTable=SLE.tblorderhdr` می‌گذارد؛
- `OperationId` را از Record ID می‌سازد؛
- Script canonical و `InsertToLog` را تولید می‌کند.

خود لاگ OperationType/Table/Id/TransDate و metadata برنامه، کاربر، میزبان و
Session دارد و روی Table+OperationId Index دارد. هیچ نام یا مقدار هویتی ذخیره
نشد؛ فقط cardinality و concentration ثبت شد: ۲۳ App، یک DB user، ۲۵ Host، ۴۶۶
Session و ۳۹ جفت App/Host. بزرگ‌ترین App به‌تنهایی ۵۶۷ حذف و بزرگ‌ترین App/Host
pair تعداد ۲۶۲ حذف دارد؛ پس یک مسیر اجرایی واحد از این شاهد قابل ادعا نیست.

## اثر انگشت مسیر حذف

در پنجرهٔ همان Session، هر ۱٬۰۲۴ Target این tail را دارد:

```text
SLE.tblOrderItm DELETE → dbo.visit_BOOrder DELETE → SLE.tblOrderHdr DELETE
```

برای ۱٬۰۰۸ Target، Visit delete دقیقاً Log قبلی Header است؛ برای ۱۶ Target نیز
نزدیک‌ترین رویداد قبلی همان Session است. Item-before-Visit تعداد ۱٬۰۲۴ و
Visit-before-Item صفر است. SaleHeader DELETE در پنجرهٔ ۳۰ ثانیه/۱۰۰۰ Log قبلی
صفر است.

مقایسه با چهار Procedure حذف مستقیم:

- `NGT_RollBackTour`: Visit → Item → Header → History؛ با tail ثبت‌شدهٔ موفق
  سازگار نیست.
- `USP_sdsnet_UndoUserExtraInfo`: Item → Header و Visit ندارد؛ سازگار نیست.
- `usp_sdsnet_Order_Delete`: Item → Visit → Header؛ تطبیق کامل tail.
- `usp_sdsnet_ConfirmFreeInvoice`: Sale → Item → Visit → Header؛ tail مشترک دارد،
  اما هیچ Sale DELETE متناظری دیده نشد.

پس `usp_sdsnet_Order_Delete` قوی‌ترین نامزد است، نه attribution قطعی. اجرای شاخه‌ای
با SaleRef خالی یا پوشش ناقص Log همچنان باید با Runtime trace ایزوله رد یا تأیید
شود. از ۱٬۰۲۴ Target، تعداد ۵۲۴ متعلق به ۵۲۲ والد با `IsFreeInvoice=1`، هفت
Target با Flag صفر و ۴۹۳ Target با Flag تهی‌اند؛ Flag به‌تنهایی Procedure را
تعیین نمی‌کند.

## چیزی که هنوز معلوم نیست

Delete log اثبات می‌کند Target حذف شده و زمان/شناسهٔ Target را دارد، اما NGT
Entity، علت تجاری، Procedure فراخوان، approval و disposition را ثبت نمی‌کند.
دو Procedure نگهداری Replication بررسی‌شده، main log را حذف نمی‌کنند؛ بااین‌حال
کامل بودن تاریخ قبل از اولین رکورد باقی‌مانده ثابت نشده است.

در نتیجه `R-069` و `R-070` دقیق‌تر شدند: حذف Target قطعی است، ولی attribution
مسیر و مجاز بودن recreate همچنان باز است. شمار رجیستر تغییر نکرد: ۷۰ ریسک، ۴۰
بحرانی، ۲۷ بالا، ۲۷۵ اتصال و صفر Command-ready.

## Artifactها

- `scripts/sql/extract_varanegar_ngt_order_delete_log_boundary.py`
- `artifacts/varanegar_analysis/domains/ngt_order_delete_log_boundary_20260829.json`
- `tests/test_varanegar_ngt_order_delete_log_boundary.py`
- `scripts/windows/build_varanegar_ngt_order_delete_log_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/varanegar_ngt_order_delete_log_checkpoint_20260829.json`

## حدود شاهد

- هیچ Trigger، Procedure، Endpoint یا Script تولیدی اجرا نشد؛
- هیچ OperationId، GUID، نام App/User/Host، SPID یا ردیف خام ذخیره نشد؛
- تطبیق شناسه و ترتیب زمانی حذف را ثابت می‌کند، نه Procedure یا علت تصمیم حذف؛
- Delete log عمومی جای Tombstone دامنه‌ای و Workflow تعیین‌تکلیف NGT را نمی‌گیرد.
