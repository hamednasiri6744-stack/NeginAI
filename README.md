# NeginAI Secure SQL Gateway

## دستیار مستقل NeginAI

نسخه Custom GPT و فایل `openapi-action.yaml` حفظ شده‌اند. در کنار آن، رابط مستقل
هوش مصنوعی در `http://127.0.0.1:8000/assistant` قرار دارد و مستقیماً از
OpenAI API استفاده می‌کند. کلید `OPENAI_API_KEY` فقط در فایل `.env` روی سرور
نگهداری می‌شود و هرگز برای مرورگر ارسال نمی‌شود. مدل پیش‌فرض دستیار مستقل
`gpt-5.6-sol` با سطح استدلال `medium` است و از طریق
`OPENAI_MODEL` و `OPENAI_REASONING_EFFORT` قابل تغییر است.
برای ایمنی فنی در برابر گردش بی‌پایان، حد اضطراری عامل با `OPENAI_MAX_TURNS` (پیش‌فرض ۱۴) و
تاریخچهٔ ارسالی با `OPENAI_HISTORY_LIMIT` (پیش‌فرض ۱۲ پیام) محدود می‌شود.

موتور برای سؤال‌های داده‌ای مسیر ثابت و سؤال‌محور ندارد. پیش از هر اجرا، تعریف‌های کسب‌وکار،
ساختار مرتبط، خطاهای شناخته‌شدهٔ منابع و نمونهٔ گزارش‌های موفق قبلی را بازیابی می‌کند؛ سپس SQL
زنده را می‌سازد، خطا یا نتیجهٔ خالی را اصلاح و کنترل می‌کند و فقط از شاهد تأییدشده پاسخ می‌دهد.

دستیار مستقل از OpenAI Agents SDK و ابزارهای محدودشده برای جست‌وجوی چندمرحله‌ای
ساختار، تعریف‌ها و موجودیت‌های شرکت استفاده می‌کند. تنها ابزار اجرایی آن از
کنترل `sqlglot` عبور می‌کند و فقط یک `SELECT` یا `WITH...SELECT` را می‌پذیرد.

فایل `NeginAI-Assistant.exe` نسخه مستقل ویندوز را اجرا می‌کند. رابط وب واکنش‌گرا
است و از منوی مرورگر موبایل با گزینه Add to Home Screen به‌صورت PWA نصب می‌شود.

## Automatic brand/manufacturer catalog

NeginAI reads brands from `GNR.tblBrand` and manufacturers from
`GNR.tblManufacturer` into a separate SQLite catalog. It refreshes immediately
after service startup and then every `ENTITY_SYNC_INTERVAL` seconds (default:
300). The source SQL Server is only read; no row is inserted or updated there.

Use `GET /entities/search?q=...` to resolve Persian/Arabic spelling variants.
When the question explicitly says brand or manufacturer, results are restricted
to that entity type and include the correct `BrandRef` or `ManufacturerRef` join
guidance. `POST /context/search` also returns these resolved entities, so Custom
GPT can use them before composing a sales query.

بخش Custom GPT همچنان یک درگاه فقط‌خواندنی مستقل است؛ وابستگی OpenAI فقط به
دستیار مستقل وب/ویندوز مربوط می‌شود.

## پیش‌نیازهای Windows 10

- Python 3.11 (گزینه Add Python to PATH فعال باشد)
- Microsoft ODBC Driver 18 for SQL Server
- یک کاربر SQL Server که در خود SQL Server فقط مجوز `SELECT` و مشاهده metadata دارد

## نصب

