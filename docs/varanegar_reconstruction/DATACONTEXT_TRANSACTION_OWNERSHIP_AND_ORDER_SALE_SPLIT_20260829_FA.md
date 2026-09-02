# مالکیت Transaction در DataContext و شکاف مرحله‌ای تبدیل سفارش

تاریخ استخراج: ۲۰۲۶-۰۸-۲۹  
وضعیت: **IL ایستای Hash-pinned از ۵۹ Assembly مدیریت‌شده؛ Load/Execute صفر**

## نتیجهٔ کوتاه

ابهام «آیا DataContextهای تو‌در‌تو یک Transaction مشترک دارند؟» برای پیاده‌سازی
مستقر Thunderstruck تا حد زیادی حل شد. هر `DataContext` به‌صورت پیش‌فرض Provider
و Connection تازه می‌سازد. Enum کتابخانه `Transaction.Begin=0` و
`Transaction.No=1` است و Constructor بدون پارامتر صریحاً حالت ۱، یعنی بدون
Transaction، را انتخاب می‌کند.

`Commit` و `Rollback` فقط وقتی `DbTransaction` غیرNULL باشد عمل می‌کنند؛ در Context
بدون تراکنش هر دو no-op هستند. در کل ۵۹ Assembly مدیریت‌شدهٔ Inventory هیچ
Callsite برای Setter سفارشی Provider، ConnectionFactory یا TransactionalContext
پیدا نشد. بنابراین Contextهای جدا در مسیرهای منتخب را نمی‌توان Ambient/shared
فرض کرد.

## قرارداد کتابخانه

زنجیرهٔ ایستا چنین است:

1. `DataContext(mode)` یک `ProviderFactory` می‌سازد؛
2. Factory یک Provider و یک `DbConnection` تازه ایجاد می‌کند؛
3. Provider در اولین Open فقط وقتی mode برابر صفر باشد `BeginTransaction` می‌کند؛
4. هر Command همان Connection و `DbTransaction` Provider را می‌گیرد؛
5. Commit/Rollback فقط Transaction موجود را Commit/Rollback می‌کند؛
6. Dispose ابتدا Transaction و سپس Connection را Dispose/Close می‌کند.

Property ایستای `TransactionalContext` در خود Assembly فقط Getter/Setter دارد و
هیچ مصرف داخلی ندارد. اسکن Package نیز Setter آن و Setterهای Factory سفارشی را
پیدا نکرد. Reflection یا Plugin خارج از Inventory همچنان در محدودیت باقی است.

## مسیر قدیمی تبدیل سفارش

`OrderAdapter.CreateSaleByOrder` صریحاً `DataContext(Transaction.Begin)` می‌سازد.
اگر Context ورودی NULL باشد همین Context را به Caller برمی‌گرداند، Wrapper را
Execute و سپس Commit می‌کند. Wrapper SQL مقدار `@@TRANCOUNT` را می‌خواند و فقط
وقتی Transaction بیرونی وجود ندارد خودش Begin/Commit می‌کند؛ در این مسیر،
Transaction مدیریت‌شدهٔ Adapter مالک فیزیکی تبدیل است و Wrapper به آن می‌پیوندد.

Overload Business دیگری که مستقیم Core قدیمی را Query می‌کند، اگر Context نگیرد
`DataContext()` پیش‌فرض بدون تراکنش می‌سازد و Commit هم ندارد. Core SQL نیز
Transaction محلی ندارد. پس استفاده از این Overload بدون Context تراکنش‌دار،
نوشتن‌های Core را در یک واحد کار مدیریت‌شده تضمین نمی‌کند.

## مسیر Discount V2

`CreateSaleByOrderUsingDiscountV2` ابتدا `DataContext(Transaction.No)` می‌سازد و
آن را به `FillEVCUsingDiscountV2` می‌دهد. متد بعداً `Commit` صدا می‌زند، اما چون
Context حالت No دارد و `DbTransaction` ساخته نشده، این Commit no-op است؛ Commandهای
SQL این مرحله با دوام مستقل Connection اجرا می‌شوند.

