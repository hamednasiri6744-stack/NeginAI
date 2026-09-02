# دامنه ۸: موجودی، رزرو، گردش انبار و خروج کالا

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- سرور: `127.0.0.1`
- دیتابیس: `NeginPakhsh_WebDev`
- وضعیت: `READ_ONLY`
- حساب تحلیل: `Negin_Report_ReadOnly` با `UPDATE=0` و
  `db_denydatawriter=1`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/inventory_reservation_and_exit_20260826.json`

این مرحله ۱۳ جدول، ۱۰۰ ارتباط FK رسمی، ۱٬۸۸۱ مصرف‌کننده ماژولی و ۲۹۱
کاندید ارتباط ضمنی را بررسی کرده است. ۱۷۷ کاندید FK رسمی ندارند. هیچ Comment،
نام کاربر/میزبان، طرف‌حساب یا Credential در Artifact ذخیره نشده است.

## نتیجه اصلی: «موجودی» یک عدد واحد نیست

در Runtime فعلی دست‌کم چهار قرارداد جدا وجود دارد:

```text
مانده عملیاتی سالم          GNR.tblStockGoods.OnHandQty
رزرو سندی                   GNR.tblStockGoods.ReservedQty
تعهد سفارش باز              FRU.StockGoodsModel.OpenOrderQty
موجودی تور/خودروی توزیع     NGT.StockLevels
```

در مدل مقصد نباید این چهار مفهوم در یک ستون `available_qty` ادغام شوند.
دو برداشت فعلی از «قابل‌فروش» نیز با هم متفاوت‌اند:

- `OnHandQty - ReservedQty`: در ۲۱۲ کلید کالا–انبار منفی است؛
- `OnHandQty - OpenOrderQty` که در `FRU.StockGoodsModel.RemQty` استفاده می‌شود:
  فقط در ۳ کلید منفی است.

از ۳۳٬۳۱۴ کلید جاری، ۲۹۷ کلید رزرو سندی، ۳۱۸ کلید سفارش باز و فقط ۱۱ کلید
هر دو نوع تعهد را هم‌زمان دارند. مجموع `OpenOrderQty` برابر ۹٬۸۷۳ واحد است.
پس رزرو سندی و تعهد سفارش باز دو Ledger مستقل‌اند، نه دو نام برای یک مقدار.

## انبارها و Snapshot موجودی

ده مرکز انبار تعریف شده است، اما در سال عملیاتی ۱۴۰۵ فقط ۹ مرکز رکورد موجودی
دارند؛ انبار بسته‌بندی `ID=8` در Snapshot سال جاری ردیفی ندارد. هر ده انبار
`AllowNegativeOnHandQty=0` و `AllowNegativeCardexQty=0` دارند.

| سال عملیاتی | ردیف موجودی | انبار | کالا |
|---:|---:|---:|---:|
| ۱۴۰۳ | ۹٬۲۷۶ | ۴ | ۲٬۳۱۹ |
| ۱۴۰۴ | ۲۴٬۵۷۱ | ۷ | ۳٬۵۴۸ |
| ۱۴۰۵ | ۳۳٬۳۱۴ | ۹ | ۳٬۸۲۴ |

در سال ۱۴۰۵:

- ۵٬۴۷۲ ردیف مانده سالم مثبت دارند و هیچ `OnHandQty` منفی نیست؛
- ۲۹۷ ردیف `ReservedQty` غیرصفر دارند و هیچ رزرو منفی نیست؛
- ۱٬۰۱۵ ردیف موجودی ضایعاتی غیرصفر دارند؛
- `UnDeliveredQty` در همه ردیف‌ها صفر است؛
- هیچ ردیف `IsBatch=1` نیست.

Trigger کنترل موجودی منفی، منفی‌شدن هر جزء `OnHandQty`، `DamagedQty`،
`UnDeliveredQty` و `ReservedQty` را جداگانه کنترل می‌کند؛ اما منفی‌شدن تفاضل
`OnHandQty-ReservedQty` را منع نمی‌کند. به همین دلیل ۲۱۲ تفاضل منفی، تناقض با
پرچم‌های منع موجودی منفی نیست.

## گردش انبار و قرارداد Cardex

`inv.tblVocherHdr` تعداد ۹۶٬۵۰۲ سند و `inv.tblVocherItm` تعداد ۱٬۵۱۸٬۱۶۶
ردیف برای ۳٬۶۱۶ کالا دارد. ۹۶٬۴۹۵ سند تأیید و ۷ سند تأییدنشده‌اند. تمام
مقادیر `TotalQty` مثبت و تمام `UnitCapacity`ها بزرگ‌تر از صفرند.

شماره سند فقط با ترکیب زیر در داده فعلی یکتا است:

```text
(AccYear, StockDCRef, VocherTypeCode, VocherNo)
```

۱۰٬۱۱۸ Header فاقد UUID است و یک گروه UUID تکراری وجود دارد؛ بنابراین UUID
منبع بدون کنترل یکتایی Snapshot نمی‌تواند کلید اصلی مقصد باشد.

در پنجره تجاری `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` تعداد ۱۲٬۲۶۲ سند ثبت شده است:

| نوع عملیات | سند | ردیف |
|---|---:|---:|
| برگشت حواله | ۵٬۱۶۲ | ۱۷٬۶۷۲ |
| خروجی | ۳٬۱۹۹ | ۱۶۰٬۶۱۳ |
| برگشت به انبار | ۱٬۲۰۸ | ۳٬۳۵۱ |
| انباربه‌انبار بدهکار | ۶۹۹ | ۵٬۶۶۶ |
| انباربه‌انبار بستانکار | ۶۹۵ | ۵٬۷۰۸ |
| رسید انبار | ۵۶۴ | ۴٬۷۶۵ |
| رزرو | ۲۵۴ | ۱٬۱۴۳ |
| برگشت از رزرو | ۱۷۷ | ۱٬۱۵۹ |

`inv.tblCardexType` قرارداد جهت و محل اثر هر نوع سند را با `CardexType`،
`EffectType` و سه پرچم اثر روی سالم/ضایعاتی/رزرو نگه می‌دارد. این جدول و
Viewهای رسمی Cardex باید به‌صورت Crosswalk نسخه‌دار مهاجرت شوند؛ Hard-code
کردن علامت‌ها در UI مجاز نیست.

Trigger اصلی چند مسیر خاص مانند نوع ۶۰ و ۶۵ را از مسیر عمومی عبور نمی‌دهد و
در متن آن نوع ۱۲ «بدون اثر روی کاردکس» معرفی شده است. در مقابل Viewهای Cardex
مجموعه قواعد خود را دارند. این ناهمگونی شاهد وجود چند مسیر تخصصی Legacy است
و علت هر مغایرت را نمی‌توان صرفاً از نام نوع سند حدس زد.

## اصلاح نتیجهٔ مغایرت‌گیری Snapshot و Cardex

مقایسهٔ اولیهٔ زیر فقط `tblStockGoods` را با `vwHealthyCardex` سنجیده بود و
فرمول کامل عملیاتی وارانگار را لحاظ نمی‌کرد:

مقایسه سال ۱۴۰۵ با Viewهای رسمی:

| مؤلفه | کلید مقایسه‌شده | تطبیق دقیق | مغایرت | قدرمطلق اختلاف |
|---|---:|---:|---:|---:|
| ضایعاتی | ۳۳٬۳۱۴ | ۳۳٬۳۱۴ | ۰ | ۰ |
| رزرو سندی | ۳۳٬۳۱۴ | ۳۳٬۳۱۴ | ۰ | ۰ |
| سالم، مقایسهٔ ناقص Cardex-only | ۳۳٬۳۱۴ | ۳۱٬۷۲۰ | ۱٬۵۹۴ | ۱۰۴٬۴۷۰ |

تحلیل دقیق `dbo.usp_ModifyStockGoods` ثابت کرد این ۱٬۵۹۴ مورد مغایرت نیستند.
فرمول رسمی `vwHealthyCardexForCheck` را با چند تعهد عملیاتی تعدیل می‌کند. در
Snapshot فعلی تنها تعهد غیرصفر «فروش فعالِ هنوز خارج‌نشده» است و دقیقاً همان
۱٬۵۹۴ کلید و ۱۰۴٬۴۷۰ واحد را می‌سازد. پس از اعمال فرمول کامل، هر ۳۳٬۳۱۴ کلید
با `tblStockGoods.OnHandQty` تطبیق دارند و Residual صفر است.

انبارهای ۱، ۲، ۳ و ۹ دارای تعهد فروش بازند؛ نه ماندهٔ خراب. قرارداد مقصد:

1. `StockGoods` منبع Snapshot عملیاتی لحظه‌ای باشد؛
2. Cardex به‌عنوان Ledger تغییرناپذیر مستقل مهاجرت شود؛
3. `OpenSaleStockObligation` جدا و قابل Rebuild باشد؛
4. Projection عملیاتی از `Cardex - obligations` ساخته شود؛
5. فقط Residual پس از فرمول کامل به‌عنوان مغایرت ثبت شود؛
6. هیچ Rebuild یا Overwrite خودکار اجرا نشود.

جزئیات و Runbook:
`STOCK_RECONCILIATION_INCIDENT_PLAYBOOK_20260827_FA.md`.

## رزرو رسمی و سفارش باز

رزرو سندی از نوع ۷۶ و برگشت آن از نوع ۴۱ ساخته می‌شود. Stored Procedure
`inv.UspListOfReservedGoods` مانده را با همین گردش و علت/HealthCode محاسبه
می‌کند. تطبیق صفر اختلاف با `ReservedQty` این قرارداد را تأیید می‌کند.

اما `FRU.StockGoodsModel` سفارش‌های فعالِ بدون فروش نهایی را با قرارداد نوع
سفارش و Package قابل‌فروش به‌عنوان `OpenOrderQty` جمع می‌کند. این عدد در
`ReservedQty` ذخیره نشده است. در مقصد دو موجودیت لازم است:

- `InventoryReservationLedger` برای سندهای ۷۶/۴۱؛
- `SalesCommitmentProjection` برای سفارش‌های باز، با قابلیت Rebuild.

## خروج کالا و اتصال به فروش

`inv.tblExit` تعداد ۳۳٬۹۴۵ خروج دارد: ۲۴٬۰۳۵ فعال و ۹٬۹۱۰ لغوشده. همه
خروج‌ها `DistRef` دارند و هیچ‌کدام `DriverRef` مستقیم ندارند؛ راننده از دامنه
توزیع به‌دست می‌آید.

اتصال نوع ۶۰ کاملاً تأیید شد:

```text
inv.tblExit فعال 1 ─── 1 inv.tblVocherHdr(VocherTypeCode=60, DocRef=Exit.ID)
```

- ۲۴٬۰۳۵ Header نوع ۶۰ و ۲۴٬۰۳۵ `DocRef` متمایز؛
- تطبیق با تمام ۲۴٬۰۳۵ خروج فعال؛
- تطبیق انبار در همه موارد؛
- خروج فعال بدون سند نوع ۶۰ و `DocRef` تکراری: صفر؛
- ۲۴۸٬۵۵۳ Sale به همین ۲۴٬۰۳۵ خروج فعال وصل‌اند و هیچ اتصال یتیم یا متصل
  به خروج لغوشده نیست.

`DocRef` در کل جدول Voucher چندریختی است. این اثبات فقط برای نوع ۶۰ معتبر است
و Join عمومی `DocRef` به Exit یا Sale ممنوع است.

در پنجره سه‌ماهه ۴٬۷۳۸ خروج ثبت شده که ۱٬۵۳۹ مورد لغوشده‌اند؛ این خروج‌ها
۷ انبار و ۳٬۲۵۳ توزیع را پوشش می‌دهند.

## Projection پیش‌فروش

`dbo.PreSaleStockOnHandQty` فقط ۶۵۷ کالا از یک انبار را پوشش می‌دهد. همه UUID
کالا و انبار معتبرند، هیچ مانده منفی و هیچ `HasAllocation=1` وجود ندارد. این
جدول Projection محدود برای پیش‌فروش است و به‌جای Master ۳٬۸۲۴ کالایی موجودی
قابل استفاده نیست.

## موجودی تور/خودروی NGT

`NGT.StockLevels` تعداد ۴۰٬۹۴۵ ردیف یکتا برای ۵۶۶ تور و ۱٬۳۴۱ کالا دارد.
تمام اتصال‌های UUID کالا و تور معتبرند و تکرار `(TourUniqueId,ProductUniqueId)`
وجود ندارد. همه ردیف‌ها فعال، بدون Conflict و دارای `Number_ID=0` هستند.

در Snapshot فعلی فقط `InitialQty` در ۴۰٬۹۴۴ ردیف پر است؛ `RenewQty`،
`SoldQty`، `RemainQty` و `ActualQty` خالی‌اند. جدول هم‌نام `FRU.StockLevels`
خالی است، ولی `FRU.StockLevelsModel` قرارداد محاسبه مانده، فروش و برگشت تور
را تعریف می‌کند. بنابراین ردیف‌های NGT «موجودی اولیه همگام‌شده تور» هستند،
نه شاهد یک Ledger کامل و نه جایگزین موجودی انبار.

## Batch در وضعیت فعلی

هر سه مسیر فعلی خالی‌اند:

- `GNR.tblStockGoodsDetail`: صفر؛
- `inv.tblVocherItmDetail`: صفر؛
- `NGT.BatchOnHands`: صفر.

با وجود صفر بودن داده، ستون‌ها، Triggerها و Stored Procedureهای Batch در
برنامه وجود دارند. مقصد باید قابلیت Batch را در Schema حفظ کند اما فعال‌سازی
عملیاتی آن را به Reconciliation و تست جدا موکول کند.

## قرارداد اولیه مدل مقصد

حداقل موجودیت‌ها و Projectionهای مستقل:

- `Warehouse` و `WarehouseChannelCrosswalk`؛
- `InventoryBalanceSnapshot` با کلید `(year, warehouse, product)`؛
- `InventoryMovementHeader/Line` با شماره مرکب و UUID منبع nullable؛
- `InventoryMovementEffectRule` نسخه‌دار؛
- `InventoryReservationLedger`؛
- `SalesCommitmentProjection`؛
- `WarehouseExit` و `WarehouseExitSale`؛
- `PresaleStockProjection` با Scope صریح؛
- `TourStockSnapshot` مستقل از موجودی انبار؛
- `InventoryReconciliationFinding` بدون اصلاح خودکار.

برای Quantity باید واحد پایه، Package/Unit مبدأ، جهت اثر و Scope انبار/تور
صریح ذخیره شود. وضعیت Confirm/Cancel نیز رویداد دامنه است، نه Boolean نمایشی
بدون تاریخچه.

## ابهام‌های باز

1. Residual فرمول رسمی در Snapshot فعلی صفر است؛ تکرار همین سنجش روی Snapshot
   مجاز و آرام Production با Watermark هنوز لازم است.
2. نقش دقیق `HealthCodeType=1009` و دو مقدار «تغییر قیمت/قیمت قدیم» در رزرو.
3. قرارداد Runtime پرشدن `PreSaleStockOnHandQty` و زمان Refresh آن.
4. علت خالی‌بودن تمام مسیرهای Batch با وجود کد فعال پشتیبان.
5. زمان و قاعده انتقال InitialQty تور به فروش/برگشت/مغایرت واقعی NGT.

## Golden Caseهای لازم

1. ورودی/خروجی تأییدشده با اثر جهت‌دار؛
2. Voucher لغوشده بدون اثر جاری؛
3. رزرو و برگشت رزرو؛
4. Exit چند Sale و جلوگیری از دوباره‌خروج؛
5. مانده تخصصی متفاوت در Reconciliation، بدون اصلاح خودکار؛
6. Presale projection محدود در برابر موجودی اصلی؛
7. Tour InitialQty بدون ادعای Ledger کامل؛
8. Batch capability بدون داده فعلی.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_inventory_reservation_exit_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\inventory_reservation_and_exit_20260826.json
```
