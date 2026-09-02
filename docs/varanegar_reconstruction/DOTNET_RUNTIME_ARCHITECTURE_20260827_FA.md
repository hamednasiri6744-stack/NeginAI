# معماری Runtime و قرارداد فرم‌های وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **شاهد فقط‌خواندنی از فایل‌های Runtime فعال**

## هدف و مرز ایمنی

این سند مشخص می‌کند فرم‌های واقعی وارانگار چگونه از پوسته برنامه به Business
و DataAccess وصل می‌شوند. فایل‌ها از Share اجرای جاری خوانده شده‌اند، اما هیچ
Assembly بارگذاری یا اجرا نشده و هیچ Config، Resource payload، Connection
String یا مقدار Data-bound در Artifact ذخیره نشده است.

- Runtime: `\\192.168.1.171\exe\VN.SDS.Container`
- موجودی فایل: `artifacts/varanegar_analysis/ui/varanegar_binary_inventory_20260827.json`
- Metadata: `artifacts/varanegar_analysis/ui/varanegar_assembly_contracts_20260827.json`
- IL هدفمند: `artifacts/varanegar_analysis/ui/varanegar_targeted_il_contracts_20260827.json`
- UI→SQL: `artifacts/varanegar_analysis/ui/varanegar_ui_sql_contracts_20260827.json`
- Extractorها:
  - `scripts/windows/extract_varanegar_binary_inventory.ps1`
  - `scripts/windows/extract_varanegar_assembly_contracts.py`
  - `scripts/windows/extract_varanegar_targeted_il_contracts.py`
  - `scripts/sql/extract_varanegar_ui_sql_contracts.py`

در IL هدفمند، رشته‌های غیرمجاز فقط با SHA-256 و طول ثبت می‌شوند. تنها
Literalهای کوتاه ASCII که واژه تجاری/SQL دارند و شبیه Credential، URL، Email
یا Path نیستند، به‌صورت متن باقی می‌مانند.

## نمای کلان Runtime

- ۶۲ فایل First-party در ۲۸ خانواده و مجموع ۳۷٬۱۵۴٬۴۳۲ بایت دیده شد؛
- ۲۹ فایل هسته انتخابی بدون خطا تحلیل شد: ۴٬۲۸۶ Type و ۳۹٬۷۵۹ Method؛
- ۴۶۴ نامزد فرم و ۲٬۸۵۱ نامزد قرارداد Business شناسایی شد؛
- خانواده‌های `CreateVoucher`، `MainData`، `POSSystem`، `Sales`، `Setting`،
  `Stock`، `Tablet` و `Treasury` الگوی لایه‌ای زیر را دارند:

```text
Container/Menu
  -> UI / Forms
     -> IBusiness / Business
        -> DataAccess
           -> SQL
```

وجود فایل‌های `.disable` کنار DLLها نشان می‌دهد Runtime قابلیت تعویض/خاموش‌کردن
ماژول دارد. این شاهد به‌تنهایی مشخص نمی‌کند کدام Variant در هر لحظه انتخاب شده
است؛ وضعیت Load جاری باید جدا اثبات شود.

## پوسته، منو و Context کاربر

`VN.SDS.Container.Program.FillUserPermissionS` مجوزها را از
`AccessNodeInfoHandler` گرفته و برای هر Node پنج مؤلفه
`AccessNodeId`، `AccessNodeKey`، `ClassName`، `HasAccess` و `ParentId` را در
Session کاربر می‌سازد.

`MainForm.BuildMenu` و `GenerateSubMenu` منو را از `MenuConfigViewEntity` و
`UserPermissionS` تولید می‌کنند. فیلدهای `Caption`، `FileName`،
`IsShowInContainer` و سلسله‌مراتب Node در ساخت منو دخیل‌اند. بازکردن فرم از
`MdiManager.ShowForm` استفاده می‌کند و `OpenReason`، `ResourceId` و
`ShowModal` نیز بخشی از قرارداد Launch هستند.

