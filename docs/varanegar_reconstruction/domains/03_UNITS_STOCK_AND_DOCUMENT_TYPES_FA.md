# دامنه ۳: واحدها، نوع حمل/انبار و انواع سند وارانگار

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- سرور: `127.0.0.1`
- دیتابیس: `NeginPakhsh_WebDev`
- وضعیت: `READ_ONLY`
- حساب تحلیل: `Negin_Report_ReadOnly` با `UPDATE=0` و
  `db_denydatawriter=1`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/units_stock_and_document_types_20260826.json`

این مرحله ۱۲ جدول پایه، ۳۵ ارتباط FK رسمی، ۷۴۹ مصرف‌کننده ماژولی و ۴۰۲
ستون کاندید ارتباط ضمنی را بررسی کرده است. از کاندیدهای ضمنی، ۳۵۷ ستون FK
رسمی ندارند.

## نتیجه اصلی: یک Type عمومی نسازیم

وارانگار چند مفهوم هم‌نام ولی مستقل دارد:

```text
واحد فروش کالا             GNR.tblGoods.UnitRef     → GNR.tblUnit
واحد بسته‌بندی کالا        GNR.tblGoods.PackUnitRef → GNR.tblUnit
نوع سنجش فیزیکی            MeasurementUnitType / GeneralUnitType
کلاس دمایی حمل             GNR.tblShipType
نوع کانال/مدل انبار        Lookup ordinal و bit-mask عملیاتی
نوع عملیات سند انبار       GNR.tblLookup(CodeType=14)
نوع سفارش فروش             SLE.tblOrderType
نوع سند دفترکل             dbo.VoucherType
نوع مدرک پرسنلی            dbo.DocumentType
```

این مفاهیم در مدل مقصد نباید صرفاً به‌دلیل داشتن ستون‌های `Id/Title` در یک
جدول عمومی ادغام شوند.

## واحد کالا و بسته‌بندی

`GNR.tblUnit` دارای ۲۲ ردیف، PK روی `ID` و کلید یکتای `UnitCode` است. چهار
عنوان ابتدایی «کارتن»، «کارتن ۱»، «بسته» و «عدد» هستند؛ بخش بزرگی از بقیه
عنوان‌ها عدد بسته مانند ۶، ۷، ۱۰، ۲۴، ۴۸ و ۱۰۰ است. بنابراین این جدول Master
خالص واحد فیزیکی نیست و بخشی از قرارداد بسته‌بندی را نیز حمل می‌کند.

مصرف فعلی ۳٬۸۲۴ کالا:

| ستون | مقدار غالب | کالا |
|---|---|---:|
| `UnitRef` | ۳، «عدد» | ۳٬۸۲۲ |
| `UnitRef` | ۲، «بسته» | ۱ |
| `UnitRef` | ۵، عنوان «۷» | ۱ |
| `PackUnitRef` | ۰، «کارتن» | ۲٬۶۳۳ |
| `PackUnitRef` | ۱، «کارتن ۱» | ۱٬۱۹۱ |

هر سه ستون `MeasurementUnit`، `GeneralUnit` و `sdpmsMeasurementUnit` در تمام
۳٬۸۲۴ کالا خالی‌اند. دو جدول `dbo.MeasurementUnitType` و
`dbo.GeneralUnitType` هر کدام فقط سه ردیف هم‌عنوان دارند: «فله کیلویی»،
«لیتری» و «تعدادی». در Clone برای این دو جدول PK رسمی ثبت نشده است.

هیچ `UnitRef` یا `PackUnitRef` یتیم پیدا نشد.

## نوع حمل

| ID | عنوان | اولویت | مصرف کالا | مصرف انبار |
|---:|---|---:|---:|---:|
| ۱ | عادی | ۳۰ | ۳٬۸۲۰ | ۱۰ |
| ۲ | یخچالی | ۲۰ | ۰ | ۰ |
| ۳ | زیر صفر | ۱۰ | ۴ | ۰ |

هیچ ارجاع یتیم نوع حمل در کالا یا انبار وجود ندارد. «یخچالی» با وجود مصرف
صفر باید به‌عنوان مقدار معتبر Master حفظ شود؛ صفر بودن مصرف مجوز حذف نیست.

## دو نمایش ناسازگار نوع انبار

`GNR.vwStockType` پنج مقدار ترتیبی را از `GNR.tblLookup(CodeType=70)` برمی‌گرداند:

| کد ترتیبی | عنوان |
|---:|---|
| ۰ | پیش‌ویزیت |
| ۱ | فروش گرم |
| ۲ | انبارک |
| ۳ | فروش فروشگاهی |
| ۴ | ایستگاه کاری |

اما قرارداد `FRU.StockTypeModel` و `GNR.vwVocherStockType` از Bit Flag استفاده
می‌کند: `1, 2, 4, 8, 16` با همان ترتیب عنوان‌ها. `GNR.tblStockDC.StockType`
نیز در عمل Bit Flag است: ۹ انبار مقدار ۱ و انبار بسته‌بندی مقدار ۴ دارد.

تابع `GNR.HasStockType` عبارت `Power(2, Code-1)` را روی کدهای ترتیبی ۰ تا ۴
اعمال می‌کند. برای Code صفر این عبارت ۰٫۵ می‌شود و با قرارداد Bit Flag مشاهده‌شده
هم‌راستا نیست. این رفتار به‌عنوان **ابهام/احتمال خطای Legacy** ثبت می‌شود و
نباید بدون آزمون فرم و Runtime به وب منتقل شود.

قرارداد مقصد باید دو فیلد صریح داشته باشد:

- `stock_type_ordinal_code` فقط برای Crosswalk منبع Legacy؛
- `stock_type_flags` برای مقدار عملیاتی با اعتبارسنجی Bit Mask.

## انواع عملیات سند انبار

`GNR.tblLookup(CodeType=14)` تعداد ۳۰ نوع عملیات دارد و
`inv.tblVocherStockType` تعداد ۶۰ اتصال نوع عملیات به کانال انبار ثبت می‌کند.
نمونه‌های اصلی عبارت‌اند از افتتاحیه، رسید انبار، برگشت به انبار، برگشت حواله،
انباربه‌انبار بدهکار/بستانکار، تعدیل مثبت/منفی، رزرو، خروجی، ضایعاتی و معدومی.

هشت ردیف پل به دو کد ۳۵ و ۸۰ متصل‌اند که در Lookup فعلی وجود ندارند؛ هر کد
چهار بار برای Flagهای ۱، ۲، ۴ و ۸ آمده است. هیچ سند انبار تاریخی و هیچ سند در
پنجره سه‌ماهه برای این دو کد وجود ندارد. پس این‌ها «تنظیم Legacy بلااستفاده»
هستند، نه سند عملیاتی یتیم؛ تا تعیین نسخه/فرم مبدأ نباید حذف شوند.

## انواع سند و سفارش؛ چهار خانواده مستقل

| جدول | نقش واقعی | ردیف |
|---|---|---:|
| `dbo.DocumentType` | مدارک هویتی/پرسنلی | ۸ |
| `SLE.tblOrderType` | نوع سفارش فروش | ۲۳ |
| `dbo.POrderType` | نوع سفارش ثانویه | ۷ |
| `dbo.VoucherType` | نوع سند دفترکل | ۷۸ |
| `dbo.ExternalVoucherType` | نگاشت منبع بیرونی به سند دفترکل | ۶۵ |
| `Acc.ManualVoucherType` | نوع سند دستی حسابداری | ۱ |

`dbo.DocumentType` شامل صفحه‌های شناسنامه، گذرنامه، کارت ملی، دفترچه بیمه،
مدرک تحصیلی و طب کار است. بنابراین نام عمومی آن گمراه‌کننده است و نباید به
نوع فاکتور یا Voucher نگاشت شود.

در `SLE.tblOrderType`، ستون `Selectable` عملاً Boolean نیست و مقادیر ۰، ۱ و ۲
دارد؛ نوع‌های «فاکتور امانی» و «مرجوع امانی» مقدار ۲ دارند. همچنین ID=2 با
عنوان «پیش‌ویزیت» هم `IsDefault=1` و هم `IsFreeInvoice=1` دارد؛ معنای تجاری
این ترکیب باید از فرم سفارش و Stored Procedure مصرف‌کننده تأیید شود.

`dbo.ExternalVoucherType.VoucherTypeId` به `dbo.VoucherType` نگاشت می‌شود و
هیچ ارجاع یتیم در این نگاشت یا در ۲۰۵٬۹۴۴ سند دفترکل پیدا نشد.

## فعالیت سه ماه عملیاتی

مبنای این بخش تاریخ تجاری شمسی از `۱۴۰۵/۰۳/۰۱` تا `۱۴۰۵/۰۵/۳۱` است. تاریخ
ایجاد رکورد عمداً مبنا نیست: برای مثال `dbo.Voucher.CreatedDate` تازه از
۲۰۲۵-۰۹-۰۶ شروع می‌شود، درحالی‌که `VoucherDate` از `۱۴۰۳/۰۱/۰۱` داده دارد؛
این اختلاف شاهد Backfill/Migration است.

| خانواده | کل سند در پنجره |
|---|---:|
| سند انبار | ۱۲٬۲۶۲ |
| سفارش فروش | ۳۸٬۰۶۳ |
| سند دفترکل | ۸۸۷ |

پرتکرارترین انواع:

- انبار: برگشت حواله ۵٬۱۶۲، خروجی ۳٬۱۹۹، برگشت به انبار ۱٬۲۰۸،
  انباربه‌انبار بدهکار ۶۹۹ و بستانکار ۶۹۵.
- سفارش: پیش‌ویزیت ۲۰٬۰۲۹، پیش‌ویزیت تهران ۸٬۱۰۴، رسمی عادی ۳٬۶۵۱ و
  پیش‌ویزیت گیلان ۲٬۵۴۷.
- دفترکل: عمومی ۵۲۷، عمومی تأمین‌کننده ۱۵۶، سند پرداخت ۵۵، سند دریافت ۵۲،
  فروش ۴۹ و برگشت از فروش ۴۸.

این نتایج نشان می‌دهد نوع سند باید در مقصد به‌صورت خانواده‌محور تعریف شود و
Crosswalk هر خانواده جداگانه نسخه‌گذاری شود.

## کیفیت داده و کلیدها

- هیچ کالا با Unit، PackUnit یا ShipType یتیم وجود ندارد.
- هیچ سفارش با OrderType یتیم وجود ندارد.
- هیچ سند دفترکل یا نگاشت خارجی با VoucherType یتیم وجود ندارد.
- هیچ گروه ID/Code تکراری در Unit، ShipType، دو Lookup اصلی، OrderType یا
  VoucherType پیدا نشد.
- `SLE.tblOrderType` با وجود استفاده گسترده، PK رسمی ندارد؛ ID باید در مقصد
  به‌عنوان `source_id` حفظ شود اما یکتایی آن در هر Snapshot نیز کنترل شود.

## قرارداد اولیه مدل مقصد

حداقل موجودیت‌های مستقل:

- `GoodsSalesUnit` و `GoodsPackageUnit` با یک Crosswalk مشترک به `tblUnit`؛
- `PhysicalMeasurementUnit` و `GeneralUnit`؛
- `ShippingTemperatureClass`؛
- `StockChannel` با `legacy_ordinal_code` و `operational_bit` جدا؛
- `InventoryVoucherType` و پل `InventoryVoucherTypeStockChannel`؛
- `SalesOrderType`؛
- `GeneralLedgerVoucherType` و `ExternalVoucherTypeMapping`؛
- `PersonnelAttachmentType`؛
- `SecondaryOrderType` تا زمان تعیین مصرف واقعی آن.

برای همه موجودیت‌ها باید `source_system`، `source_table`، `source_id`، عنوان
خام منبع، وضعیت فعال/قابل‌انتخاب، زمان Snapshot و Crosswalk نسخه‌دار ذخیره شود.
حذف نرم یا غیرفعال‌سازی باید جای حذف مقادیر بلااستفاده را بگیرد.

## ابهام‌های باز

1. معنای دقیق `Selectable=2` در فرم سفارش.
2. علت `IsFreeInvoice=1` برای OrderType پیش‌ویزیت پیش‌فرض.
3. رفتار واقعی `GNR.HasStockType` در فرم‌ها و امکان وجود Workaround در کد .NET.
4. منشأ کدهای VoucherType ۳۵ و ۸۰ در پل، با وجود نبود Lookup و سند.
5. نقش عملیاتی `dbo.POrderType` نسبت به `SLE.tblOrderType`.

## Golden Caseهای لازم

1. یک Unit در نقش فروش و بسته‌بندی؛
2. Stock channel ordinal در برابر operational bit؛
3. OrderType با `Selectable=2`؛
4. VoucherType خارجی با نگاشت معتبر؛
5. VoucherType پل بدون سند جاری؛
6. شماره/نوع سند در خانواده‌های انبار، سفارش و دفترکل بدون ادغام اشتباه.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_units_documents_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\units_stock_and_document_types_20260826.json
```
