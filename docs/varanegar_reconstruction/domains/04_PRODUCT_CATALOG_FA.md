# دامنه ۴: کالا، گروه، برند، بسته‌بندی و بارکد وارانگار

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- سرور: `127.0.0.1`
- دیتابیس: `NeginPakhsh_WebDev`
- وضعیت: `READ_ONLY`
- حساب تحلیل: `Negin_Report_ReadOnly` با `UPDATE=0` و
  `db_denydatawriter=1`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/product_catalog_20260826.json`

این مرحله ۱۷ جدول، ۱۸۶ ارتباط FK رسمی، ۱٬۹۷۲ مصرف‌کننده ماژولی و ۳۲۸ کاندید
ارتباط ضمنی را بررسی کرده است. ۲۱۴ کاندید FK رسمی ندارند.

## نتیجه اصلی: سه طبقه‌بندی موازی کالا

هر کالا هم‌زمان در سه قرارداد طبقه‌بندی حضور دارد:

```text
GNR.tblGoods
  ├─ GoodsGroupRef ───────────────→ GNR.tblGoodsGroup
  ├─ BrandRef / ManufacturerRef ─→ Brand / Manufacturer
  ├─ GoodsMainSubType ────────────→ MainType / SubType
  └─ ProductMainGroupUniqueId
       + ProductSubGroupUniqueId ─→ NGT.ProductGroups
