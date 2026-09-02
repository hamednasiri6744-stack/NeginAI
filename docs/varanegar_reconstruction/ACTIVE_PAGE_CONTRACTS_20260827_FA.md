# قرارداد فیلد، فیلتر و Validation چهار صفحه فعال

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۲۱ Type، ۴۵ ستون Grid، ۱۰۵ Field candidate، ۶۱ Validation method و ۱۲ SQL contract**

## روش و مرز اطمینان

این سند از IL هدفمند Redacted، ماتریس Capability/Permission و قراردادهای SQL
Clone فقط‌خواندنی ساخته شده است. هیچ مقدار داخل Grid، نام مشتری/کاربر، شماره چک
یا دادهٔ عملیاتی خوانده نشده و هیچ Command اجرا نشده است.

- ستون‌های دو Grid چک از `AddColumns` اطمینان بالا دارند؛
- Fieldهای موجودی/توزیع از Property call و `InitializeComponent` اطمینان متوسط
  تا بالا دارند، اما الزاماً همه در Session جاری Visible/Edit-enabled نیستند؛
- وجود Validator/Handler قطعی است، ولی معنی تمام Branchها بدون تحلیل Control
  flow اختصاصی نباید حدس زده شود؛
- شماره Statusها باید تا ساخت Status dictionary رسمی به‌عنوان Source code حفظ
  شوند، نه معنی‌گذاری آزاد.

## ۱. پیگیری چک دریافتی

### Work queue و Scope

صفحه فعال Variant قدیمی است و Inbox اولیه را با
`RChequeStatusId in (1,2,4,8,9)` می‌سازد؛ سپس ReceiptStatus، DC و SaleOffice
قابل‌دسترسی کاربر را اعمال و نتیجه را نزولی بر `RChequeId` مرتب می‌کند.

### ستون‌های قراردادی Grid

گروه‌های اصلی ۲۹ ستون یکتا:

- شناسه/نسخه: `RChequeId`, `RChequeHistoryId`, `ModifiedDate`, `ReceiptId`؛
- ابزار: `RChequeNo`, `RChequeDate`, `RChequeAmount`, `ChequeTypeId`؛
- بانک: `BankId`, `BankAccountId`, `RChequeBranchCode`, `RChequeBranchName`؛
- وضعیت: `RChequeStatusId`, `LastStatusDate`, `PayDate`, `RPReasonId`؛
- توضیح/برگشت: `RChequeComment`, `ChqHistComment`, `RetChequeComment`,
  `ChequeUnpaidPlaceName`, `ChequeUnpaidPlaceComment`, `ReceiptDate`؛
- صاحب/فروش: `NationalCode`, `CustomerCode`, `ManualCustCode`,
  `HozePayCustomerCode`, `LegalTypeName`, `PersonnelId`, `SaleOfficeName`.

### Validation و Command

`CanChangeStatus` آخرین History و تاریخ عملیات را می‌سنجد. `CanDoUndo` به آخرین
وضعیت، Transfer و Balance حساب وابسته است. انتخاب Grid پیش‌شرط فعال‌شدن
ChangeStatus است. SQL مقصد باید History append و Current pointer را اتمیک کند؛
Undo «حذف آزاد» نیست، فقط برگشت آخرین Transition معتبر است.

## ۲. پیگیری چک پرداختنی

### Work queue و Scope

Inbox اولیه `PChequeStatusId in (1,5)` است و همان تابع دسترسی DC/SaleOffice را
اعمال می‌کند؛ بنابراین این صفحه گزارش همه چک‌های پرداختنی نیست.

### ستون‌های قراردادی Grid

۱۶ ستون یکتا:

`PChequeId`, `PChequeBookName`, `PChequeBookItemNo`, `PChequeBookItemId`,
`PChequeDate`, `PChequeAmount`, `BankAccountId`, `PChequeStatusId`,
`LastStatusDate`, `PChequeIsCertified`, `PayDate`, `SaleOfficeName`,
`PChequeHistoryId`, `ModifiedDate`, `PayId`, `RPReasonId`.

