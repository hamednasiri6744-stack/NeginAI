# مرز صدور و لغو برگشت از فروش، سند ورود و اعتبار

تاریخ شواهد: ۲۰۲۶-۰۸-۲۹

## جمع‌بندی

برگشت از فروش رسمی در وارانگار یک Aggregate چنددامنه‌ای است: Header/Item برگشت، سند ورود انبار نوع ۱۰، Payment/اعتبار برگشت و پیوندهای فاکتور/توزیع. Snapshot جاری کاملاً منسجم است، اما کد Legacy مالکیت چندلایه و کنترل‌های پس از Write دارد. نسخه‌ی وب نباید این زنجیره را به یک Flag یا چند فراخوانی مستقل تبدیل کند.

همه‌ی بررسی‌ها فقط‌خواندنی بوده‌اند. هیچ Procedure، فرم یا Command اجرا نشده و Assemblyها Load/Execute نشده‌اند.

## Snapshot جاری

- برگشت فعال: ۱۳٬۹۱۳
- برگشت لغوشده: ۱۷۸
- برگشت فعال با دقیقاً یک Voucher نوع ۱۰: ۱۳٬۹۱۳
- Voucher نوع ۱۰ جاری: ۱۳٬۹۱۳؛ همه به برگشت فعال وصل و همه تأییدشده‌اند.
- برگشت فعال با Voucher چندگانه یا تأییدنشده: صفر
- برگشت لغوشده با Voucher نوع ۱۰: صفر
- برگشت لغوشده با Payment: صفر
- لغو با تاریخ تجاری سه‌ماهه: دو

هر ۱۷۸ Header لغوشده هنوز `VocherFlag=1` دارد، با اینکه Voucher جاری ندارد. بنابراین `VocherFlag` نشان «تاریخچه‌ی صدور/مرحله» است و نباید به‌عنوان FK وجود سند یا Projection جاری تفسیر شود.

برگشت‌های فعال شامل ۱۳٬۲۲۳ Header دارای Payment و ۱۴٬۵۸۶ Payment هستند. برای ۱۷۸ لغو، Payment و Voucher هر دو پاک شده‌اند؛ این پاکیزگی جاری با Rule کد سازگار است ولی Procedure تاریخی هر لغو را قطعی نمی‌کند.

## مرز SQL صدور

`dbo.usp_Sdsnet_RetSale_Save` یک Orchestrator تراکنشی با Savepoint، Try/Catch، Commit و Rollback است. هم مسیر صدور Voucher، هم تولید Voucher لغو و هم لغو Header را در dependency graph دارد و می‌تواند Payment و Voucher graph را Delete کند.

`dbo.USP_SDSNET_GenerateRetSaleVocher` نیز Transaction/Savepoint مستقل دارد:

- Header/Item/Detail سند نوع ۱۰ را Insert می‌کند؛
- `VocherFlag` را Update می‌کند؛
- در صورت وجود Settlement Sale، `USP_CreatePaymentFromRetSale` را صدا می‌زند؛
- بخشی از کنترل‌های بسته‌بندی/Batch/وجود قلم و پیام خطا پس از Insertهای Voucher قرار دارد؛
- Try/Catch و Rollback دارد، اما این ترتیب باید در مقصد به precondition-before-write تبدیل شود.

`SLE.usp_AfterSaveRetSale` تراکنش/Savepoint محلی ندارد اما Rollback signal و اثرهای کنترل/Projection متعدد دارد؛ پس اجرای آن بدون Owner محیطی یک قرارداد مستقل و امن تلقی نمی‌شود.

## مرز SQL لغو

`dbo.USP_SDSNET_GenerateCancelRetSaleVocher` تراکنش محلی، Try/Catch، Commit/Rollback دارد. هم Delete و هم Insert روی Voucher graph انجام می‌دهد و کنترل موجودی را فراخوانی می‌کند. این رفتار صرفاً «حذف سند ورود» نیست؛ مسیر جبرانی/بازسازی Voucher دارد.

