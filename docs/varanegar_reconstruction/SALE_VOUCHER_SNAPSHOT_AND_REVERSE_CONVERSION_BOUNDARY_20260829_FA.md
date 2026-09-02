# مرز Snapshot ووچر فروش و تبدیل معکوس

تاریخ شواهد: ۲۰۲۶-۰۸-۲۹

## جمع‌بندی

`tblSaleVocherHdr/Itm` سند حسابداری کل نیست؛ یک Snapshot نسخه‌بندی‌شده از فروش
و اقلام آن است که هنگام تبدیل سفارش به فروش ساخته می‌شود و مسیر مستقل «برگرداندن
فروش از ووچر» دارد. این Snapshot در فروش‌های لغوشده نیز عموماً حفظ می‌شود. در
نسخهٔ وب نباید آن را با وضعیت جاری Header یکی کرد یا هنگام لغو فروش به‌طور ضمنی
حذف کرد.

همهٔ بررسی‌ها فقط‌خواندنی و ایستا بوده‌اند. هیچ Procedure، فرم یا Command اجرا
نشده و هیچ Assembly بارگذاری/اجرا نشده است.

## Snapshot جاری

- فروش دارای شمارهٔ ووچر: ۲۶۶٬۱۸۳؛ فروش دارای Snapshot: ۲۶۶٬۱۸۳
- اختلاف «شماره بدون Snapshot»، «Snapshot بدون شماره»، شمارهٔ متفاوت، Snapshot
  تکراری و Snapshot/Item یتیم: صفر
- Headerهای Snapshot: ۲۶۶٬۱۸۳؛ Itemها: ۲٬۱۲۸٬۲۵۳
- فروش لغوشده‌ای که Snapshot تاریخی را نگه داشته است: ۶۰٬۶۹۸
- فقط ۳۲۴ فروش لغوشدهٔ وضعیت ۱ Snapshot ندارند؛ این همان Shape متفاوت مرحلهٔ
  لغو است و خرابی نام‌گذاری نمی‌شود.

۱۱٬۷۵۰ فروش فعال نهایی Amount جاری متفاوت از Amount Snapshot دارند؛ ۱٬۵۳۷ مورد
در پنجرهٔ سه‌ماهه‌اند. همه در Shape فعال `Status=1/CancelFlag=0` هستند و هیچ
اختلاف شماره یا فقدان Snapshot ندارند. این شاهد، Snapshot را به‌عنوان نسخهٔ یک
مرحله از جریان نشان می‌دهد؛ بدون تاریخچهٔ تغییر فیلد و Rule رسمی، این اختلاف‌ها
نه فساد داده و نه Amount صحیح/غلط نام‌گذاری می‌شوند.

## مرز ایجاد و برگشت SQL

`SLE.usp_FillSaleVocher` Header و هفت گروه Detail/Item وابسته را Insert می‌کند
ولی Transaction محلی ندارد. فراخوان اصلی آن `SLE.usp_sdsnet_CreateSaleByOrder`
است که Transaction، Savepoint، Try/Catch و Commit/Rollback دارد؛ بنابراین مالکیت
اتمی ایجاد Snapshot باید در Orchestrator حفظ شود.

`dbo.usp_sdsnet_ConvertSaleToVocher` مسیر معکوس مستقلی با Transaction محلی،
Try/Catch و Commit/Rollback است. این مسیر Sale و Snapshot را با Payment،
Sale detail/item، RetSale، شماره فروش و rollback تخفیف توزیع هماهنگ می‌کند؛ پس
یک تغییر سادهٔ Status نیست.

`SLE.usp_RollbackDisSaleSaleVocher` چهار بخش از graph تخفیف Snapshot را حذف و
نسخهٔ جاری آن‌ها را بازسازی می‌کند، ولی Transaction محلی ندارد. Procedure لغو
فروش Snapshot header را مستقیم حذف نمی‌کند. تنها capability حذف مستقیم Header
در Catalog منتخب متعلق به تأیید FreeInvoice است و وقوع تاریخی به آن منتسب نشد.

Trigger حذف replication-aware است و قابلیت bypass دارد؛ وقوع bypass ادعا نشده
است.

## مسیر Managed

سه Assembly، چهار Method و ۲۴۳ Instruction با Hash موجودی باینری تطبیق داده شد:

- UI به Business فراخوان می‌دهد و Context/Commit/RollBack صریح ندارد.
- Business یک DataContext می‌سازد، ابتدا Validation Adapter و بعد Conversion
  Adapter را صدا می‌زند، اما Commit/RollBack صریح ندارد.
- Conversion Adapter Context می‌سازد و Procedure نام‌دار را از مسیر Query اجرا
  می‌کند، ولی Commit/RollBack صریح ندارد.
- Transaction محلی SQL مالک قطعی Commit/Rollback است؛ enlistment فیزیکی Context
  مدیریت‌شده با آن از IL ثابت نمی‌شود.

## Audit و حدود تاریخی

Audit عمومی ۲۶۶٬۲۰۱ شناسهٔ Snapshot را دیده است. ۲۶۶٬۱۸۳ مورد هنوز موجود و ۱۸
شناسه غایب‌اند؛ Delete retained و غیبت سه‌ماهه هر دو صفر است. این ۱۸ مورد تاریخی
پیش از پوشش حذف فعلی‌اند و به Procedure، actor یا علت خاص منتسب نمی‌شوند.

## قرارداد پیشنهادی Negin ERP

1. `SaleSnapshot` یک Aggregate/نسخهٔ صریح و append-oriented باشد، نه mirror قابل
   ویرایش از `Sale`.
2. `IssueSaleFromOrder`، ایجاد Snapshot، Payment، Stock، Audit و Outbox یک
   UnitOfWork و CommandId مشترک داشته باشند.
3. `ReverseSaleVoucher` یک Command idempotent و version-checked با Eventهای
   جبرانی صریح برای شماره، Payment، تخفیف و ارتباط برگشت باشد.
4. لغو Sale، نگهداری/آرشیو Snapshot و تبدیل معکوس سه مفهوم مستقل باشند؛ حذف
   فیزیکی ضمنی ممنوع باشد.
5. Amount جاری و Amount Snapshot با `snapshotStage`, `capturedAt`, `sourceVersion`
   و Rule روشن نمایش داده شوند؛ اختلاف ۱۱٬۷۵۰ مورد به‌عنوان exception خام مهاجرت
   نشود.
6. مسیر FreeInvoice و replication bypass با مجوز، Tombstone و Audit غیرقابل‌تغییر
   محدود شوند.

## بازتولید و حدود ادعا

- `scripts/sql/extract_varanegar_sale_voucher_snapshot_boundary.py`
- `scripts/sql/extract_varanegar_sale_voucher_snapshot_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/sale_voucher_snapshot_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/sale_voucher_snapshot_runtime_boundary_20260829.json`
- `tests/test_varanegar_sale_voucher_snapshot_boundary.py`
- `scripts/windows/build_varanegar_sale_voucher_snapshot_checkpoint_20260829.py`

Definition، SQL literal خام، شناسه یا مقدار فروش/سفارش/مشتری/کاربر/میزبان و متن
خطا ذخیره نشده است. SQL و IL فقط capability و ترتیب ایستا را ثابت می‌کنند، نه
branch اجراشده، actor، موفقیت تاریخی یا Transaction فیزیکی مشترک.
