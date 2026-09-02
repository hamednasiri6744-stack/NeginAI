# مرز تراکنش، وضعیت و حذف در تبدیل سفارش به فروش

تاریخ شواهد: ۲۰۲۶-۰۸-۲۹

## جمع‌بندی

تبدیل سفارش به فروش در وارانگار یک Insert ساده نیست. Procedure اصلی علاوه بر Header/Item فروش، Pointer سفارش، زمان اجرای تبدیل، پرداخت، Batch، جایزه‌ی رزروشده، جزئیات آیتم و اثرهای Triggerی موجودی/تاریخچه را درگیر می‌کند. Orchestrator تراکنش محلی دارد، اما پارامتر `WithOutRollback` رفتار rollback را شاخه‌ای می‌کند. مسیر Managed نیز هم در Business و هم در Adapter سیگنال Commit دارد و اشتراک تراکنش فیزیکی Contextهای تو‌در‌تو از IL ایستا ثابت نمی‌شود.

Snapshot فعلی از نظر invariant اصلی سالم است: هیچ سفارش بیش از یک Sale فعال ندارد و Pointer غیرتهیِ یتیم یا reverse mismatch صفر است. با این حال Attempt timing کامل نیست، چند استثنای تاریخی Projection وجود دارد و حذف فیزیکی Sale رخ داده است. این‌ها باید در مهاجرت صریح و بدون نسبت‌دادن علتِ اثبات‌نشده نگه داشته شوند.

## جمعیت و وضعیت جاری

- Sale: ۲۷۵٬۹۹۵
- فعال: ۲۱۴٬۹۷۳
- لغوشده: ۶۱٬۰۲۲
- شماره‌دار: ۲۱۳٬۰۸۳
- بدون SaleNo: ۶۲٬۹۱۲؛ این گروه state معتبر حواله/فروش موقت است، نه خطای شماره‌گذاری.
- SaleDate سه‌ماهه‌ی ۱۴۰۵/۰۳/۰۱ تا ۱۴۰۵/۰۵/۳۱: ۴۰٬۰۵۹
- لغوشده در همین بازه: ۷٬۷۰۲

ترکیب وضعیت دقیقاً پنج Shape دارد: فاکتور فعال Status=1، فاکتور شماره‌دار لغوشده Status=1، حواله فعال Status=2، حواله لغوشده Status=2 و مرحله/مرجوع لغوشده Status=3.

## رابطه‌ی Order و Sale

- ۲۵۴٬۱۶۴ سفارش حداقل یک Sale attempt دارند.
- ۱۸٬۰۰۹ سفارش چند attempt دارند.
- سفارش با بیش از یک Sale فعال: صفر.
- ۴٬۵۶۱ سفارشِ دارای Sale، Pointer منتخب Null دارند؛ این State تاریخی است و Pointer dangling نیست.
- Pointer غیرتهی به Sale غایب: صفر.
- Reverse mismatch بین `OrderHdr.SaleHdrRef` و `SaleHdr.OrderRef`: صفر.
- Pointer منتخب به Sale لغوشده: ۳۴٬۶۳۰.

پس مقصد باید `ConversionAttempt` و `SelectedSaleVersion` را جدا کند؛ Unique کردن ساده‌ی OrderId روی همه‌ی Saleها تاریخچه را خراب می‌کند.

## ساختار SQL تبدیل

`SLE.usp_sdsnet_CreateSaleByOrder`:

- `BEGIN TRANSACTION`، Try/Catch، Commit و Rollback دارد؛
- پارامتر و شاخه‌ی `WithOutRollback` دارد؛
- ابتدا Core بدون تراکنش `SLE.usp_CreateSaleByOrder` را صدا می‌زند و بعد Pointer فروش منتخب سفارش را Update می‌کند؛
- زمان تبدیل و Stateهای Payment، Batch، ReservedPrize و SaleItemDetail را نیز تغییر می‌دهد؛
- Dynamic SQL capability دارد.

Core، Header و Item فروش را می‌سازد اما تراکنش یا Savepoint محلی ندارد. بنابراین فراخوانی مستقیم Core با فراخوانی Orchestrator یک Contract یکسان نیست.

## Triggerهای صاحب اثر

- `trg_tblSaleHdr_FillDetail`: تغییر Header را به `tblSaleHdrDetail` Projection/Event می‌برد.
- `trg_tblSaleHdr_CancelFlag_DeletePayment98`: تغییر CancelFlag می‌تواند Payment را حذف کند.
- `Trg_tblSaleHdr_UpdateStockGoods`: از تغییر Header به StockGoods اثر می‌دهد.
- Trigger حذف replication فعال است و replication-mode bypass دارد.

در مقصد، این اثرها باید تحت Command و Transaction Owner صریح باشند؛ Trigger پنهان نباید مرز صحت API باشد.

## وضعیت Header در برابر Detail

۵۴۰٬۸۸۸ Detail برای تمام ۲۷۵٬۹۹۵ Sale وجود دارد و Detail یتیم صفر است.

مقایسه‌ی خام آخرین Detail با Header تعداد ۲۶٬۶۲۴ اختلاف می‌دهد، اما این عدد «خرابی» نیست:

- ۲۶٬۶۱۸ مورد شکل طبیعی لغو است: Detail پایانی Status=0، در حالی که Header وضعیت تجاری پیشین را حفظ می‌کند.
- شش Sale فعال، Header Status=1 و آخرین Detail Status=3 دارند؛ آخرین مورد مربوط به ۲۰۲۵ است.
- سه Sale لغوشده، Detail پایانی خارج از مجموعه‌ی مورد انتظار 0/3 دارند؛ همگی مربوط به ۲۰۲۴ هستند.
- استثنای Projection در بازه‌ی سه‌ماهه: صفر.
- فقط سه زنجیره با Initial Status خارج از 1/2 دیده شد.