```

این مدل‌ها جایگزین یکدیگر نیستند:

- `GNR.tblGoodsGroup` یک Taxonomy عمومی با ریشه‌هایی مانند بهداشتی، غذایی،
  شوینده و پلیمری است.
- ریشه‌های فعال `NGT.ProductGroups` عمدتاً نام تجاری/لاین مانند راپیدو،
  کانفیدنت، اسپینو و میسویک دارند و فرزندانشان زیرگروه محصول همان لاین‌اند.
- `BrandRef` به Master برند GNR وصل است، اما با ریشه NGT رابطه یک‌به‌یک ندارد.
  ۳۳ برند به بیش از یک MainGroup و ۱۹ MainGroup به بیش از یک برند متصل‌اند.

پس Crosswalk باید از خود ۳٬۸۲۴ کالا ساخته شود؛ تطبیق نام برند و نام گروه NGT
برای مهاجرت کافی نیست.

## Master کالا

| شاخص | مقدار |
|---|---:|
| کالا | ۳٬۸۲۴ |
| دارای UUID | ۳٬۸۲۴ |
| `ShowInSale=1` | ۳٬۳۷۲ |
| `ShowInSale=0` | ۴۵۲ |
| `ShowInBuy=1` | ۰ |
| `ShowInBuy=0` | ۱٬۰۸۳ |
| `ShowInBuy=NULL` | ۲٬۷۴۱ |
| دارای MainGroup و SubGroup معتبر NGT | ۳٬۸۲۴ |

`GNR.tblGoods.ID` کلید اصلی، `GoodsCode` کلید یکتا و `UniqueId` در Snapshot
فعلی کامل و بدون تکرار است. از آنجا که `ShowInBuy` هیچ مقدار True ندارد، این
ستون به‌تنهایی منبع معتبر «قابل خرید بودن کالا» نیست.

Masterهای وابسته:

| جدول | نقش | ردیف |
|---|---|---:|
| `GNR.tblGoodsGroup` | گروه‌بندی Legacy | ۱۷۰ |
| `GNR.tblBrand` | برند | ۱۳۰ |
| `GNR.tblManufacturer` | تولیدکننده | ۷۱ |
| `GNR.tblGoodsType` | نوع داخلی کالا | ۴ |
| `GNR.tblMainType` | طبقه اصلی Legacy | ۱۶ |
| `GNR.tblSubType` | زیرطبقه Legacy | ۲۴۴ |
| `GNR.tblGoodsMainSubType` | پل کالا/طبقه | ۱۵٬۰۳۳ |

تمام ۳٬۸۲۴ کالا `GoodsTypeRef=1` با عنوان «بسته‌بندی» دارند؛ سه نوع «فله دو
واحدی»، «فله تک‌واحدی» و «خدمات» فعلاً مصرف ندارند، اما مقدار معتبر Master
هستند و حذف نمی‌شوند.

## درخت گروه Legacy

`GNR.tblGoodsGroup` هم `ParentRef` دارد و هم Nested Set با `NLeft/NRight/NLevel`.
ده ریشه فعلی عبارت‌اند از آبنبات، بهداشتی، پلیمری، تبلیغاتی، سلولزی، شوینده،
غذایی، لوازم خودرو، لوازم سوختی و لوازم منزل.

- هیچ Parent یتیم وجود ندارد.
- هیچ بازه `NLeft>=NRight`، تداخل Parent/Child یا Level نامعتبر پیدا نشد.
- `NLeft` و `NRight` تکراری نیستند.
- ۳۹ گروه کالا مستقیم ندارند؛ برخی از آن‌ها گره میانی‌اند، بنابراین مصرف صفر
  مجوز حذف نیست.

## طبقه‌بندی MainType/SubType و بقایای تاریخی

پل `GNR.tblGoodsMainSubType` تعداد ۱۵٬۰۳۳ ردیف برای ۵٬۰۰۳ شناسه کالا دارد،
درحالی‌که Master فعلی فقط ۳٬۸۲۴ کالا دارد:

- ۱٬۳۳۵ ردیف مربوط به ۱٬۱۸۰ شناسه کالای حذف‌شده یا تاریخی است.
- فقط یک کالای فعلی هیچ ردیف MainType/SubType ندارد.
- MainType و SubType یتیم و Triplet تکراری پیدا نشد.

این ۱٬۳۳۵ ردیف نباید وارد FK اجباری دیتابیس جدید شوند. آن‌ها باید در
Quarantine/Audit مهاجرت نگهداری شوند تا سابقه حذف کالا روشن بماند.

## بسته‌بندی و تبدیل واحد

`GNR.tblPackage` تعداد ۸٬۲۳۸ ردیف برای تمام ۳٬۸۲۴ کالا دارد. این جدول تبدیل
`کالا × واحد × تعداد` است، نه بسته تخفیفی:

- Qty خالی، صفر یا منفی ندارد.
- ترکیب تکراری `GoodsRef + UnitRef + Qty` ندارد.
- هر کالا دقیقاً یک Default فروش، یک Default انبار و یک Default برگشت دارد.
- Barcode بسته در تمام ردیف‌ها خالی است.
- Statusهای ۰، ۱ و ۲ به‌ترتیب ۳٬۸۲۴، ۳٬۸۲۴ و ۵۹۰ ردیف دارند، اما معنای رسمی
  آن‌ها هنوز از فرم یا Stored Procedure تأیید نشده است؛ Status=0 نباید
  «غیرفعال» فرض شود.

در مقابل، `SLE.tblGoodsPackage` با ۸ Header و ۳۶ Item یک بسته ترکیبی
فروش/تخفیف است. این مفهوم باید با `ProductUnitPackage` جدا بماند.

## بارکد: برای Unique Constraint آماده نیست

بارکد در چهار سطح مشاهده شد:

| منبع | ردیف پر |
|---|---:|
| `GNR.tblGoods.Barcode` | ۳٬۶۴۱ |
| `GNR.tblGoods.Barcode2` | ۴۴ |
| `GNR.tblGoods.GTIN` | ۰ |
| `GNR.tblPackage.Barcode` | ۰ |
| `GNR.tblGoodsBarcode` | ۱۶ |

مشکلات داده‌ای:

- ۲۸۶ مقدار Barcode اصلی میان چند کالا مشترک است؛ حتی پس از حذف Sentinel صفر،
  ۲۸۵ گروه تکراری باقی می‌ماند.
- مقدار `0` برای ۵۷ کالا استفاده شده و Barcode واقعی نیست.
- ۲۶ مقدار غیرعددی وجود دارد؛ نمونه‌هایی شبیه Scientific Notation اکسل
  (`2/162...E+15`)، حروف میانی و فاصله انتهایی مشاهده شد.
- در جدول Barcode اضافی نیز یک مقدار میان دو کالا مشترک است.
- طول Barcode اصلی از ۱ تا ۲۰ کاراکتر متغیر است؛ ۳٬۴۱۹ مقدار طول ۱۳ دارند.

مدل مقصد باید مقدار خام، مقدار Trim/Normalized، نوع (`EAN13/GTIN/legacy/...`)،
وضعیت اعتبارسنجی و Source را جدا ذخیره کند. هیچ قید Unique سراسری قبل از
Reconciliation قابل اعمال نیست.

## مدل UUIDمحور NGT و کاتالوگ

```text
NGT.ProductGroups (دو سطح)
  └──< NGT.Catalogs
         └──< NGT.CatalogProducts

