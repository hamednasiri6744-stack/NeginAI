# مرز لغو فروش، پرداخت، موجودی و پیوند سفارش/خروج

تاریخ شواهد: ۲۰۲۶-۰۸-۲۹

## جمع‌بندی

لغو فروش در وارانگار یک تغییر ساده‌ی `CancelFlag` نیست. Procedure اصلی تراکنش محلی دارد و فروش، سفارش، پرداخت و جزئیات را تغییر می‌دهد؛ Triggerهای فعال نیز حذف پرداخت مستقیم، ثبت وضعیت پایانی و Projection موجودی را بر عهده دارند. در مقابل، خود Procedure وابستگی مستقیمی به خروج یا توزیع ندارد. به همین دلیل بخشی از فروش‌های لغوشده عمداً یا تاریخیاً پیوند فعال خروج/توزیع را نگه داشته‌اند و مقصد نباید آن را بدون Rule مستقل پاک کند.

هیچ رخداد عملیاتی اجرا نشده است. همه‌ی اعداد از Clone فقط‌خواندنی و همه‌ی مسیرهای برنامه از Metadata/IL ایستای Assemblyهای Hash-pinned به دست آمده‌اند.

## وضعیت جاری

- کل فروش لغوشده: ۶۱٬۰۲۲
- فروش لغوشده با Payment مستقیم باقی‌مانده: صفر
- فروش لغوشده با `ExitRef`: ۳۴٬۴۰۱
- فروش لغوشده با `DistRef`: ۳۴٬۴۰۱
- هر ۳۴٬۴۰۱ پیوند خروج به خروج فعال متصل است.
- فروش لغوشده‌ای که هنوز `SaleHdrRef` منتخب یک سفارش است: ۳۴٬۶۳۰
- از این تعداد، سفارش فعال: ۳۴٬۳۹۷

تفکیک Status نشان می‌دهد ۳۲۴ لغو در Status=1، تعداد ۲۶٬۲۹۷ در Status=2 و تعداد ۳۴٬۴۰۱ در Status=3 قرار دارند. تنها گروه Status=3 پیوند خروج/توزیع را نگه داشته است. این هم‌بستگی دقیق، Contract وضعیت را نشان می‌دهد اما به‌تنهایی معنی Status=3 یا علت هر رکورد را ثابت نمی‌کند.

## مالک اثر در SQL

`dbo.usp_sdsnet_Sale_Cancel`:

- `BEGIN TRANSACTION`، Try/Catch، Commit و Rollback دارد؛
- فروش، سفارش، پرداخت و Sale detail را مستقیماً در dependency graph دارد؛
- پنج Delete، سه Update و دو Insert در متن اجرایی آن دیده می‌شود؛
- به `tblExit` یا جدول توزیع dependency مستقیم ندارد؛
- Dynamic SQL capability در این Procedure دیده نشد.

Triggerهای فعال روی SaleHdr:

- `SLE.trg_tblSaleHdr_CancelFlag_DeletePayment98` پرداخت‌های مستقیم متصل به Sale را حذف می‌کند؛ Snapshot صفر Payment باقی‌مانده با این Rule سازگار است.
- `SLE.trg_tblSaleHdr_FillDetail` تغییر Header را به `tblSaleHdrDetail` می‌برد.
- `SLE.Trg_tblSaleHdr_UpdateStockGoods` Projection موجودی را تغییر می‌دهد و خود دارای Rollback signal است.
- `SLE.trg_tblSaleHdr_Ebtal` به تغییر لغو واکنش نشان می‌دهد و وضعیت‌های مرتبط سفارش/فروش را Update می‌کند.

بنابراین تراکنش محلی Procedure همراه با Triggerها، مالک SQL اثبات‌شده است. موفق بودن Snapshot امروز، تضمین نمی‌کند که یک بازنویسی ساده‌ی Flag همان مرز را حفظ کند.

## مسیر Managed

سه Assembly و چهار Method، جمعاً ۳۹۰ Instruction، بدون Load/Execute بررسی شد:

- `FormSaleList.CancelCommand` ابتدا فرم دلیل لغو را می‌سازد و سپس `SaleHandler.CancelSale` را فراخوانی می‌کند؛ Context/Commit/RollBack صریح ندارد.
- `CheckCancelPermission` Method جداگانه‌ای در همان فرم است، اما از IL محدود انتخاب‌شده نمی‌توان ترتیب قطعی اجرای Permission و OperationDate را در همه‌ی branchها اثبات کرد.
- `SaleHandler.CancelSale` یک delegate باریک به Adapter است و Context صریح ندارد.
- `SaleAdapter.CancelSale` Context می‌سازد و Procedure نام‌دار را Execute می‌کند، ولی Commit یا RollBack صریح در Method منتخب دیده نشد؛ Exception region دارد.

نبود Commit در Adapter به معنی نبود Commit عملیاتی نیست، زیرا Procedure خودش تراکنش را Commit می‌کند. با این حال enlistment فیزیکی Context مدیریت‌شده و تراکنش محلی SQL از IL ایستا ثابت نشده است.

## Projection پایانی

از ۶۱٬۰۲۲ لغو:

- ۲۶٬۶۱۲ مورد آخرین Detail با Status=0 دارند؛
- ۳۴٬۴۰۷ مورد آخرین Detail با Status=3 دارند؛
- سه مورد Status خارج از 0/3 دارند و تاریخی‌اند؛
- در بازه‌ی اخیر هیچ terminal exception دیده نشد.

پس مقایسه‌ی عددی Header.Status و Detail.Status Rule صحیحی برای تشخیص خرابی نیست. نگاشت semantic و نسخه‌دار لازم است.

## قرارداد پیشنهادی برای Negin ERP

1. `CancelSale` یک Command idempotent با `ExpectedVersion`، `CommandId` و یک Transaction Owner باشد.
2. Sale event، پرداخت، وضعیت/انتخاب سفارش، موجودی، حسابداری، دلیل لغو، Audit و Outbox در مرز اتمیک تعریف شوند.
3. پیوند خروج و توزیع Rule مستقل داشته باشد: Retain، Cancel یا Compensate؛ حذف ضمنی مجاز نباشد.
4. دلیل لغو، actor، OperationDate و وضعیت قبل/بعد تغییرناپذیر ثبت شود.
5. Retry نباید پرداخت، برگشت موجودی یا سند حسابداری را دوباره اعمال کند.
6. وضعیت پایانی با Event و نگاشت semantic مدل شود، نه صرفاً Flag یا برابری Statusها.
7. سه استثنای تاریخی quarantine شوند و ۳۴٬۴۰۱ پیوند خروج/توزیع بدون نسبت‌دادن علت مهاجرت کنند.

## بازتولید و حدود ادعا

- `scripts/sql/extract_varanegar_sale_cancellation_boundary.py`
- `scripts/sql/extract_varanegar_sale_cancellation_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/sale_cancellation_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/sale_cancellation_runtime_boundary_20260829.json`
- `tests/test_varanegar_sale_cancellation_boundary.py`
- `scripts/windows/build_varanegar_sale_cancellation_checkpoint_20260829.py`

تعریف SQL خام، Literalهای برنامه، شناسه‌ی فروش/سفارش/مشتری/کاربر/میزبان و متن خطا ذخیره نشده است. Dependency و ترتیب IL توان ایستا را ثابت می‌کند، نه branch اجراشده، actor، علت یا موفقیت تاریخی هر لغو.
