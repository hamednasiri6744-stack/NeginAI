# مرز OperationDate بازگشت NGT و انتخاب تاریخ Replication

تاریخ بررسی: ۲۰۲۶-۰۸-۲۹  
وضعیت: **تأیید ایستا روی چهار Assembly مستقر + Catalog/SQL/Aggregate روی Clone فقط‌خواندنی؛ اجرای Runtime و ادعای رخداد عملیاتی ندارد**

## نتیجه‌ی اصلی

در ورانگار سه مفهوم متفاوت با نام‌های نزدیک وجود دارد و در ERP آینده نباید در
یک فیلد ادغام شوند:

1. `NGT.CustomerCallReturns.OperationDate`: زمان رویداد/درخواست بازگشت در مدل NGT؛
2. `CustomerCallDateBasedOnUniqueId`: تنظیمی که منبع تاریخ سند در Replication را انتخاب می‌کند؛
3. `GNR.tblOprDate`: مرز باز/بسته و تاریخ فعال سیستم برای DC، سال مالی و زیرسیستم.

شباهت نام، رابطه‌ی یک‌به‌یک ایجاد نمی‌کند. فقط در یکی از شاخه‌ها تاریخ رویداد
NGT به تاریخ خروجی کپی می‌شود و حتی آن شاخه در پیاده‌سازی Business و SQL منبع
یکسانی را ثابت نمی‌کند.

## دامنه و ایمنی

- چهار فایل `NGT.Common.dll`، `NGT.Business.dll`، `NGT.DataAccess.dll` و
  `NGT.WebApi.dll` فقط با PE metadata و IL خوانده شدند؛ Assembly بارگذاری یا
  اجرا نشد؛
- ۲۷٬۷۸۸ بدنه متد بررسی و ۶۴۳ متد سیگنال‌دار انتخاب شد؛ سه خطای Parse وجود
  داشت ولی هیچ‌کدام نام مرتبط با این مرز نداشت؛
- Clone در حالت `READ_ONLY`، با `UPDATE=0` و `db_denydatawriter=1` بود؛
- Procedure، Endpoint، فرم و Command اجرا نشد؛
- UUID تنظیم، هویت، مشتری، شماره سند یا ردیف خام در Artifact ذخیره نشده است؛
- تنها نام‌های معنایی غیرمحرمانه‌ی چهار گزینه‌ی BaseValue ذخیره شده‌اند.

## قرارداد Schema و داده‌ی جاری

| مدل | نوع/Null | Default | جمعیت جاری |
|---|---|---|---:|
| `NGT.CustomerCallReturns.OperationDate` | `datetime NOT NULL` | `1900-01-01` | ۲ |
| `FRU.CustomerCallReturns.OperationDate` | `datetime NOT NULL` | ندارد | ۰ |

در Snapshot جاری:

- هر دو Header فعال‌اند؛
- مقدار Sentinel سال ۱۹۰۰ و تاریخ آینده صفر است؛
- هر دو `OperationDate` در همان روز تقویمی `CreatedDate` قرار دارند؛
- Crosswalk دقیق `NGT.Number_ID → FRU.Id` صفر است؛ بنابراین برابری ردیفی تاریخ
  دو مدل موبایل قابل ادعا نیست؛
- روی دو جدول هیچ Trigger وجود ندارد و هیچ Check Constraint مرتبط با
  `OperationDate` پیدا نشد.

## دو مسیر ورود OperationDate

### SaveTourData

IL متد async `TourDomain.SaveTourData` مقدار `OperationDate` را با
`default(DateTime)` مقایسه و در حالت برابر Exception ایجاد می‌کند. پس مسیر
Business مقدار خالی .NET را رد می‌کند و سپس شناسه‌ی CustomerCall را روی Return
قرار می‌دهد.

### AddDistributionTour

در `TourDomain.AddDistributionTour` یک `DateTime.Now` در فیلد Captureشده‌ی
`now` قرار می‌گیرد. Lambda ساخت Return همان مقدار را برای `ReturnStartTime`،
`ReturnEndTime` و `OperationDate` و همچنین زمان‌های ایجاد/آخرین تغییر مصرف می‌کند.

مرز مهم این است که Guard برنامه `DateTime.MinValue` را رد می‌کند، ولی Default
مستقل SQL مقدار ۱۹۰۰ است. Insert مستقیم، Migration یا مسیر دیگری که ستون را
حذف کند می‌تواند بدون Check Constraint مقدار ۱۹۰۰ بسازد. دو ردیف جاری چنین
مشکلی ندارند، اما طراحی مقصد باید Guard را در Persistence نیز قطعی کند.

## تنظیم انتخاب تاریخ

یک ردیف فعال `NGT.AppSettings` وجود دارد. FK آن به `NGT.BaseValues` دقیق Match
می‌شود، مقدار Null یا Removed نیست و گزینه‌ی جاری چنین است:

- نام: `تاريخ درخواست`
- نام کدی: `CallDate`

چهار گزینه‌ی مستقر:

| نام کدی | نام معنایی DB | Business IL | `dbo.NGT_DoReplicateTour` |
|---|---|---|---|
| `CallDate` | تاريخ درخواست | شاخه‌ی Override صریح دیده نشد؛ منبع اولیه‌ی `ReturnDate` هنوز اثبات نشده | `CallPDate` |
| `OperationDate` | تاريخ عمليات | `NGT Return.OperationDate → ReturnDate` | `CallPDate` با fallback به `TourPDate` |
| `ServerDate` | تاریخ سرور پخش | `DateTime.Now` با قالب Server Culture | `@ToDay` از تاریخ سرور |
| `ActiveDate` | تاریخ جاری پخش | تاریخ Active بازیابی‌شده از BackOffice | `GNR.tblOprDate.OprDate` بازِ فروش |