`CanDoUndo` علاوه بر آخرین History، تکرار برگ دفترچه، Pay linkage، leaf بودن چک
و مانده را کنترل می‌کند. ChangeStatus و Undo مجوز مستقل دارند و هر دو باید
Optimistic concurrency روی Current history/version داشته باشند.

## ۳. اقلام انبار

صفحه List از Projection سروری `GNR.vwStockGoods_serverMode` تغذیه می‌شود و
`AccYear + DC + StockDCRef` بخشی از Scope است. موجودی یک Master کالای ساده
نیست؛ رابطهٔ کالا در یک انبار و سال مالی است.

Fieldهای اصلی کشف‌شده:

- کلید/Scope: `GoodsRef`, `StockDCRef`, `AccYear`, `DCRef`؛
- نمایش: `GoodsCode`, `GoodsName`, `GoodsTypeName`, `CartonType`, `location`؛
- سیاست موجودی: `IsBatch`, `OrderPoint`, `MinQty`, `MaxQty`؛
- Snapshot کمّی: `OnHandQty`, `DamagedQty`, `ReservedQty`, `UndeliveredQty`.

New/Edit/Delete با `HasPersmission` مستقل کنترل می‌شوند. Validatorهای اصلی وضعیت
کالا، ارتباط Batch، استفاده در Voucher، سفارش/فروش باز، جریان موجودی، سال مالی و
نوع حمل را می‌سنجند. در ERP مقصد Snapshot quantity باید از Ledger/Cardex قابل
Reconcile باشد و ویرایش سیاست انبار از تغییر مقدار موجودی جدا بماند.

## ۴. مدیریت توزیع

این صفحه یک Master/detail orchestrator است. List علاوه بر Dist header، مجموعه
`SaleS` را بار می‌کند و Data entry انتخاب Factor، تیم پخش، مسیر و ظرفیت خودرو
را ترکیب می‌کند.

### Header و برنامه‌ریزی

Fieldهای اصلی:

- کلید/Scope: `DistRef`, `DistNo`, `AccYear`, `DCRef`؛
- تاریخ/وضعیت: `DistDate`, `SendDate`, `ReturnDate`, `Status`؛
- مسیر: `DistPath`, `DistPathTreeNo`, `IDZonePath`؛
- تیم: `DistributerRef`, `RealDistributerRef`, `DriverRef`, `TruckRef`,
  `DistAssistant1Ref`, `DistAssistant2Ref`؛
- توضیح: `Description`, `Description2`؛
- Lock: `LockedByAppUserForExit`, `LockedByHostNameForExit` و همتای Return؛
- جزئیات: `SaleS`, `GoodsID/GoodsRef`, `BatchID/BatchNo`, `StockID`,
  `TotalQty`, `AcceptQty`, `GoodsExitID`.

Validation ظرفیت روزانه، حداقل/حداکثر وزن/حجم/مبلغ خودرو، تاریخ عملیات، وضعیت
جاری، وجود Sale/Return، موجودی/Batch، Lock مالک/Host و دلیل RemoveExit را درگیر
می‌کند. پنج SQL contract اصلی CreateDist، CreateExit، Merge exit، RemoveExit و
GetMaxDistNo به همین صفحه وصل‌اند.

## قرارداد API مقصد مشترک

Read model و Command model جدا باشند. Command باید دست‌کم این Envelope را
داشته باشد:

```text
command_id + aggregate_id + expected_version/current_state
+ operational_date + fiscal_year + dc/sale-office/stock scope
+ reason/evidence when required
```

سرور باید Permission، Scope، Feature، تاریخ و Transition را دوباره بررسی کند؛
Client enablement امنیت نیست. نتیجهٔ موفق باید Transaction اتمیک، Idempotency و
Audit event داشته باشد. هیچ Web client نباید مستقیم جدول عملیاتی وارانگار را
بنویسد.

## Artifact و بازتولید

- `scripts/windows/build_varanegar_active_page_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_active_page_contracts_20260827.json`
- `tests/test_varanegar_ui_evidence.py`