منو بعد از تغییر DC دوباره ساخته می‌شود. همان مسیر Contextهای `AccYear`،
`DCRef`، `SalesOfficeRef` و تاریخ‌های عملیاتی حسابداری، خرید، خزانه، نصب و فروش
را روی GlobalVariables اعمال می‌کند. سپس `ApplyLockOnMenu` قابلیت‌های دارای
License/Feature flag مانند Treasury، Product، Reports، CallCenter، DirectSale،
POS و FreeInvoice را حذف/قفل می‌کند.

نتیجه برای ERP مقصد:

1. Authorization فقط Route guard فرانت نیست؛ Node tree، Class/Command access و
   Data partition باید سمت سرور هم اعمال شود؛
2. سال مالی و DC بخشی از Session/Query context هستند و تغییرشان باید Form state
   و cacheهای وابسته را باطل کند؛
3. Feature entitlement از User permission مستقل است؛ دسترسی نهایی حاصل اشتراک
   Role، Data partition، Context و Feature flag است؛
4. منوی وب باید از Capability contract ساخته شود، نه از فهرست ثابت صفحه‌ها.

## پیگیری چک دریافتی

دو Variant در `TreasuryOld.Forms.dll` وجود دارد:
`frmRChequeTracking` و `frmRChequeTrackingNew`. Variant جدید از DevExpress
`VNGrid` و Variant قدیمی از Janus `GridEX` استفاده می‌کند. Crosswalk
`MenuConfig→FormInfo` ثابت کرد Route فعال این Caption مستقیماً
`frmRChequeTracking` قدیمی را هدف می‌گیرد.
پیش از Crosswalk، Hash هفت Label زنده با User stringهای `InitializeComponent`
مقایسه شد؛ تمام Labelهای مشترک در هر دو Variant تطبیق داشتند و Labelهای متمایز
old/new در WindowText زنده قابل مشاهده نبودند. پس ارتقای اطمینان بدون شاهد جدید
درست نبود؛ شاهد Route بعدی این ابهام را با اطمینان بالا حل کرد. فقط امکان Redirect
کد runtime، که فعلاً شاهدی برای آن نیست، به‌عنوان محدودیت باقی می‌ماند.

قراردادهای مشترک/تأییدشده:

- `LoadData -> RChequeAdapter.GetRChequeSWhere`؛
- Variant جدید فیلتر اولیه `RChequeStatusId in (1,2,4,8)` دارد و
  `ReceiptStatusId` را نیز محدود می‌کند؛ Variant قدیمی Status 9 را هم در ورودی
  اولیه دارد؛
- مقصدهای Combo وضعیت از `RChequeWORKFLOW` می‌آیند، نه Enum ثابت؛ Status 7 در
  یک شاخه و Status 6 در یک Guard حذف می‌شود؛
- `SetFormPermission` دسترسی‌های مستقل `ChangeStatus` و `Undo` را مصرف می‌کند؛
- تغییر وضعیت قبل از اجرا `RchequeWorkFlow_IsValid` را بررسی کرده و سپس History
  اضافه می‌کند؛
- Undo تاریخچه، انتقال/واگذاری و Context صندوق/بانک را بررسی می‌کند؛
- Guardهای `OprDateIsValid` و `CanChangeStatus` نشان می‌دهد تاریخ عملیات بخشی از
  Command contract است؛
- بررسی Reconcile و ارتباط Pay/Receipt قبل از Transition در خود فرم وجود دارد.

بنابراین صفحه وب باید Query projection محدودشده، فهرست Transition مجاز از
Workflow، مجوز Command مستقل، Business date، Context وابسته به وضعیت و ثبت
Append-only event را جدا نگه دارد.

## پیگیری چک پرداختنی

دو Variant `frmPChequeTracking` و `frmPChequeTrackingNew` موجود است. هر دو:

