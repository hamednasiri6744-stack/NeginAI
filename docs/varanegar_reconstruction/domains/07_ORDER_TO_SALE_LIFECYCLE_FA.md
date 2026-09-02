# دامنه ۷: چرخه سفارش تا فروش وارانگار

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- سرور: `127.0.0.1`
- دیتابیس: `NeginPakhsh_WebDev`
- وضعیت: `READ_ONLY`
- حساب تحلیل: `Negin_Report_ReadOnly` با `UPDATE=0` و
  `db_denydatawriter=1`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/order_sale_lifecycle_20260826.json`

هیچ ردیف مشتری/پرسنل، Comment، نشانی، نام کاربری یا Credential در Artifact
ذخیره نشده است. این مرحله ۱۷ جدول، ۱۲۷ FK رسمی، ۱٬۹۴۹ مصرف‌کننده ماژولی و
۱۹۲ کاندید ارتباط ضمنی را بررسی کرد؛ ۱۳۴ کاندید FK رسمی ندارند.

## نتیجه اصلی: سفارش یک فروش واحد تولید نمی‌کند

```text
SLE.tblOrderHdr
  ├──< SLE.tblOrderItm
  ├──< SLE.tblOrderToSaleTime       (تلاش‌های تبدیل)
  ├──< SLE.tblOrderHdrCustPathInfo  (Snapshot مسیر)
  ├──< SLE.tblSaleHdr               (نسخه‌ها/تلاش‌های فروش)
  │      ├──< SLE.tblSaleItm
  │      ├──< SLE.tblSaleHdrDetail  (رویداد/اسنپ‌شات وضعیت)
  │      └── 0..1 SLE.tblSaleVocherHdr + Items
  └── SaleHdrRef ──> فروش منتخب فعلی
