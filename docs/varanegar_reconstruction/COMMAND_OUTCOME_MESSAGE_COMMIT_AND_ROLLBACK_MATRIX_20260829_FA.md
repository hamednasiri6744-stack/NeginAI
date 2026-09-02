# ماتریس Outcome، پیام، Commit و Rollback فرمان‌های وارانگار

تاریخ شواهد: ۲۰۲۶-۰۸-۲۹  
وضعیت: **۱۰ مسیر در ۶ دامنه با شواهد قبلی Hash-pinned تطبیق داده شد**

## نتیجهٔ اصلی

در وارانگار «پیام خطا»، «خطای کسب‌وکار»، Exception و Rollback یک مفهوم واحد
نیستند. شکل خروجی یک Procedure به‌تنهایی تعیین نمی‌کند داده Commit شده یا نه.
این تصمیم در هر مسیر به ترتیب Write/Validation، مالک تراکنش و رفتار Caller وابسته
است.

ماتریس بازتولیدپذیر حاضر ۱۰ مسیر را به ۱۰ کلاس متمایز رساند. شش مسیر از
Message یا Result به‌عنوان بخشی از کنترل شکست استفاده می‌کنند و در سه مسیر،
اشتراک یک تراکنش فیزیکی میان Contextهای مدیریت‌شدهٔ تو‌در‌تو اثبات نشده است.
بنابراین در ERP وب نباید همهٔ قراردادهای Legacy را به یک Boolean سادهٔ
`success/error` تبدیل کرد.

## مهم‌ترین تفاوت‌های اثبات‌شده

| مسیر | کانال شکست | نسبت شکست با Write/Commit | نتیجه |
|---|---|---|---|
| صدور سند حسابداری | Result عددی نوع خطای کسب‌وکار | خطا پیش از Write ساخته می‌شود، ولی Business همچنان Commit می‌کند | فعلاً فقط به‌خاطر ترتیب فعلی امن است |
| انتقال سند حسابداری | Result خطا بدون Exception | پاک‌سازی شماره می‌تواند پیش از Validation رخ دهد | Caller می‌تواند پاک‌سازیِ درخواست ردشده را Commit کند |
| تأیید سند انبار | پیام خروجی After | در مسیر مستقیم، Commit پیش از After است | پیام Post-commit است و Transaction را کنترل نمی‌کند |
| برگشت تأیید سند انبار | پیام خروجی After | After پیش از Commit است، اما پیام Guard نمی‌شود | Caller با وجود پیام Commit می‌کند |
| ذخیرهٔ برگشت از خرید در Desktop | پیام Validator | Caller پیام غیرخالی را پیش از Commit تفسیر می‌کند | ردشدن واقعاً Commit را متوقف می‌کند |
| صدور سند برگشت از فروش | Exception/Catch | بعضی Validationها بعد از Insert هستند | Transaction/Savepoint محلی Rollback می‌کند |
| صدور/لغو خروج توزیع | وابسته به Route | Procedureهای منتخب مالک تراکنش محلی نیستند | اتمیک‌بودن به Caller/Ambient وابسته است |
| تبدیل سفارش به فروش | Exception و شاخهٔ Rollback | Business و Adapter هر دو Commit signal دارند | اشتراک تراکنش و مقدار شاخهٔ بدون Rollback اثبات نشده |
| لغو فروش | Exception/Catch | Procedure و Triggerها زیر Transaction محلی‌اند | مالک SQL برای این مسیر اثبات شده است |
| ثبت چاپ موفق فاکتور | وضعیت موفق چاپ | Audit فقط بعد از `PrintedCompleted` و در Commit جدا ثبت می‌شود | چاپ و Audit دو Outcome جدا و قابل Partial-success هستند |

## برداشت معماری برای Negin ERP

پیام نمایش به کاربر نباید primitive کنترل تراکنش باشد. قرارداد مقصد باید حداقل
Outcomeهای زیر را صریح و ماشین‌خوان تعریف کند:

- `ACCEPTED`: تغییر کسب‌وکاری و Receipt آن Commit شده است؛
- `ACCEPTED_WITH_WARNING`: تغییر Commit شده و Warning فقط metadata است؛
- `REJECTED`: هیچ تغییر کسب‌وکاری نباید Commit شود؛
- `PARTIAL_SUCCESS`: اثر بیرونی و ثبت داخلی هم‌زمان اتمیک نیستند و نیاز به
  reconciliation دارند؛
- `UNKNOWN`: نتیجهٔ Commit/Rollback قابل اثبات نیست و باید quarantine شود.

قواعد پایهٔ مقصد:

1. فقط `ACCEPTED` و `ACCEPTED_WITH_WARNING` مجاز به پیش‌بردن state هستند.
2. همهٔ preconditionها تا حد ممکن پیش از اولین Write اجرا شوند.
3. postcondition ناموفق باید همان Transaction را Abort کند؛ نباید بعد از Commit
   صرفاً به متن پیام اضافه شود.
4. هر Command یک مالک تراکنش فیزیکی Server-side و قابل مشاهده داشته باشد.
5. Context تو‌در‌تو، Commit دوگانه و پارامتر عمومی «بدون Rollback» در API مقصد
   مجاز نباشد.
6. اثر خارجی مانند چاپ با Outbox/Receipt و reconciliation مدل شود، نه با ادعای
   Atomicity غیرواقعی.
7. Warning، خطای دامنه، خطای فنی و وضعیت نامعلوم Commit چهار نوع مستقل باشند.

## چیزی که این مرحله ثابت نمی‌کند

- وقوع واقعی هر branch خطا یا فراوانی آن در Production؛
- اشتراک Connection/Transaction در مسیرهایی که IL فقط Contextهای تو‌در‌تو را
  نشان می‌دهد؛
- موفقیت یا شکست تاریخی هر فرمان؛
- برابری Query داخلی Template چاپ با دیتابیس جاری؛
- اینکه پاک‌بودن Aggregateهای فعلی، مسیر خطرناک را غیرقابل‌دسترسی می‌کند.

## خروجی بازتولیدپذیر

- Builder آفلاین:
  `scripts/windows/build_varanegar_command_outcome_commit_matrix_20260829.py`
- Artifact:
  `artifacts/varanegar_analysis/domains/command_outcome_commit_matrix_20260829.json`
- Test:
  `tests/test_varanegar_command_outcome_commit_matrix.py`

این مرحله هیچ اتصال تازه‌ای به دیتابیس، اجرای UI/Procedure/Trigger، Load/Execute
Assembly یا ذخیرهٔ شناسه/نام/متن خطا/تعریف SQL خام نداشت. ماتریس فقط از Artifactهای
قبلیِ redacted و Hash-pinned ساخته شده است.