`SLE.USP_SDSNET_CancelRetSaleHdr` تراکنش محلی ندارد، `CancelFlag` را Update و رابطه‌ی `tblPayWithPaymentRelation` را حذف می‌کند. Orchestrator Save و Adapter مدیریت‌شده این مسیر را با Cancel Voucher و پاک‌سازی Payment هماهنگ می‌کنند.

سه Module در کل Catalog قابلیت Delete مستقیم `tblRetSaleHdr` دارند. Audit عمومی ۱۴٬۰۹۱ شناسه‌ی Header را کامل پوشش می‌دهد و Delete/Absent جاری یا اخیر صفر است؛ بنابراین هیچ حذف فیزیکی رخ‌داده یا attribution به این سه Module ادعا نمی‌شود.

## مسیر Managed

سه Assembly، پنج Method و ۴۰۴ Instruction به‌صورت PE metadata/IL ایستا بررسی شد:

- `FormRetSaleList.CancelCommand` مستقیماً Business cancel را صدا می‌زند و Context/Commit/RollBack صریح ندارد.
- دو Method در `RetSaleHandler` delegate باریک به Adapter هستند.
- `RetSaleAdapter.GenerateRetSaleVocher` Procedure نام‌دار را Query می‌کند، اما Context constructor، Commit یا RollBack صریح در Method منتخب ندارد.
- `RetSaleAdapter.CancelRetSaleAndGenerateCancelRetSaleVocher` Context می‌سازد، Cancel Voucher و Cancel Header نام‌دار را Query/Execute می‌کند و Commit صریح دارد؛ RollBack صریح ندارد.
- هر دو Method Adapter Exception region دارند.

اشتراک Connection/Transaction بین Managed context و تراکنش‌های محلی SQL از IL ثابت نمی‌شود. Commit Adapter در مسیر لغو نیز به‌تنهایی اثبات نمی‌کند که تمام اثرها یک Transaction فیزیکی دارند.

## قرارداد پیشنهادی Negin ERP

1. `IssueSalesReturn` و `CancelSalesReturn` دو Command جدا، idempotent و version-checked باشند.
2. Return، Voucher type 10، Stock projection، Credit/Payment، Accounting، Audit و Outbox یک UnitOfWork داشته باشند.
3. همه‌ی کنترل‌های کالا، بسته‌بندی، Batch، سقف مقدار برگشت و Amount پیش از اولین Write اجرا شوند؛ Postcondition نیز شکست typed و rollback کامل بدهد.
4. `VocherFlag` با state machine جایگزین شود: Draft → Issued → Cancelled؛ وجود Projection از FK/Projection خوانده شود.
5. لغو، Event جبرانی صریح برای ورود انبار و اعتبار داشته باشد؛ Delete فیزیکی تنها Cleanup داخلی تراکنش باشد، نه Audit.
6. Retry صدور یا لغو نباید Voucher، Payment، Stock یا Accounting را دوباره اعمال کند.
7. سه capability حذف مستقیم فقط با Tombstone، مجوز بازیابی و Audit غیرقابل‌تغییر پوشش داده شوند.

## بازتولید و حدود ادعا

- `scripts/sql/extract_varanegar_return_issue_cancel_boundary.py`
- `scripts/sql/extract_varanegar_return_issue_cancel_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/return_issue_cancel_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/return_issue_cancel_runtime_boundary_20260829.json`
- `tests/test_varanegar_return_issue_cancel_boundary.py`
- `scripts/windows/build_varanegar_return_issue_cancel_checkpoint_20260829.py`

Definition و Literal خام، شناسه‌ی برگشت/فروش/Voucher/Payment/مشتری، نام کاربر/میزبان و متن خطا ذخیره نشده است. ترتیب متن SQL و IL capability و ترتیب ایستا را نشان می‌دهد، نه branch واقعی، actor یا موفقیت تاریخی.