```

`SaleHdr.OrderRef` همه تلاش‌های تبدیل را به سفارش وصل می‌کند، اما
`OrderHdr.SaleHdrRef` فقط نسخه منتخب را نشان می‌دهد. این دو رابطه نباید به یک
FK یک‌به‌یک ساده تقلیل پیدا کنند.

## Master نوع سفارش

۲۳ نوع سفارش تعریف شده است. نمونه‌های مهم: پیش‌ویزیت، رسمی عادی، قراردادی،
پیش‌ویزیت بدون آفر و تخفیف، انواع تهران/گیلان/قزوین، حمل مستقیم، پیش‌فروش،
حواله/فاکتور/مرجوع امانی، پیش‌فاکتور و فروش فروشگاهی.

- تمام Typeها UUID دارند.
- `Selectable` مقادیر ۰، ۱ و ۲ دارد و Boolean ساده نیست.
- فقط «پیش‌فاکتور» `EffectOrderOnStockGoods=1` دارد.
- View رسمی محاسبه موجودی سفارش باز، Typeهای ۱۰۰۳/۱۰۰۷/۱۰۰۸ را استثنا می‌کند
  و Typeهایی با `EffectOrderOnStockGoods=0` را از موجودی قابل نمایش کم می‌کند.

پس اثر موجودی را نمی‌توان از نام نوع سفارش یا یک Flag به‌تنهایی بازسازی کرد؛
Rule مرکب Type/State/Line/Package لازم است.

## وضعیت سفارش

| شاخص | مقدار |
|---|---:|
| سفارش | ۲۶۰٬۵۱۷ |
| UUID کامل و یکتا | ۲۶۰٬۵۱۷ |
| CancelFlag=0 | ۲۴۹٬۴۱۲ |
| لغوشده | ۱۱٬۱۰۵ |
| ConfirmDate پر | ۲۶۰٬۵۱۵ |
| دارای SaleHdrRef منتخب | ۲۴۹٬۶۰۳ |

State مشتق‌شده فعلی:

| وضعیت | سفارش |
|---|---:|
| فروش نهایی فعال | ۲۱۲٬۷۵۹ |
| فروش منتخب لغوشده | ۳۴٬۳۹۷ |
| خود سفارش لغوشده | ۱۱٬۱۰۵ |
| حواله/فروش موقت فعال بدون SaleNo | ۲٬۲۱۴ |
| تأییدشده بدون Sale | ۴۲ |
| تأییدنشده فعال | ۰ |

وجود ConfirmDate برای تقریباً همه رکوردها فقط Stored State را ثابت می‌کند؛
ثابت نمی‌کند تأیید حتماً انسانی یا یک مرحله مستقل Workflow بوده است. این موضوع
باید از Procedure و رفتار UI با Golden Test تأیید شود.

## وضعیت اقلام سفارش

Lookup رسمی `IsUsed`:

- ۰: عدم صدور — ۲۱۳٬۵۰۷ Line؛
- ۱: صادر — ۱٬۲۳۶٬۱۴۶ Line؛
- ۲: درخواست بخشی — ۳٬۰۳۵ Line؛
- ۳: عدم درخواست — ۱۷٬۰۳۹ Line.

تمام ۱٬۴۶۹٬۷۲۷ Line فعلی `IsDeleted=0` و `SoldQty=0` دارند. بنابراین SoldQty
در Snapshot فعلی منبع واقعیت مقدار صادرشده نیست؛ وضعیت صدور، SaleItem و
جزئیات مقدار باید با هم Reconcile شوند.

## فروش، حواله و تلاش‌های تبدیل

| شاخص | مقدار |
|---|---:|
| SaleHdr | ۲۷۵٬۹۹۵ |
| UUID کامل و یکتا | ۲۷۵٬۹۹۵ |
| فعال / لغوشده | ۲۱۴٬۹۷۳ / ۶۱٬۰۲۲ |
| دارای SaleNo نهایی | ۲۱۳٬۰۸۳ |
| بدون SaleNo | ۶۲٬۹۱۲ |
| دارای SaleVocherNo | ۲۶۶٬۱۸۳ |
| دارای ExitRef / DistRef | ۲۴۸٬۵۵۳ / ۲۴۸٬۵۵۴ |

ترکیب وضعیت جاری Sale:

- ۲۱۲٬۷۵۹ فاکتور فعال با `Status=1` و SaleNo؛
- ۲٬۲۱۴ حواله فعال با `Status=2` و بدون SaleNo؛
- ۲۶٬۲۹۷ حواله لغوشده با Status=2؛
- ۳۴٬۴۰۱ مرجوع/مرحله لغوشده با Status=3؛
- ۳۲۴ فاکتور شماره‌دار لغوشده.

`SaleNo=NULL` در Sale فعال خطای شماره‌گذاری نیست؛ وضعیت حواله/پیش‌فاکتور فروش
است. Final Invoice و Voucher Stage باید Stateهای جدا باشند.

## رابطه چندنسخه‌ای سفارش و فروش

- ۱۸٬۰۰۹ سفارش بیش از یک SaleHdr تاریخی دارند.
- هیچ سفارش بیش از یک Sale فعال ندارد.
- هیچ Sale فعال خارج از `OrderHdr.SaleHdrRef` منتخب نیست.
- ۲۶٬۳۹۲ Sale لغوشده نسخه قدیمی و غیرمنتخب‌اند.
- ۳۴٬۶۳۰ Sale لغوشده هنوز Pointer منتخب سفارش‌اند؛ ۳۴٬۳۹۷ مورد متعلق به
  سفارش‌های غیرلغوشده‌اند و حالت «تلاش تبدیل لغوشده/منتظر اقدام بعدی» می‌سازند.
- هیچ OrderRef یا Reverse Pointer یتیم/ناسازگار پیدا نشد.

در مقصد، حذف نسخه لغوشده یا Unique کردن `Sale.OrderId` تاریخچه واقعی را خراب
می‌کند. `OrderConversionAttempt` و `SelectedSaleVersion` لازم‌اند.

## Snapshot و تاریخچه وضعیت فروش

`tblSaleVocherHdr` دقیقاً ۲۶۶٬۱۸۳ Header یکتا برای ۲۶۶٬۱۸۳ Sale و
۲٬۱۲۸٬۲۵۳ Item دارد؛ Sale یتیم و Snapshot تکراری ندارد. این تعداد دقیقاً با
Saleهای دارای VoucherNo برابر است.

`tblSaleHdrDetail` تعداد ۵۴۰٬۸۸۸ رویداد/جزئیات برای تمام ۲۷۵٬۹۹۵ Sale دارد؛
۲۶۴٬۲۹۷ Sale بیش از یک Detail دارند. توزیع مهم:

- ۲۶۶٬۱۸۳ رویداد Status=2 با Snapshot XML کالا/گروه؛
- ۲۰۳٬۲۷۲ رویداد Status=1 بدون Snapshot مجدد؛
- ۹٬۸۱۲ رویداد Status=1 با Snapshot کالا؛
- ۳۵٬۰۰۰ رویداد Status=3؛
- ۲۶٬۶۲۱ رویداد Status=0.

پس Detail صرفاً Extension یک‌به‌یک Header نیست؛ ترکیبی از Snapshot و Event
انتقال وضعیت است. XMLهای قدیمی باید به Snapshot ساخت‌یافته و Versioned تبدیل
شوند، نه اینکه آخرین ردیف روی Header overwrite شود.

## Snapshot مسیر در زمان سفارش

`tblOrderHdrCustPathInfo` تعداد ۴۷٬۰۷۴ Snapshot یکتا دارد؛ همه دارای Path،
SaleArea، SaleZone، Dealer و Area هستند و هیچ Order یتیم/تکراری ندارد. در سه
ماه اخیر فقط ۱۳٬۶۶۳ سفارش از ۳۸٬۰۶۳ سفارش این Snapshot را دارند.

این پوشش ناقص نشان می‌دهد نمایش مسیر تاریخی نباید همیشه از Master فعلی مشتری
خوانده شود. اگر Snapshot موجود است همان شاهد سند است؛ در غیر این صورت Source
و زمان Lookup باید صریح ثبت شود.

## زمان تبدیل

`tblOrderToSaleTime` تعداد ۲۶۶٬۲۰۲ اجرای تبدیل برای ۲۴۴٬۳۶۴ سفارش دارد؛
۱۸٬۰۱۳ سفارش چند اجرای ثبت‌شده دارند. Start/End همه کامل‌اند، مدت منفی صفر،
میانگین اجرای ثبت‌شده ۲٫۳۵ ثانیه و فقط ۲۱۱ اجرا بیش از ۶۰ ثانیه‌اند.

این جدول زمان اجرای عملیات تبدیل است، نه Lead Time سفارش مشتری تا تحویل؛ برای
KPI زمان چرخه نباید با OrderDate/SaleDate اشتباه گرفته شود.

## فعالیت سه ماه تجاری

در `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` تعداد ۳۸٬۰۶۳ سفارش ثبت شده است:

| وضعیت | سفارش |
|---|---:|
| فروش نهایی فعال | ۳۰٬۱۳۳ |
| فروش منتخب لغوشده | ۳٬۸۲۶ |
| حواله فعال | ۲٬۲۱۴ |
| سفارش لغوشده | ۱٬۸۴۸ |
| تأییدشده بدون Sale | ۴۲ |

Typeهای پرتعداد: پیش‌ویزیت ۲۰٬۰۲۹، پیش‌ویزیت تهران ۸٬۱۰۴، رسمی عادی ۳٬۶۵۱ و
پیش‌ویزیت گیلان ۲٬۵۴۷. در همان بازه SaleDate، تعداد ۴۰٬۰۵۹ SaleHdr برای
۳۶٬۷۷۳ سفارش دیده می‌شود که ۷٬۷۰۲ مورد لغوشده است؛ اختلاف با تعداد سفارش
نتیجه چند تلاش و تفاوت تاریخ سندهاست.

## Crosswalk با NGT

### Header

`NGT.CustomerCallOrders` تعداد ۲۲۸٬۲۸۴ ردیف فعال دارد. Header قدیمی پوشش
Back-office کامل ندارد:

- `Number_ID` در تمام ردیف‌ها صفر است.
- `BackOfficeOrderUniqueId` در تمام ردیف‌ها Null است.
- `BackOfficeOrderId` برای ۲۱۸٬۴۸۹ ردیف صفر و فقط برای ۹٬۷۹۵ ردیف مثبت و
  منطبق با Order است.
- همین ۹٬۷۹۵ ردیف Invoice ID معتبر دارند؛ Invoice UUID فقط برای ۳٬۵۹۳ مورد
  منطبق است و هرجا هر دو موجودند توافق دارند.

بنابراین Header NGT به‌تنهایی Crosswalk کامل سفارش نیست.

### Line

`NGT.CustomerCallOrderLines` تعداد ۱٬۲۳۹٬۹۹۸ ردیف دارد که ۱٬۲۲۰٬۸۴۰ فعال‌اند:

- UUID کالا در همه ۱٬۲۳۹٬۹۹۸ ردیف معتبر است.
- ۱٬۱۱۲٬۷۱۱ Line هم BackOfficeOrderRef و هم BackOfficeOrderUUID منطبق دارند؛
  ID و UUID در همه این موارد توافق دارند.
- ۲۱۱٬۲۱۱ Order NGT حداقل یک Line منطبق و ۱۹۹٬۹۲۳ Order تمام Lineهای منطبق
  دارند.
- هفت Order NGT به بیش از یک Order back-office شکسته شده‌اند؛ Split Order یک
  قابلیت واقعی است.
- `ItemRef` برای ۱٬۱۷۷٬۳۴۳ Line Null است و مقدارهای پرشده نیز با OrderItem
  فعلی تطبیق ندارند؛ این فیلد Crosswalk قابل اتکا نیست.

`PriceUniqueId` تاریخی Polymorphic است: ۶۳۳٬۰۸۰ UUID صفر، ۶۲٬۴۶۱ UUID از
`tblPrice` و ۵۴۴٬۴۵۷ UUID از `tblCPrice`. ستون جدیدتر `CPriceUniqueId` برای
۷۰۱٬۲۲۰ ردیف پر و همگی معتبر است. موتور مقصد باید نوع Source قیمت را صریح
نگه دارد؛ یک FK واحد برای PriceUniqueId کافی نیست.

جزئیات مقدار NGT شامل ۱٬۲۹۰٬۰۴۷ ردیف مقدار درخواستی و ۳۲٬۶۴۲ ردیف مقدار
فاکتورشده است؛ هیچ Line یتیم ندارد.

## کلیدها و کیفیت ارجاع

- UUID سفارش و Sale یکتا است.
- OrderNo به‌تنهایی ۸۶٬۵۸۱ گروه تکراری و SaleNo به‌تنهایی ۶۷٬۹۶۸ گروه
  تکراری دارد.
- ترکیب `AccYear + DCRef + OrderNo` و `AccYear + DCRef + SaleNo` یکتا است.
- `AccYear + DCRef + SaleVocherNo` نیز یکتا است.
- RowOrder فعال در Itemهای Order/Sale داخل Header تکراری نیست.
- مشتری، فروشنده، Header و Line یتیم در Order/Sale پیدا نشد.

پس شماره نمایشی سند Cross-system ID نیست و حتی Global Unique هم نیست. مدل
مقصد باید UUID داخلی مستقل و کلید تجاری مرکب نسخه‌دار داشته باشد.

## قرارداد اولیه مدل مقصد

- `SalesOrder` با UUID داخلی و Source UUID/ID؛
- `SalesOrderLine` با RequestedQty و وضعیت صدور؛
- `OrderType` نسخه‌دار با قواعد موجودی/تخفیف؛
- `OrderStateEvent` برای Confirm/Cancel/Conversion؛
- `OrderRouteSnapshot`؛
- `OrderCalculationSnapshot` برای CPrice/Rule/Prize؛
- `OrderConversionAttempt` با Start/End/Result؛
- `SaleDocument` به‌عنوان نسخه/تلاش وابسته به Order؛
- `SelectedSaleVersion` یا Pointer صریح روی Order؛
- `SaleStateEvent` و `VoucherSnapshot` غیرقابل‌تغییر؛
- `SaleLine` با قیمت و Rule Snapshot؛
- `ExternalDocumentLink` چندشناسه‌ای برای NGT ID/UUID/Line split؛
- `MigrationQuarantine` برای ItemRef نامنطبق و Crosswalk ناقص؛
- `IdempotencyKey` مستقل برای جلوگیری از ساخت تلاش تکراری ناخواسته.

## قواعد قطعی برای وب‌ERP

1. Order و Sale دو Aggregate جدا هستند؛ تبدیل Order می‌تواند چند Attempt بسازد.
2. فقط یک Sale فعال منتخب مجاز است، ولی نسخه‌های لغوشده حذف نمی‌شوند.
3. SaleNo Null یک State معتبر Voucher است.
4. ConfirmDate به‌تنهایی اثبات Human Approval نیست.
5. SoldQty قدیمی منبع صدور نیست؛ Quantity reconciliation لازم است.
6. شماره سند فقط در سال مالی و مرکز توزیع یکتا است.
7. Route، Price، Rule و Customer Classification هنگام سند Snapshot می‌شوند.
8. Crosswalk NGT در سطح Line از Header کامل‌تر است و Split Order را می‌پذیرد.
9. تبدیل و ثبت باید Idempotent و دارای Audit Attempt باشد.
10. وب‌ERP جدید هیچ Write مستقیمی به وارانگار عملیاتی انجام نمی‌دهد؛ تا زمان
    Cutover، مسیر رسمی سرویس و تأیید انسانی حفظ می‌شود.

## Golden Caseهای لازم

1. سفارش تأییدنشده و تأییدشده بدون Sale؛
2. Order → Sale نهایی فعال؛
3. Voucher-only sale با `SaleNo=NULL`؛
4. Sale منتخب لغوشده و تلاش جایگزین؛
5. Split order NGT؛
6. Retry همان Command با Idempotency؛
7. لغو Order و لغو Sale به‌عنوان Eventهای جدا؛
8. شماره تکراری در سال/DC متفاوت؛
9. Crosswalk line معتبر با Header ناقص.

## ابهام‌های باز

- رفتار دقیق ۳۴٬۳۹۷ سفارش فعال با Sale منتخب لغوشده؛
- معنای عملی `ConfirmDate` و `ConfirmUserRef` در UI؛
- Rule کامل اثر موجودی برای هر OrderType؛
- علت هفت Split Order در NGT و قرارداد رسمی Split/Merge؛
- Crosswalk مقدار فاکتورشده NGT با SaleItem؛
- معنای ItemRef پرشده ولی نامنطبق در NGT؛
- Transition دقیق `Status 0→2→1/3` از Procedureهای تبدیل و توزیع؛
- Golden Case برای ایجاد، تبدیل، لغو، Retry و صدور فاکتور.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_order_sale_lifecycle_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\order_sale_lifecycle_20260826.json
```
