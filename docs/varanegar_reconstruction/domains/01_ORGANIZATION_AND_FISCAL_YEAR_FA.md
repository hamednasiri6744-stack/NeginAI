# دامنه ۱: ساختار سازمانی و سال مالی وارانگار

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- سرور: `127.0.0.1`
- دیتابیس: `NeginPakhsh_WebDev`
- وضعیت دیتابیس هنگام استخراج: `READ_ONLY`
- حساب: `Negin_Report_ReadOnly`
- دسترسی حساب: `SELECT=1`، `VIEW DEFINITION=1`، `UPDATE=0` و
  `db_denydatawriter=1`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/organization_and_fiscal_year_20260826.json`

## موجودی جدول‌های هسته

| نقش | جدول | PK | رکورد | ستون | Trigger |
|---|---|---|---:|---:|---:|
| مرکز توزیع/حوزه عملیاتی | `GNR.tblDC` | `ID` | ۲ | ۲۸ | ۶ |
| دفتر فروش | `GNR.tblSaleOffice` | `ID` | ۱ | ۱۸ | ۳ |
| انبار/مرکز موجودی | `GNR.tblStockDC` | `ID` | ۱۰ | ۱۷ | ۵ |
| پل مرکز، دفتر فروش و انبار | `GNR.tblDCSaleOffice` | `ID` | ۱۰ | ۵ | ۴ |
| اتصال مرکز به ناحیه | `GNR.tblDCDependency` | `ID` | ۳۱ | ۵ | ۳ |
| سال عملیاتی | `GNR.tblAccYear` | `ID` | ۳ | ۸ | ۵ |
| سال مالی دفترکل | `dbo.FiscalYear` | `FiscalYearId` | ۳ | ۱۳ | ۵ |
| پل مرکز و سال مالی | `dbo.DCFiscalYear` | `DCFiscalYearId` | ۳ | ۱۳ | ۱ |

## نقشه روابط مستقیم

```text
GNR.tblDC (مرکز)
  ├──< GNR.tblStockDC (انبار)
  ├──< GNR.tblDCSaleOffice >── GNR.tblSaleOffice
  │                         └── GNR.tblStockDC
  ├──< GNR.tblDCDependency >── GNR.tblArea
  └──< dbo.DCFiscalYear >───── dbo.FiscalYear

GNR.tblAccYear
  └── مدل سال عملیاتی مستقل؛ مصرف‌کننده‌های آن الزاماً از FiscalYearId استفاده نمی‌کنند
