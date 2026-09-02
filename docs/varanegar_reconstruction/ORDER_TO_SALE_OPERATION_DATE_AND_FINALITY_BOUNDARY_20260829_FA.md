# مرز تاریخ عملیات و قطعیت در تبدیل سفارش به فروش

تاریخ استخراج: ۲۰۲۶-۰۸-۲۹  
وضعیت: **SQL Clone فقط‌خواندنی + IL ایستای Hash-pinned؛ اجرای عملیاتی صفر**

## نتیجهٔ کوتاه

تاریخ فروش در مسیر تبدیل سفارش یک مقدار نمایشی یا صرفاً تاریخ سیستم نیست. دو مسیر
گروهی فرم سفارش، مقدار `OperationdDate_Sale` را از Session می‌خوانند و به‌عنوان
`CreateSaleDate` به فرمان تبدیل می‌دهند. Wrapper آن را به هسته می‌فرستد و هسته
همان تاریخ را در کنترل قیمت سفارش، قیمت قراردادی، بازبودن تاریخ فروش، محاسبه EVC
و سقف مشتری مصرف می‌کند.

برای سفارش‌های معمولی، SQL دورهٔ بسته و تاریخ کوچک‌تر یا مساوی `LastDate` را رد
می‌کند. بااین‌حال انواع سفارش ۱۰۰۷ و ۱۰۰۸ از Check بازبودن تاریخ مستثنا هستند و
نبود رکورد مرزی نیز در Procedure منتخب، رد صریح ندارد؛ مقایسه‌های `NULL` می‌توانند
باعث عبور fail-open شوند. ERP مقصد باید تاریخ را Server-side و fail-closed resolve
کند و تاریخ Session یا Client را مرجع نهایی نداند.

## مسیر کلاینت اثبات‌شده

`FormOrderToSale.CheckSetOprDate`، سرویس `OprDateHandler.CheckSetOprDate` را صدا
می‌زند. خروجی این Gate یکی از حالت‌های زیر را ایجاد می‌کند:

- اگر Validation نامعتبر باشد، Toolbar فرم غیرفعال می‌شود؛
- اگر تاریخ آماده باشد، فرم ادامه می‌دهد؛
- اگر تعیین دستی لازم باشد، فرم تاریخ عملیات باز می‌شود و عدم پذیرش آن Toolbar را
  غیرفعال می‌کند.

در Business Handler، مجوز نام‌دار `VN.SDS.Sales / SetOprDate` مشاهده شد. این
مجوز حق تغییر تاریخ Session است و **مجوز تبدیل سفارش به فروش نیست**. اثر مجوز مؤثر
برای هر کاربر یا نقش نیز از IL ایستا قابل نتیجه‌گیری نیست.

دو مسیر `AcceptCommandOld` و `AcceptCommandDiscountV2` مقدار
`UserSessionInfo.OperationdDate_Sale` را در `CreateSaleDate` می‌گذارند. مسیر
`SetUpInitial` هم همان مقدار Session را مصرف می‌کند.

## حل نگاشت FetchReason=2

SQL در `usp_SDSNet_OprDate_getList` برای `FetchReason=2` دو ستون را به‌ترتیب
`LastDate, OprDate` بازمی‌گرداند. IL متد `IsBiggerlastDate` نیز خروجی اول را از
`LastDate` و خروجی دوم را از `OprDate` می‌سازد. در هر دو شاخهٔ خودکار
`CheckSetOprDate`، همان Local متناظر با خروجی دوم وارد
`OperationdDate_Sale` می‌شود.

پس قرارداد اثبات‌شده این است:

`FetchReason=2 → (LastDate, OprDate) → Session.OperationdDate_Sale = OprDate`

این نتیجه از Operandهای Local در IL و ترتیب ستون‌های SQL به‌صورت مشترک اثبات
شده است و صرفاً از نام متغیرها استنباط نشده است.

## مسیر SQL و قواعد قطعیت

Wrapper، `CreateSaleDate` را به هسته به‌عنوان `OprDate` می‌فرستد. مصرف‌کنندگان
اثبات‌شدهٔ آن عبارت‌اند از:

1. کنترل مستقل قیمت اقلام سفارش؛
2. کنترل قیمت قراردادی برای انواع غیر ویژه؛
3. `usp_IsSaleDateOpen` برای انواع غیر ۱۰۰۷/۱۰۰۸؛
4. ساخت و محاسبهٔ EVC؛
5. کنترل سقف مشتری.

`usp_IsSaleDateOpen` رکورد `SysRef=1` همان DC و سال سفارش را می‌خواند و دو Guard
دارد:

- `IsClosed=1` باعث رد می‌شود؛
- `SaleDate <= LastDate` باعث رد می‌شود.

مقایسه روی `varchar(10)` انجام می‌شود؛ بنابراین صحت ترتیب زمانی به قالب ثابت و
صفرپُر تاریخ شمسی وابسته است. مقصد باید تاریخ شمسی را Type کند و مقایسهٔ متنی را
تکرار نکند.

## استثناها و رفتار fail-open

