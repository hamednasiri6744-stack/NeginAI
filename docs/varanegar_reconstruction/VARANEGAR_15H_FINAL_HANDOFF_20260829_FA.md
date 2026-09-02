# تحویل مرحله شناخت فقط‌خواندنی ۱۵ ساعته وارانگار — ۱۴۰۵/۰۶/۰۷

## نتیجه

مرحله زمانی تعیین‌شده با یک Baseline قابل بازتولید بسته شد. ۳۶ Checkpoint روز
۲۰۲۶-۰۸-۲۹ همگی `PASS` هستند و ۵۲۹ تست آفلاین روی ۴۳ فایل تست عبور کردند. رجیستر
ریسک عمداً ثابت ماند: ۸۴ ریسک شامل ۵۰ Critical، ۳۱ High و سه Medium؛ ۳۴۳ اتصال
ریسک به نیاز ثبت شده و تعداد Moduleهای آماده اجرای Command همچنان صفر است.

صفر بودن Command-ready نقص بسته نیست؛ نتیجه صادقانهٔ شناخت فعلی است. رفتارهای
Legacy به‌اندازه کافی برای طراحی قرارداد مقصد شناخته شده‌اند، ولی پیاده‌سازی
فرمان مالی/انبار/فروش بدون Golden Case و UAT ایزوله هنوز مجاز نیست.

## پوشش اثبات‌شده

- سفارش، تبدیل سفارش به فروش، لغو فروش، برگشت، Voucher، صدور حسابداری، چاپ فاکتور
  و خروج توزیع؛
- دریافت/پرداخت NGT، Replication و Compensation، Undo چک پرداختنی و دریافتی و
  حذف Master دریافت؛
- تأیید/ابطال تأیید/حذف سند انبار، Projection موجودی، اعمال/برگشت هزینه خرید؛
- مجوز، Scope، OperationDate، Feature/Policy flag و مرزهای UI در برابر Service؛
- Outcome پیام در برابر Commit/Rollback، مالکیت DataContext، Idempotency و
  Retry/Replication؛
- موتور Discount V2، ۴۲ Query template، ۴۱ dependency پایدار، ۷٬۱۵۶ Method در
  سه DLL موتور و مسیر اجرای `SqlCondition`؛
- رفتار سه‌ماههٔ قواعد پیشرفته: ۴۴ خانواده، فقط دو خانواده/سه Rule دارای اثر
  retained، ۴۷۱ اثر روی ۳۸ فروش.

## کشف‌های با بیشترین اثر معماری

1. تبدیل سفارش یک Insert ساده نیست؛ تراکنش، Trigger، پرداخت، موجودی، رزرو، تاریخ
   عملیات و Policyهای چندحالته در آن دخیل‌اند.
2. Commitهای DataContextهای تو در تو اثبات یک تراکنش فیزیکی نیستند؛ بخشی از
   مسیرها Context جدا دارند یا بدون Transaction کار می‌کنند.
3. Discount V2 ورودی را با ۳۵ خواندن مستقیم و بدون Snapshot کل محاسبه می‌سازد؛
   RCSI فقط هر Statement را جدا پایدار می‌کند.
4. `SqlCondition` واقعاً با `sp_executesql` اجرا می‌شود. داده فعلی DML/DDL مخرب
   نشان نداد، اما مقصد باید آن را به DSL/AST نوع‌دار، نسخه‌دار و چهارچشمی تبدیل کند.
5. مجوزهای مشاهده‌شده عمدتاً UI/Session-cache gate هستند؛ API مقصد باید هر Command
   و Resource scope را مستقل و deny-first بررسی کند.
6. Cancellation برخی Batchها بین آیتم‌هاست، نه Cancel تراکنش جاری؛ خروجی قبلی
   می‌تواند Commit شده باشد و قرارداد Partial Success لازم است.
7. Replication و تاریخچه حذف، Attempt ledger کامل نیستند؛ Idempotency key، Outbox،
   Tombstone و Reconciliation در مقصد الزامی‌اند.

## Safety اجراشده

- هیچ فرم یا Stored Procedure عملیاتی اجرا نشد؛
- هیچ داده وارانگار/NGT یا سیستم زنده تغییر نکرد؛
- هیچ دسترسی Write ساخته نشد؛
- DLLها فقط با PE/CLR metadata و IL ایستا خوانده شدند و Load/Execute نشدند؛
- متن خام شرط تجاری، شناسه ردیف و Credential در Artifactهای جدید ذخیره نشد.

## Artifact نهایی

- `artifacts/varanegar_analysis/varanegar_15h_final_baseline_bundle_20260829.json`
- `artifacts/varanegar_analysis/varanegar_15h_final_test_result_20260829.json`
- `scripts/windows/build_varanegar_15h_final_bundle_20260829.py`
- `scripts/windows/run_varanegar_15h_final_tests.py`
- `tests/test_varanegar_15h_final_bundle.py`

## مسیر پیشنهادی ۲۵ ساعت بعد

1. Truth table کامل Commandهای باقیمانده را از UI → Business → Adapter → SQL →
   Trigger → Accounting/Replication ببندیم؛
2. Reportهای مرجع را به Definition، Filter، تاریخ/Scope و Reconciliation formal
   تبدیل کنیم؛
3. برای دو خانواده فعال Discount V2 و مسیرهای پرتکرار فروش/چک/انبار Golden Case
   ناشناس بسازیم؛
4. در UAT ایزوله و دارای Snapshot، Differential harness فقط‌خواندنی/rollback-safe
   طراحی کنیم؛ هیچ اجرای عملیاتی روی Production انجام نشود؛
5. قراردادهای Web ERP را به Command schema، State machine، Authorization matrix،
   Unit of Work، Idempotency و Audit event تبدیل و سپس Module readiness را دوباره
   ارزیابی کنیم.

## محدودیت

شناخت فعلی عمیق و قابل رجوع است، اما «کارشناس کامل همه شاخه‌های Production» هنوز
ادعای درستی نیست. Branchهای وابسته به تنظیمات مشتری، Integrationهای بیرونی،
رفتار Operator و خروجی واقعی Ruleها بدون UAT/Golden Case فقط قابلیت ایستا یا
استنباط قوی محسوب می‌شوند.
