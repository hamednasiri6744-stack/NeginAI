# دامنه ۲: جغرافیا و مسیرهای وارانگار

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- سرور: `127.0.0.1`
- دیتابیس: `NeginPakhsh_WebDev`
- وضعیت: `READ_ONLY`
- حساب تحلیل: `Negin_Report_ReadOnly` با `UPDATE=0` و `db_denydatawriter=1`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/geography_and_routes_20260826.json`

این مرحله ۲۲ جدول را بررسی کرده است: جغرافیای GNR، چهار خانواده مسیر قدیمی،
FRU و مسیرهای NGT.

## جغرافیای پایه

```text
GNR.tblState (استان)
  └──< GNR.tblCounty (شهرستان)
         └──< GNR.tblArea (Area؛ عنوان دقیق UI هنوز باز است)
                └──< GNR.tblDCDependency >── GNR.tblDC
```

| جدول | نقش | رکورد |
|---|---|---:|
| `GNR.tblState` | استان | ۳۱ |
| `GNR.tblCounty` | شهرستان | ۴۰ |
| `GNR.tblArea` | شهر/ناحیه پایه | ۶۹ |
| `GNR.tblDCDependency` | اتصال مرکز به Area | ۳۱ |

هیچ County بدون State، هیچ Area بدون County و هیچ اتصال مرکز بدون Area معتبر
پیدا نشد. کد State، کد County درون State و کد Area درون County نیز گروه تکراری
ندارند.

## پوشش مرکز عملیاتی

هر ۳۱ ردیف `GNR.tblDCDependency` به `DCRef=1` و `Status=1` متصل است:

| استان | Area متصل به مرکز |
|---|---:|
| گیلان | ۱۶ |
| البرز | ۱۳ |
| تهران | ۱ |
| قزوین | ۱ |

مقدار `Distance` در تمام ردیف‌ها صفر است. بنابراین این ستون در داده فعلی
«فاصله واقعی» را اثبات نمی‌کند و نباید مبنای مسیریابی یا کنترل GPS قرار گیرد.

## خانواده‌های مسیر قدیمی

وارانگار چهار سلسله‌مراتب مستقل و هم‌شکل دارد:

```text
Sales:       SaleZone → SaleArea → SalePath
Distribution: DistZone → DistArea → DistPath
Collection:   RcptZone → RcptArea → RcptPath
Telephone:    TeleZone → TeleArea → TelePath
```

| خانواده | Zone | Area | Path |
|---|---:|---:|---:|
| فروش | ۲ | ۵ | ۱۴۶ |
| توزیع | ۰ | ۰ | ۰ |
| وصول | ۰ | ۰ | ۰ |
| فروش تلفنی | ۰ | ۰ | ۰ |

مسیر فروش فعال به این شکل توزیع شده است:

- Zone «شعبه البرز»: Line مارکت با ۱۳۸ مسیر، Line داروخانه با ۱ مسیر، Line
  زنجیره‌ای با ۶ مسیر و Line عمده بدون مسیر ثبت‌شده.
- Zone «شعبه گیلان»: یک Area و یک مسیر.
- هیچ Zone بدون مرکز، SaleArea بدون Zone یا SalePath بدون SaleArea پیدا نشد.
- شماره Zone در هر مرکز، شماره Area در هر Zone و شماره Path در هر Area تکراری
  نیست.

## اتصال مشتری به جغرافیا و مسیر

`GNR.tblCust` هم‌زمان چند نوع مرجع دارد:

- `StateRef → GNR.tblState`
- `AreaRef → GNR.tblArea`
- `SalePathRef → GNR.tblSalePath`
- `DistPathRef → GNR.tblDistPath`
- `RcptPathRef → GNR.tblRcptPath`
- `TelePathRef` بدون FK رسمی مشاهده‌شده
- `CityZone` و `CityArea` بدون جدول مرجع یا FK اثبات‌شده

| پوشش روی ۴۴٬۸۲۹ مشتری | تعداد | درصد تقریبی |
|---|---:|---:|
| دارای State | ۴۲٬۴۶۲ | ۹۴٫۷٪ |
| دارای Area | ۴۰٬۹۲۵ | ۹۱٫۳٪ |
| دارای مسیر فروش قدیمی | ۸٬۶۵۷ | ۱۹٫۳٪ |
| دارای مسیر توزیع | ۰ | ۰٪ |
| دارای مسیر وصول | ۰ | ۰٪ |
| دارای مسیر تلفنی | ۰ | ۰٪ |

تمام State، Area و SalePathهای مقداردهی‌شده مشتری به رکورد معتبر وصل شدند.

`CityZone` برای ۱۳٬۸۷۱ مشتری مقدار دارد و ۳۰ مقدار متمایز مشاهده شد؛ مقدار صفر
به‌تنهایی برای ۷٬۷۷۲ مشتری استفاده شده است. چون جدول مرجع پیدا نشد و مقادیر آن
با دو SaleZone فعلی هم‌خوان نیست، تبدیل آن به `SaleZone` ممنوع است. `CityArea`
فقط برای یک مشتری مقدار دارد و آن هم فعلاً داده Legacy مبهم محسوب می‌شود.

## مدل مسیر جدید NGT

```text
NGT.VisitTemplates
  └──< NGT.VisitTemplatePaths
         └──< NGT.VisitTemplatePathCustomers