- انواع سفارش ۱۰۰۷ و ۱۰۰۸ از `usp_IsSaleDateOpen` عبور داده نمی‌شوند، اما سایر
  مصرف‌های تاریخ در هسته باقی می‌مانند. دلیل کسب‌وکاری این استثنا هنوز نیازمند
  تأیید Owner است.
- اگر Join رکورد تاریخ عملیات را پیدا نکند، Procedure منتخب شرط `NOT EXISTS`
  یا رد صریح ندارد. متغیرهای مرزی `NULL` می‌مانند و هر دو شرط با منطق سه‌مقداری
  SQL وارد Branch رد نمی‌شوند.
- `usp_ValidateOrderNo` تاریخ عملیات نمی‌گیرد؛ معتبر بودن شماره/دامنه سفارش، جای
  کنترل تاریخ را نمی‌گیرد.
- مجوز `SetOprDate` در Business/UI مشاهده شد؛ بازاعتبارسنجی Actor این مجوز در
  Procedure نهایی تبدیل اثبات نشد.

## Snapshot ناشناس فعلی

Clone ده Profile تاریخ عملیات برای یک DC دارد و Orphan DC صفر است. برای
`SysRef=1` سه ردیف سالانه دیده شد: دو دوره بسته و یک دوره باز؛ هیچ‌کدام تاریخ
عملیات یا `LastDate` خالی ندارند. در کل جدول سه `OprDate=NULL` مربوط به سیستم‌های
دیگر وجود دارد. این Snapshot فقط وضعیت Clone را نشان می‌دهد و تاریخ Session یا
انتخاب هر تبدیل تاریخی را اثبات نمی‌کند.

هر دو نوع ۱۰۰۷ و ۱۰۰۸ در `tblOrderType` پیکربندی شده‌اند، اما تعداد Order و Sale
فعلی و سه‌ماههٔ هر دو در Clone صفر است. پس استثنا capability موجود در کد و
پیکربندی است، ولی استفادهٔ عملیاتی جاری آن اثبات نشده است؛ صفر بودن Clone نیز
مجوز حذف قابلیت یا تعمیم به Production نیست.

## قرارداد مقصد

- `ConvertOrderToSale` فقط شناسهٔ Context و Expected Version بگیرد؛ تاریخ مؤثر
  از Boundary معتبر Server-side resolve شود.
- برای هر `(DC, AccYear, SaleSystem)` دقیقاً یک رکورد جاری مجاز باشد؛ نبود، تکرار،
  بسته‌بودن یا تاریخ غیرروبه‌جلو باعث رد بدون Mutation شود.
- `BusinessDate` یک Value Object تاریخ شمسی باشد، نه `varchar(10)` آزاد.
- مجوز `SetOperationDate` از `ConvertOrderToSale` جدا باشد و Actor، Scope، دلیل،
  Policy version و مقدار قبل/بعد Audit شود.
- استثنای ۱۰۰۷/۱۰۰۸ تا تأیید Owner به حالت `LEGACY_EXCEPTION_UNAPPROVED` بماند و
  به bypass عمومی تبدیل نشود.
- Receipt فرمان باید تاریخ resolveشده، Hash رکورد مرزی و دلیل تصمیم finality را
  ذخیره کند تا Retry همان تصمیم را بازگرداند.

Golden caseها باید دورهٔ باز/بسته، تاریخ قبل/مساوی/بعد، رکورد مفقود/تکراری، قالب
نامعتبر، تغییر هم‌زمان Boundary و انواع ۱۰۰۷/۱۰۰۸ را پوشش دهند.

## سطح اطمینان و محدودیت

- جریان Session تا پارامتر تبدیل و Guardهای SQL: **تأییدشده**.
- ترتیب دو خروجی و انتخاب خروجی دوم برای Session: **تأییدشده** از SQL + IL.
- اثر مجوز مؤثر برای یک Identity، فراوانی تعیین دستی و انتخاب تاریخی هر فرمان:
  **اثبات‌نشده**.
- دلیل کسب‌وکاری استثنای ۱۰۰۷/۱۰۰۸: **نیازمند Owner**.
- نبود رکورد در Snapshot فعلی SysRef=1 مشاهده نشد؛ fail-open یک قابلیت ساختاری
  Procedure است، نه ادعای رخداد عملیاتی.

## ایمنی و بازتولید

- Clone محلی `READ_ONLY` و Login فاقد حق نوشتن بود؛
- هیچ Procedure عملیاتی، فرم یا Command اجرا نشد؛
- Assemblyها Load/Execute نشدند و فقط PE/IL خوانده شد؛
- هیچ شناسهٔ DC/User/Document، SQL خام، پیام یا String حساس در Artifact ذخیره نشد.

خروجی‌ها:

- `scripts/sql/extract_varanegar_order_sale_operation_date_sql.py`
- `scripts/sql/extract_varanegar_order_sale_operation_date_runtime.py`
- `artifacts/varanegar_analysis/domains/order_sale_operation_date_sql_20260829.json`
- `artifacts/varanegar_analysis/domains/order_sale_operation_date_runtime_20260829.json`
- `tests/test_varanegar_order_sale_operation_date_boundary.py`