پس از آن `CreateSaleByOrderV2` با Metadata token دقیق، Overload Adapter را صدا
می‌زند. Adapter یک Context تازه با `Transaction.Begin` می‌سازد و تبدیل اصلی را
Commit می‌کند.

نتیجهٔ قطعی ساختاری:

`EVC preparation (No transaction / connection A) → Sale conversion (Begin / connection B)`

این دو مرحله یک Transaction فیزیکی مشترک ندارند. شکست تبدیل پس از موفقیت آماده‌سازی
EVC می‌تواند نیازمند Cleanup/Reconciliation باشد. Artifact وقوع یک Incident
تاریخی را ادعا نمی‌کند؛ فقط امکان و مرز دوام را اثبات می‌کند.

## اصلاح شناخت قبلی

اسناد قبلی صرف وجود چند `Commit` را دلیل اشتراک یا استقلال قطعی نمی‌دانستند. با
خواندن خود کتابخانه، برای مسیر Order-to-Sale اکنون می‌دانیم:

- Contextهای جدا به‌صورت پیش‌فرض Connection جدا دارند؛
- Commit روی Context حالت No نتیجهٔ تراکنشی ندارد؛
- Adapter تبدیل مالک Transaction Begin است؛
- مرحلهٔ EVC نسخهٔ Discount V2 بیرون آن Transaction است؛
- Overload مستقیم Core فقط در صورت دریافت Context تراکنش‌دار از Caller می‌تواند
  داخل یک Unit of Work باشد.

## قرارداد مقصد

- یک Unit of Work تزریق‌شده از ابتدای Policy/Authorization/OperationDate و EVC تا
  Sale، Item، Pointer، Payment، Batch، Stock projection، Attempt و Outbox مالک کل
  فرمان باشد.
- هیچ Business/Adapter داخلی Context تازه نسازد؛ Context/Transaction از Command
  handler عبور داده شود.
- آماده‌سازی EVC یا محاسبهٔ تخفیف یا کاملاً Pure باشد، یا Writeهایش داخل همان Unit
  of Work قرار گیرد.
- اگر مرحله‌ای ذاتاً جداست، Saga state، idempotency key، receipt و Compensation
  صریح داشته باشد؛ Commit no-op نباید API موفقیت تولید کند.
- Architecture test ساخت `new DataContext` در لایه‌های دامنه/Adapter را ممنوع و
  تنها Transaction owner مجاز را enforce کند.

Golden caseها باید شکست بعد از هر Write آماده‌سازی EVC، قبل/بعد از Header، Pointer،
Payment، Batch، Stock و Outbox را تزریق و اثبات کنند که یک نتیجهٔ کامل یا صفر تغییر
باقی می‌ماند. Retry پس از crash-after-commit نیز باید Receipt نخستین نتیجه را
برگرداند.

## سطح اطمینان و محدودیت

- رفتار Constructor/Open/Commit/Rollback/Dispose: **تأییدشده** از IL کتابخانه.
- نبود Setter سفارشی در ۵۹ Assembly Inventory: **تأییدشده**.
- شکاف فیزیکی EVC/Conversion در Discount V2: **تأییدشده** از IL و Metadata token.
- نبود Reflection/Plugin یا کد بیرون Inventory: **اثبات‌نشده**.
- وقوع Partial failure تاریخی: **ادعا نشده**.
- Transaction محلی داخل هر Procedure دیگر باید جداگانه بررسی شود؛ Context بدون
  تراکنش به معنی نبود هر Transaction SQL داخلی نیست.

## ایمنی و بازتولید

- هیچ Assembly Load/Execute نشد؛ فقط PE metadata و IL خوانده شد؛
- هیچ اتصال دیتابیس، فرم، Procedure یا Command عملیاتی اجرا نشد؛
- هیچ رشتهٔ خام، Identity یا دادهٔ کسب‌وکاری ذخیره نشد.

خروجی‌ها:

- `scripts/windows/extract_varanegar_datacontext_transaction_runtime.py`
- `artifacts/varanegar_analysis/domains/datacontext_transaction_runtime_20260829.json`
- `tests/test_varanegar_datacontext_transaction_boundary.py`