NGT.DayPaths → NGT.VisitTemplatePaths
```

| شاخص | مقدار |
|---|---:|
| VisitTemplate کل / فعال | ۵۰۷ / ۱۹۲ |
| VisitTemplatePath کل / فعال | ۴٬۷۲۵ / ۲٬۵۵۰ |
| اتصال Path/Customer فعال | ۸۷٬۹۳۵ |
| مشتری متمایز در اتصال‌های فعال | ۳۷٬۲۴۸ |
| DayPath کل / فعال | ۱ / ۰ |
| `FRU.Path` و `FRU.DayPath` | هر دو خالی |

در ۹۰ روز منتهی به زمان استخراج، `LastUpdate` برای ۲۰۱ Template، ۲٬۲۰۵ Path و
۵۲٬۱۳۵ اتصال Path/Customer تغییر کرده است. این عدد فقط تغییر Master Data را
نشان می‌دهد و شاهد انجام ویزیت یا اجرای تور نیست.

## هشدار مهم درباره نگاشت قدیم و NGT

در ۲٬۵۵۰ ردیف فعال NGT فقط ۲۷ مقدار متمایز `Number_ID` وجود دارد. از این ۲۷
مقدار، ۲۴ مقدار با `GNR.tblSalePath.ID` تطبیق می‌کنند؛ اما فقط ۳۷ ردیف NGT در
این تطبیق قرار می‌گیرند. مقادیر نامنطبق عبارت‌اند از:

| `Number_ID` | ردیف فعال |
|---:|---:|
| ۰ | ۲٬۵۰۶ |
| ۱ | ۶ |
| ۱۰ | ۱ |

پس `Number_ID` به‌تنهایی کلید مهاجرت یا Crosswalk معتبر نیست. نگاشت باید با
ترکیب Template، Path title، مالک داده، مشتریان متصل، UUID و شواهد API رسمی
ساخته شود.

## دامنه اثر و ارتباط‌های ضمنی

- ۱۰۵ FK رسمی پیرامون ۲۲ جدول این مرحله ثبت شد.
- ۱٬۱۲۰ ماژول SQL مستقیماً به یکی از این جدول‌ها وابسته‌اند.
- ۶۱۰ ستون کاندید نام جغرافیا/مسیر در سایر جدول‌ها پیدا شد.
- ۵۶۸ مورد از این ستون‌ها FK رسمی ندارند و باید قبل از مهاجرت مصرف‌کننده‌محور
  بررسی شوند.

پرمصرف‌ترین منابع متادیتایی `GNR.tblArea` با ۲۳۶، `GNR.tblState` با ۱۳۹،
`GNR.tblCounty` با ۱۳۱ و سه جدول مسیر فروش با مجموع ۲۶۴ مصرف‌کننده‌اند.

## قرارداد اولیه مدل مقصد

مدل جدید باید این مفاهیم را جدا نگه دارد:

- `State`
- `County`
- `Area` با عنوان موقت تا تأیید UI
- `OperationalCenterArea`
- `LegacySalesZone / LegacySalesArea / LegacySalesPath`
- خانواده‌های مستقل Distribution، Collection و Telephone، حتی اگر فعلاً خالی‌اند
- `VisitTemplate / VisitTemplatePath / VisitTemplatePathCustomer`
- Crosswalk صریح و نسخه‌دار میان مسیر قدیمی و NGT

تمام موجودیت‌ها باید `source_system`، `source_table`، `source_id` یا
`source_uuid`، وضعیت حذف نرم و زمان آخرین تطبیق داشته باشند. خانواده‌های مسیر
نباید صرفاً به‌دلیل شباهت ستون‌ها در یک جدول بدون `route_family` و قرارداد مبدأ
ادغام شوند.

## ابهام‌های باز

1. عنوان رسمی `GNR.tblArea` در فرم وارانگار: شهر، ناحیه یا Area.
2. معنای Legacy و منبع کدهای `CityZone` و `CityArea` مشتری.
3. قرارداد واقعی Crosswalk میان مسیر فروش GNR و مسیرهای NGT.
4. دلیل خالی بودن مسیرهای توزیع و وصول در حالی که عملیات توزیع/وصول وجود دارد.
5. تفاوت ۴۴٬۸۲۹ مشتری Legacy با ۳۷٬۲۴۸ مشتری متمایز در Pathهای فعال NGT.

## Golden Caseهای لازم

1. State/County/Area سالم با Parent chain کامل؛
2. مسیر Legacy فعال با مشتری؛
3. مسیر NGT با UUID و چند مشتری؛
4. `Number_ID=0` بدون Crosswalk حدسی؛
5. مشتری در چند Path/Template؛
6. Route family خالی ولی Capability محفوظ؛
7. Crosswalk نسخه‌دار که با تغییر مالک مسیر قابل بازسازی است.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_geography_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\geography_and_routes_20260826.json
```