GNR.tblGoods.ProductMainGroupUniqueId ─→ NGT.ProductGroups.Id
GNR.tblGoods.ProductSubGroupUniqueId  ─→ NGT.ProductGroups.Id
NGT.CatalogProducts.ProductUniqueId   ─→ GNR.tblGoods.UniqueId  (ضمنی)
```

| شاخص | مقدار |
|---|---:|
| ProductGroup کل / فعال | ۵۸۹ / ۵۶۱ |
| Root کل / فعال | ۱۰۶ / ۹۹ |
| گروه پایین‌تر از سطح دوم | ۰ |
| MainGroup استفاده‌شده | ۹۹ |
| SubGroup استفاده‌شده | ۴۶۲ |
| Catalog کل / فعال | ۵۷۶ / ۵۷۴ |
| CatalogProduct | ۱٬۲۱۶ |

تمام کالاها به MainGroup و SubGroup معتبر وصل‌اند و Parent زیرگروه دقیقاً با
MainGroup کالا سازگار است. تمام CatalogProductها Catalog معتبر دارند.

از ۱٬۲۱۶ ردیف CatalogProduct، تعداد ۱٬۱۹۹ ردیف با
`GNR.tblGoods.UniqueId` تطبیق می‌کند. ۱۷ ردیف باقی‌مانده همگی
`ProductUniqueId=00000000-...` و `Number_ID=0` هستند؛ این‌ها Placeholder خالی‌اند،
نه Product خارجی معتبر. `CatalogProducts.Number_ID` برای هیچ ردیفی با
`tblGoods.ID` تطبیق نمی‌کند و نباید Crosswalk کالا شود.

## فعالیت سه ماه عملیاتی

مبنای فعالیت تاریخ تجاری شمسی `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` است:

| شاخص | مقدار |
|---|---:|
| کالای دارای هر نوع فعالیت | ۲٬۳۳۶ |
| دارای سفارش | ۲٬۰۹۲ |
| دارای فروش | ۲٬۰۹۰ |
| دارای گردش انبار | ۲٬۳۳۰ |
| ردیف سفارش | ۲۰۲٬۵۳۵ |
| ردیف فروش | ۲۶۱٬۴۷۱ |
| ردیف گردش انبار | ۲۰۲٬۶۳۸ |
| بدون هیچ فعالیت | ۱٬۴۸۸ |

از کالاهای `ShowInSale=1`، تعداد ۱٬۴۴۱ کالا در این پنجره هیچ فعالیتی ندارند؛
در مقابل ۴۰۵ کالای `ShowInSale!=1` فعالیت سفارش/فروش/انبار داشته‌اند. پس
`ShowInSale` وضعیت نمایش فعلی است و نباید جای تاریخچه فعالیت یا وضعیت حذف نرم
را بگیرد.

در ۹۰ روز منتهی به Snapshot، ۲۰۸ کالا، ۲۲۴ ProductGroup، ۴۰ Catalog و ۶۰
CatalogProduct تغییر Master داشته‌اند. این اعداد تغییر تنظیمات‌اند، نه میزان
فروش.

## کیفیت ارجاع

هیچ GoodsGroup، Brand، Manufacturer، GoodsType، Package، Unit، Barcode،
Supplier، Promotional Package یا NGT Parent یتیم برای Masterهای فعلی پیدا
نشد. کد کالا، UUID کالا، UUID گروه Legacy، نام برند و کد تولیدکننده نیز گروه
تکراری ندارند. تنها بدهی روشن، طبقه‌بندی‌های تاریخی کالاهای حذف‌شده و کیفیت
Barcode است.

## قرارداد اولیه مدل مقصد

موجودیت‌های مستقل پیشنهادی:

- `Product` با `source_id` و `source_uuid`؛
- `LegacyProductTaxonomyNode` با Parent و Nested-set snapshot؛
- `Brand` و `Manufacturer`؛
- `LegacyMainType / LegacySubType / ProductClassification`؛
- `NgtProductGroup` با Parent UUID؛
- `ProductGroupAssignment` نسخه‌دار برای Main/Sub؛
- `ProductUnitPackage` برای `tblPackage`؛
- `PromotionBundle / PromotionBundleItem` برای جداول SLE؛
- `ProductBarcodeAlias` با Raw/Normalized/Type/Validation؛
- `Catalog / CatalogProduct` با Crosswalk بر پایه UUID؛
- `MigrationQuarantine` برای ارجاع‌های تاریخی بدون Product فعلی.

Brand و NGT MainGroup باید Crosswalk مستقل چندبه‌چند داشته باشند. حذف کالا نیز
باید Soft Delete باشد تا طبقه‌بندی‌ها، سفارش‌ها و گردش‌های تاریخی قابل تطبیق
بمانند.

## ابهام‌های باز

1. معنای رسمی Statusهای ۰، ۱ و ۲ در `GNR.tblPackage`.
2. قاعده انتخاب Barcode اصلی در UI و POS میان چهار سطح Barcode.
3. منبع ایجاد ۱۷ Placeholder خالی در CatalogProducts.
4. منطق عملیاتی `ShowInSale` و دلیل فعالیت تاریخی ۴۰۵ کالای غیرقابل‌نمایش.
5. سیاست پاک‌سازی ۲۸۵ Barcode تکراری واقعی/مشترک میان SKUها.
6. ماهیت دقیق رابطه چندبه‌چند Brand و MainGroup تجاری NGT.

## Golden Caseهای لازم

1. کالا با Brand/Manufacturer/Main/Sub و NGT group معتبر؛
2. کالا با چند Package/Unit و تبدیل مقدار؛
3. Barcode یکتا، Barcode مشترک و Barcode نامعتبر؛
4. کالای حذف‌نرم‌شده با سند تاریخی؛
5. `ShowInSale=1` بدون فعالیت و Flag مخالف با فعالیت؛
6. Catalog placeholder بدون Product؛
7. Import مجدد با Source ID/UUID ثابت و بدون Duplicate.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_product_catalog_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\product_catalog_20260826.json
```