```powershell
cd G:\NeginAI
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

در اولین اجرای برنامه، اگر `NEGIN_ACTION_API_KEY` خالی باشد، برنامه یک مقدار تصادفی امن تولید و فقط داخل `.env` ذخیره می‌کند. این مقدار را در کد، Git یا گزارش‌ها قرار ندهید.

فایل `.env` را مستقیماً ویرایش و مقادیر اتصال SQL را تکمیل کنید. رمز را در چت یا command line وارد نکنید:

```dotenv
SQL_SERVER=YOUR_SERVER
SQL_DATABASE=NeginPakhsh
SQL_USERNAME=YOUR_READ_ONLY_USER
SQL_PASSWORD=YOUR_PASSWORD
```

کاربر SQL باید در SQL Server به‌صورت واقعی Read Only ساخته شده باشد. `ApplicationIntent=ReadOnly` و کنترل SQL در برنامه لایه‌های دفاعی مکمل هستند و جای مجوز صحیح دیتابیس را نمی‌گیرند.

## اجرا و بررسی

```powershell
.\start.bat
```

سپس در پنجره دیگری:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

رابط فارسی سامانه در آدرس زیر در دسترس است:

```text
http://127.0.0.1:8000/
```

کنسول مدیریتی پرسنل، سمت‌ها و دسترسی‌ها در `/control` قرار دارد. این کنسول
با نشست امضاشده مدیر کار می‌کند. فهرست کامل پرسنل را به‌صورت فقط‌خواندنی از
`GNR.vwPersonnel` دریافت و آخرین snapshot را برای مشاهده آفلاین در IndexedDB
دستگاه نگه می‌دارد. جدول فقط کد و شناسه پرسنلی، نام کامل، نام، نام خانوادگی،
وضعیت در ورانگر، نوع پرسنل و موبایل را نشان می‌دهد و از نتیجه فیلترشده خروجی
واقعی Excel می‌سازد. هر مدیر می‌تواند تعداد ردیف، فیلترهای ستونی و ستون‌های
قابل نمایش را موقتاً اجرا کند یا در قالب طرح‌های نام‌دار و پیش‌فرض ذخیره کند.
تخصیص انحصاری پرسنل به شعب البرز، تهران، قزوین، رشت و ستاد نیز در همین کنسول
انجام می‌شود. طرح‌ها، تخصیص شعب، سمت‌ها و دسترسی‌ها فقط در SQLite داخلی NeginAI
ثبت می‌شوند و در حالت آفلاین در IndexedDB صف می‌مانند. هر عملیات شناسه پایدار
و نسخه مبنا دارد تا پس از اتصال دوباره بدون ثبت تکراری همگام شود و تعارض
ویرایش هم‌زمان به‌صورت صریح به مدیر نمایش داده شود. این مسیر هیچ عملیات
نوشتنی روی NGT، SQL Server عملیاتی یا ورانگر انجام نمی‌دهد.

برای ورود به رابط، مقدار `NEGIN_ACTION_API_KEY` را مستقیماً از `.env` وارد کنید. کلید فقط در حافظه همان صفحه نگه داشته می‌شود و با Refresh یا بستن صفحه پاک خواهد شد.

## Runtime فعلی

Workflow قدیمی EXE/launcher بازنشسته شده است. Runtime کاننیکال فعلی از `ops/vnext-runtime-supervisor.ps1`، Backend پورت `8011` و Frontend `vnext/` استفاده می‌کند.

مستندات محلی در `http://127.0.0.1:8011/docs` است. برای اسکن اولیه، درخواست `POST /schema/scan` را با Header زیر ارسال کنید:

```text
X-API-Key: مقدار NEGIN_ACTION_API_KEY از فایل .env
```

## Custom GPT Action

1. سرویس را پشت یک دامنه عمومی HTTPS معتبر منتشر کنید.
2. مقدار `servers.url` در `openapi-action.yaml` را با همان دامنه جایگزین کنید.
3. فایل را در بخش Actions مربوط به Custom GPT وارد کنید.
4. Authentication را روی API Key، نوع Custom و Header با نام `X-API-Key` تنظیم کنید.
5. مقدار `NEGIN_ACTION_API_KEY` را مستقیماً از `.env` در تنظیمات محرمانه Action وارد کنید؛ آن را در Instructions ننویسید.

ChatGPT نمی‌تواند مستقیماً به `localhost` دسترسی داشته باشد؛ برای Action واقعی به HTTPS عمومی و کنترل شبکه مناسب نیاز است.

## امنیت SQL

- فقط یک Statement از نوع `SELECT` یا `WITH ... SELECT` پذیرفته می‌شود.
- AST کوئری با `sqlglot` در dialect مربوط به T-SQL تحلیل می‌شود.
- عملیات تغییردهنده، اجرای procedure، تراکنش و `SELECT INTO` رد می‌شوند.
- تعداد ردیف با `SQL_MAX_ROWS` و timeout با `SQL_QUERY_TIMEOUT` محدود است.
- تمام تلاش‌های اجرای SQL و خطاها در SQLite ثبت می‌شوند.
- اتصال SQL با `ApplicationIntent=ReadOnly` ایجاد و در پایان rollback می‌شود.

## تست

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

تست اتصال واقعی SQL فقط پس از تکمیل `.env` و فراهم بودن SQL Server قابل انجام است.