- داده را از `PChequeAdapter.GetPChequeSWhere` می‌گیرند؛
- فهرست اولیه را به `PChequeStatusId in (1,5)` محدود می‌کنند؛
- Transitionهای Combo را از `PChequeWORKFLOW` می‌سازند؛
- `ChangeStatus` و `Undo` را به‌عنوان Permission مستقل می‌خوانند؛
- قبل از تغییر، `PchequeWorkFlow_IsValid`، برگ دسته‌چک، Pay، Balance/Margin و
  آخرین History را کنترل می‌کنند؛
- Undo بر `PChequeHistory` و Current pointer تکیه دارد.

در نتیجه «پیگیری پرداختنی» نیز Inbox کاری است، نه گزارش تمام چک‌های پرداختنی.
Projection تمام وضعیت‌ها و Work queue این صفحه باید در API مقصد دو قرارداد
جدا باشند.

## اقلام انبار

عنوان Runtime `اقلام انبار` با خانواده
`VN.SDS.Stock.UI.StockGoods.FormStockGoods` تطبیق معنایی و فنی دارد. قرارداد
لیست از مسیر زیر می‌آید:

```text
FormStockGoods.LoadInitData
  -> StockDCHandler
  -> StockGoodsUIHelper.StockGoodsGridServerModeDC
  -> GNR.vwStockGoods_serverMode
```

فیلدهای مصرف‌شده شامل `AccYear`، `StockDCRef`، `GoodsRef/Code/Name`،
`OnHandQty`، `ReservedQty`، `DamagedQty`، `MinQty`، `MaxQty`، `OrderPoint`،
`Location`، Batch flag و نوع/کارتن کالا است. Edit/Delete از
`StockGoodsHandler` و Validator عبور می‌کند.

این کشف ابهام قبلی را کم می‌کند: فرم، Projection سروری موجودی به تفکیک انبار
و سال مالی است؛ Master کالا به‌تنهایی Source آن نیست. بااین‌حال Snapshot
`StockGoods` همچنان جایگزین Cardex و OpenOrder نیست.

## مدیریت توزیع

عنوان Runtime با `FormDistManagementList` تطبیق دارد. لیست از
`DistHandler.GetAllView` با `DistViewEntityHelper`، `CheckStatus`،
`WhereStatement` و `SortField` تغذیه می‌شود. Detail فروش‌ها جدا و از
`SaleHandler.GetAllView` با `DistRef` بارگذاری می‌شود.

فرم ایجاد/ویرایش Distribution این داده‌ها را با `DistHandler.CreateDist`
ارسال می‌کند: تاریخ، مسیر، Truck، Driver، Distributer، RealDistributer، دو
Assistant، Send/Return date و KM، Status، توضیح و فهرست SaleHdr.

Commandهای فرم لیست دامنه‌ای و مستقل‌اند:

- `SetExitexportation` و `CreateExitVocherByDist` برای خروج انبار؛
- `SetFollowDist` و Follow-after-voucher؛
- `SetBackTopreviousStatus`؛
- `SetRevocation` با `Dist_Cancel_Validation`؛
- `RemoveExitFromDist` با Reason؛
- `SetFreeDistribution` و Merge خروج؛
- تغییر Batch و چاپ دسته‌ای.

این ساختار ثابت می‌کند Distribution یک CRUD ساده نیست. ERP مقصد به Commandهای
مجزا، Lock مالک/Host برای Exit/Return، Validator مرحله‌ای، تاریخ عملیاتی و
History تخصیص Sale نیاز دارد.

## قرارداد قطعی UI تا SQL Clone

Extractor مستقل روی Clone محلی `NeginPakhsh_WebDev` با وضعیت `READ_ONLY`،
`can_update=0` و `db_denydatawriter=1` اجرا شد. هر ۱۲ Object لازم پیدا شد؛ هیچ
Procedure اجرا و هیچ ردیف تجاری خوانده یا ذخیره نشد. فقط Signature، Dependency
و Hash Definition ثبت شد.