```

در محدوده این هشت جدول، ۲۱۶ FK رسمی پیدا شد. تعداد FKهایی که از کل سامانه به
مراجع اصلی این حوزه می‌رسند:

| مرجع | تعداد FK رسمی |
|---|---:|
| `GNR.tblDC` | ۱۰۶ |
| `GNR.tblStockDC` | ۴۳ |
| `GNR.tblSaleOffice` | ۳۰ |
| `GNR.tblDCSaleOffice` | ۱۲ |
| `GNR.tblAccYear` | ۶ |
| `dbo.FiscalYear` | ۵ |

علاوه بر این، ۵۳۰ ستون با نام‌هایی مانند `DCRef`، `DCId`، `StockDCRef`،
`SaleOfficeRef`، `AccYear` و `FiscalYearId` بدون FK رسمی ثبت شده‌اند. این موارد
فعلاً «کاندید ارتباط ضمنی» هستند و نه رابطه قطعی.

## تصویر فعلی اطلاعات

### مرکزها

| ID | کد | نام | دسته | وضعیت |
|---:|---:|---|---:|---:|
| ۰ | ۰ | ستاد مرکز | ۰ | ۱ |
| ۱ | ۲۶ | تهران و البرز و قزوین | ۱ | ۱ |

### دفتر فروش و انبار

- یک دفتر فروش فعال با `ID=1` وجود دارد.
- ده انبار با `ID=1..10` وجود دارد و همه به `DCRef=1` متصل‌اند.
- `GNR.tblDCSaleOffice` هر ده انبار را به همان `DCRef=1` و
  `SaleOfficeRef=1` متصل می‌کند.
- نوع انبار ۹ انبار `StockType=1` و انبار بسته‌بندی `StockType=4` است.
- نام‌های مشاهده‌شده شامل انبار مرکزی، تهران، قیمت قدیم مرکزی/تهران، نمونه
  کالا کرج، کسری مرکزی، آنلاین، بسته‌بندی، گیلان و نمونه گیلان است.
- هیچ‌کدام از ده انبار اجازه موجودی یا کاردکس منفی ندارند.

### سال‌ها

| سال | `GNR.tblAccYear.ID` | `dbo.FiscalYear.FiscalYearId` | `dbo.DCFiscalYear.DCId` |
|---:|---:|---:|---:|
| ۱۴۰۳ | ۱ | ۲ | ۰ |
| ۱۴۰۴ | ۳ | ۳ | ۰ |
| ۱۴۰۵ | ۴ | ۴ | ۰ |

سه نتیجه قطعی:

1. `AccYear` و `FiscalYearId` دو مفهوم/شناسه مستقل‌اند؛ برای سال ۱۴۰۳ حتی مقدار
   شناسه آن‌ها متفاوت است.
2. سال‌های مالی در `dbo.DCFiscalYear` به `DCId=0` یعنی ستاد مرکز متصل‌اند.
3. انبارها و دفتر فروش عملیاتی به `DCRef=1` متصل‌اند؛ بنابراین نگاشت ساده
   «هر DC همان شعبه است» معتبر نیست.

## دامنه اثر

وابستگی متادیتای SQL برای این هشت جدول ۲۲۷۸ مصرف‌کننده ماژولی ثبت کرده است:

| منبع | تعداد View/Procedure/Function/Trigger مصرف‌کننده |
|---|---:|
| `GNR.tblDC` | ۶۵۵ |
| `GNR.tblStockDC` | ۵۲۴ |
| `GNR.tblAccYear` | ۴۰۱ |
| `GNR.tblDCSaleOffice` | ۳۵۹ |
| `GNR.tblSaleOffice` | ۲۱۸ |
| `dbo.FiscalYear` | ۶۷ |
| `GNR.tblDCDependency` | ۳۲ |
| `dbo.DCFiscalYear` | ۲۲ |

پس این دامنه فقط یک صفحه اطلاعات پایه نیست؛ کل فروش، خزانه، انبار، عملیات
میدانی، دسترسی کاربران و گزارش‌ها به آن متصل‌اند.

## قرارداد اولیه مدل مقصد

مدل جدید باید حداقل این Entityها را جدا نگه دارد:

- `Company`
- `OperationalCenter`
- `SalesOffice`
- `Warehouse`
- `CenterSalesOfficeWarehouse`
- `OperationalYear`
- `FiscalYear`
- `CenterFiscalYear`
- `CenterArea`

هر رکورد مهاجرتی باید `source_system`، `source_table`، `source_id` و زمان آخرین
تطبیق را داشته باشد. تبدیل مستقیم `DCRef` به «شعبه» یا یکی‌کردن `AccYear` با
`FiscalYearId` ممنوع است تا معنای هر مصرف‌کننده جداگانه تأیید شود.

## ابهام‌های باز

1. جدول مرجع و پرشده «شرکت» هنوز پیدا نشده است. `NGT.CompanyCenters` و
   `dbo.DRGenSetting` خالی‌اند؛ تک‌شرکتی بودن دیتابیس فقط یک فرضیه است.
2. معنای رسمی `DCCategory`، `Status`، `StockType` و `ShipTypeRef` باید از
   جداول کد/فرم‌های مصرف‌کننده استخراج شود.
3. باید با اسناد سه ماه گذشته ثابت شود کدام‌یک از ده انبار واقعاً فعال‌اند.
4. دلیل تاریخی اختلاف شناسه سال ۱۴۰۳ بین دو مدل سال هنوز روشن نیست.
5. نقش دقیق `DC=0` در مالی و `DC=1` در عملیات باید با نمونه سند و گزارش رسمی
   تطبیق داده شود.

## Golden Caseهای لازم

1. سال ۱۴۰۳ با `AccYear.ID` و `FiscalYearId` متفاوت؛
2. DC مالی صفر در برابر DC عملیاتی یک؛
3. دفتر فروش با چند StockDC؛
4. StockDC غیرفعال ولی دارای تاریخچه؛
5. Import دوباره همان Snapshot بدون رکورد تکراری؛
6. Ref سازمانی نامنطبق در Quarantine، نه نگاشت حدسی.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_org_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\organization_and_fiscal_year_20260826.json
```