برای شاخه‌ی `ActiveDate` در SQL، انتخاب `tblOprDate` با این مرزهاست:

- `SysRef=1` (فروش)؛
- `IsClosed=0`؛
- `OprDate > LastDate` یا `LastDate IS NULL`؛
- DC و سال مالی از Context جاری محاسبه می‌شوند.

پس `ActiveDate` از نظر مفهوم احتمالاً همان تاریخ فعال BackOffice است، اما
برابری دقیق Retriever کد و Query SQL هنوز اثبات نشده. اختلاف روشن‌تر در
`OperationDate` است: Business مقدار datetime خود Return را کپی می‌کند، ولی SQL
از تاریخ فعالیت Call/Tour استفاده می‌کند. این دو ممکن است در روزهای عادی برابر
باشند، اما این برابری قرارداد یا Guard نیست.

## رفتار Null و گزینه ناشناخته

- Business IL فقط `OperationDate`، `ActiveDate` و `ServerDate` را Override
  می‌کند؛ `CallDate` یا مقدار ناشناخته از شاخه‌ها عبور می‌کند؛
- در `dbo.NGT_DoReplicateTour` سه عبارت CASE برای همین Selector وجود دارد و هر
  سه بدون `ELSE` هستند؛ مقدار Null/ناشناخته می‌تواند نتیجه Null بسازد؛
- گزینه‌ی جاری معتبر است، بنابراین رخداد جاری از این ساختار نتیجه‌گیری نمی‌شود.

## سطح مصرف SQL

یازده SQL module هم‌زمان به خانواده CustomerCallReturn و یکی از مفاهیم تاریخ
مرتبط‌اند؛ پنج مورد به `tblOprDate` نیز اشاره دارند. مهم‌ترین مورد
`dbo.NGT_DoReplicateTour` است که Transaction و TRY/CATCH دارد و چهار منبع بالا
را انتخاب می‌کند. وجود Transaction، اختلاف معنای منبع تاریخ را حل نمی‌کند؛
Decision باید پیش از اثر مالی/انبار قطعی و قابل توضیح باشد.

## ریسک ثبت‌شده

`R-060` با شدت High ثبت شد: «رانش معنای انتخاب‌گر تاریخ Replication بین مسیر
Business و SQL». این ریسک وقوع خرابی فعلی را ادعا نمی‌کند. خطر طراحی آن است که
نسخه وب فقط یکی از دو رفتار را تقلید کند، یا `OperationDate` رویداد را با تاریخ
فعال/بسته‌شدن سیستم یکی بگیرد و سند را در روز یا سال مالی نادرست ثبت کند.

## قرارداد پیشنهادی ERP شخصی

حداقل فیلدهای مستقل:

- `event_occurred_at` با Timezone و منبع Device/Server؛
- `call_activity_date` و `tour_activity_date` به‌عنوان تاریخ‌های کسب‌وکاری؛
- `replication_document_date` به‌عنوان نتیجه‌ی Decision؛
- `replication_date_source` از Enum تایپ‌شده؛
- `effective_setting_version` و دلیل انتخاب؛
- `open_operation_date_snapshot` با DC، FiscalYear، System و Policy version؛
- `created_at` و `imported_at` مستقل از تاریخ کسب‌وکاری.

قواعد:

1. Selector Null، Removed یا ناشناخته قبل از هر Write، Fail Closed شود؛
2. مقدار ۱۹۰۰/خارج از دامنه فقط در Quarantine مهاجرت مجاز باشد؛
3. هر چهار گزینه در یک سرویس تصمیم واحد پیاده‌سازی شوند؛ SQL و Application
   پیاده‌سازی موازی نداشته باشند؛
4. سند خروجی منبع تاریخ و نسخه تنظیم مؤثر را ثبت کند؛
5. تست‌های Golden برای اختلاف Call/Tour/Event/Server/OpenDate و مرز سال مالی و
   تاریخ بسته اجرا شوند.

## محدودیت

- هیچ Request واقعی، Payload موبایل، Procedure یا Command اجرا نشده است؛
- IL شکل کد را ثابت می‌کند، نه مقدار دو Request تاریخی را؛
- Clone جاری FRU و Crosswalk ندارد و مقایسه‌ی ردیفی دو موتور ممکن نیست؛
- مسیر مقداردهی اولیه `ReturnDate` برای شاخه‌ی بدون Override در Business IL
  هنوز با قطعیت بسته نشده است؛
- Production configuration parity و رفتار نسخه‌های دیگر NGT ادعا نمی‌شود.

## بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_ngt_operation_date_boundary.py `
  --source-directory "\\192.168.1.171\exe\NGTApp\Server\bin" `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_operation_date_boundary_20260829.json

G:\NeginAI\scripts\windows\rebuild_negin_erp_risk_and_traceability.ps1 `
  -IncludeNgtAuthorization
```

منابع ماندگار:

- `scripts/sql/extract_varanegar_ngt_operation_date_boundary.py`
- `artifacts/varanegar_analysis/domains/ngt_operation_date_boundary_20260829.json`
- `artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json`
- `artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json`