| UI/Command | SQL contract | ورودی‌های تعیین‌کننده | وابستگی مهم |
|---|---|---|---|
| ایجاد/ویرایش توزیع | `SLE.usp_sdsnet_CreateDist` | AccYear، DC، تاریخ/مسیر، تیم، Sale list، Status | `tblDist`، `tblSaleHdr`، `tblSaleDistHist` |
| صدور خروج توزیع | `dbo.usp_CreateExitVocherByDist` | DistRef، AccYear، DC، OprDate | Exit، Voucher، Sale، Batch/Cardex checks |
| Merge خروج | `inv.Usp_InsertGoodsExit_RD` | DistRef، GoodsExit_RD | `SLE.tblGoodsExit_RD` |
| حذف خروج | `inv.Usp_RemoveExitFromDist` | User، AccYear، DC، DistRef، LastDate، Reason، Status | Exit/Voucher/Sale history/return tables |
| شماره توزیع | `dbo.GetMaxDistNo` | DC، AccYear | `SLE.tblDist` و Config |
| افزودن رخداد چک دریافتی | `dbo.DoRCheque_AddRChequeHistory` | Status/date + bank/safe/person/context | `Acc.tblChqHist`، `Receipt`، `Transfer` |
| Undo چک دریافتی | `dbo.DoRCheque_DeleteLastRChequeHistory` | ChequeId، User | current history و projection |
| اعتبار Transition دریافتی | `dbo.RchequeWorkFlow_IsValid` | ChequeId، current status | `RChequeWorkflow` + current history |
| افزودن رخداد چک پرداختنی | `dbo.DoPCheque_AddPChequeHistory` | Status/date/comment/user/DC | History، cheque book، Pay/RPReason |
| Undo چک پرداختنی | `dbo.DoPCheque_DeleteLastPChequeHistory` | ChequeId، User | History + current pointer + cheque-book item |
| اعتبار Transition پرداختنی | `dbo.PChequeWorkFlow_IsValid` | ChequeId، current status | `PChequeWorkflow` + history |
| Grid اقلام انبار | `GNR.vwStockGoods_serverMode` | Query context | `tblStockGoods`، `tblStockDC`، `vwGoods` |

Definition hash در Artifact برای تشخیص Drift نسخه آینده ذخیره شده است؛ متن کامل
Definition در Artifact جدید تکرار نشده است.

## سطح اطمینان و ابهام‌های باز

| یافته | اطمینان | محدودیت |
|---|---|---|
| معماری Container→UI→Business→DataAccess | بالا | از Metadata همه فایل‌های هسته |
| منوی پویا از Permission + MenuConfig | بالا | از Call graph مستقیم |
| منبع اقلام انبار `StockGoodsGridServerModeDC` | بالا | از `LoadInitData` |
| مدیریت توزیع = `FormDistManagementList` | بالا | عنوان + خانواده/Commandها |
| Query و Workflow دو فرم چک | بالا | Adapter و Literal مستقیم IL |
| Variant دقیق old/new فرم چک باز | بالا | FormInfo به Variant قدیمی Route شده؛ Redirect مشاهده نشده |
| ترتیب دقیق تمام Transitionها | متوسط | Validator/Business DLL هنوز IL کامل نشده |

گام بعدی تحلیل، تکمیل Capability matrix صفحه/Command/Role/DataPartition و
استخراج Validatorهای مسیر فروش/خروج وابسته است. پس از آن قرارداد API مقصد از
همین Commandها و نه از CRUD جدول‌ها ساخته می‌شود.

## دستور بازتولید

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File G:\NeginAI\scripts\windows\extract_varanegar_binary_inventory.ps1 `
  -SourceDirectory '\\192.168.1.171\exe\VN.SDS.Container' `
  -Output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_assembly_contracts.py `
  --source-directory '\\192.168.1.171\exe\VN.SDS.Container' `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_assembly_contracts_20260827.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_targeted_il_contracts.py `
  --source-directory '\\192.168.1.171\exe\VN.SDS.Container' `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_targeted_il_contracts_20260827.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_ui_sql_contracts.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_ui_sql_contracts_20260827.json
```