در ERP جدید باید تابع نگاشت terminal state نسخه‌دار باشد؛ مقایسه‌ی عددی ساده‌ی Header.Status با Detail.Status، ۲۶٬۶۱۸ false positive می‌سازد.

## Runtime Managed

سه Assembly با Hash inventory و فقط از طریق PE metadata/IL بررسی شدند؛ Load/Execute نشدند.

- `FormSaleDataEntry.SaveCommand` دو branch فراخوانی Business دارد و Context/Commit/Rollback صریح ندارد.
- `SaleHandler.OrderToSaleSaveCommand` Context می‌سازد، `CreateSaleByOrder` را صدا می‌زند و بعد Commit می‌کند؛ RollBack صریح در Method منتخب دیده نشد.
- `OrderHandler.CreateSaleByOrder` دو overload دارد: یکی delegate باریک به Adapter و دیگری Context تازه ساخته و Core قدیمی را با Query صدا می‌زند، بدون Commit محلی.
- `OrderAdapter.CreateSaleByOrder` Context تازه می‌سازد، Orchestrator نام‌دار را Execute و سپس Commit می‌کند.
- در مجموع پنج Method و ۱٬۰۵۵ Instruction انتخاب شد.

بررسی اولیه صرف وجود Commit در Business و Adapter را دلیل اشتراک
Connection/Transaction نمی‌دانست. بررسی بعدی خود `Application.DataAccess.dll`
این ابهام را برای مسیر منتخب بست: Context پیش‌فرض حالت بدون تراکنش و Connection
مستقل دارد؛ Adapter تبدیل `Transaction.Begin` می‌سازد، ولی مرحلهٔ EVC در Discount
V2 با Context حالت No و Connection جدا اجرا می‌شود. Metadata token نیز نشان داد
V2 در مرحلهٔ تبدیل به overload Adapter می‌رود. جزئیات در سند
`DATACONTEXT_TRANSACTION_OWNERSHIP_AND_ORDER_SALE_SPLIT_20260829_FA.md` است؛ مقدار
واقعی `WithOutRollback` هر اجرای تاریخی همچنان ثابت نشده است.

## Attempt timing

- ۲۷۵٬۹۹۵ Sale attempt در برابر ۲۶۶٬۲۰۲ timing row.
- ۲۴۴٬۳۵۳ سفارش تعداد Sale و Timing برابر دارند.
- ۹٬۸۰۹ سفارش Sale دارد ولی Timing ندارد.
- ۹ سفارش Timing دارد ولی Sale ندارد.
- ۹٬۸۱۱ سفارش Sale attempt بیشتر و ۹ سفارش Timing بیشتر از Sale دارند.

پس `tblOrderToSaleTime` ابزار سنجش عملیات است، نه ledger کامل idempotency یا نتیجه‌ی Command.

## حذف فیزیکی و Audit

- لاگ عمومی ۲۷۶٬۶۵۳ شناسه‌ی Sale را پوشش می‌دهد؛ ۲۷۵٬۹۹۵ هنوز موجود و ۶۵۸ غایب‌اند.
- ۶۴۰ Delete retained وجود دارد و هر ۶۴۰ شناسه اکنون غایب است.
- ۱۱۲ Delete در بازه‌ی سه‌ماهه ثبت شده است.
- ۱۸ شناسه‌ی غایب Delete retained ندارند؛ هیچ‌کدام سه‌ماهه نیست.
- تنها ماژول Catalogued با Delete مستقیم `tblSaleHdr`، `SLE.usp_sdsnet_ConfirmFreeInvoice` است و Transaction/Savepoint دارد.

این تطبیق capability و شمارش زمانی، attribution قطعی ۶۴۰ حذف به Procedure نیست. Actor/reason نیز از شاهد Aggregate معلوم نیست.

## قرارداد پیشنهادی Negin ERP

1. `ConvertOrderToSale` یک Command idempotent با ExpectedVersion و یک UnitOfWork باشد.
2. `WithOutRollback` ورودی عمومی نباشد؛ recovery/partial mode اگر لازم است Command مجزا، fenced و audited باشد.
3. Sale، Item، Pointer سفارش، Attempt، Payment، Batch، ReservedPrize، Stock projection، StateEvent، Accounting و Outbox یک Transaction Owner داشته باشند.
4. Retry همان Command باید همان Attempt قبلی را برگرداند و بیش از یک Sale فعال نسازد.
5. وضعیت لغو با Event صریح مدل شود؛ Header status و terminal detail با نگاشت semantic مقایسه شوند.
6. Timing جایگزین Attempt ledger نشود؛ ۹٬۸۰۹/۹ شکاف تاریخی quarantine شوند.
7. حذف فیزیکی فقط Command recovery ویژه با Tombstone تغییرناپذیر، actor، reason و authorization مستقل باشد.

## بازتولید و حدود ادعا

- `scripts/sql/extract_varanegar_sale_conversion_state_boundary.py`
- `scripts/sql/extract_varanegar_sale_conversion_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/sale_conversion_state_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/sale_conversion_runtime_boundary_20260829.json`
- `tests/test_varanegar_sale_conversion_state_boundary.py`
- `scripts/windows/build_varanegar_sale_conversion_checkpoint_20260829.py`

هیچ Procedure، Trigger، فرم یا Command اجرا نشد. Queryها تجمیعی و فقط‌خواندنی‌اند؛ هیچ شناسه‌ی سفارش/فروش/مشتری/کالا، کاربر/میزبان، متن خطا یا SQL definition خام در Artifact ذخیره نشده است. ترتیب متن SQL و IL توان و ترتیب ایستا را نشان می‌دهد، نه branch اجراشده یا موفقیت runtime.
