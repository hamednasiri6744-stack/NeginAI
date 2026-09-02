# قرارداد مالک تراکنش، Saga و Compensation در ERP مقصد

## هدف

این بسته برای ۴۹ فرمان چهارده ماژول، مرز مالک تراکنش و تصمیم میان Local atomic، Transactional outbox، Saga و بازیابی قرنطینه‌شده را تعریف می‌کند. هیچ Pattern برای فرمانی انتخاب نشده و هیچ Transaction، Saga، Compensation یا Fault Injection اجرا نشده است.

## پوشش

- ۳۸ Edge وابستگی ماژولی به ۱۵۹ تعهد هماهنگی Command-to-Participant تبدیل شده است.
- چهار Pattern برای هر ۴۹ فرمان، یعنی ۱۹۶ Candidate، همگی `CANDIDATE_NOT_SELECTED` هستند.
- قرارداد مرز تراکنش ۱۸ فیلد، Receipt گام Saga بیست فیلد و Receipt جبران ۱۸ فیلد دارد.
- دوازده Failure stage برای هر فرمان ۵۸۸ انتساب، شانزده Gate تعداد ۷۸۴ انتساب و شش Role تعداد ۲۹۴ انتساب ایجاد می‌کند.
- ده Outcome میان Commit/Rollback محلی، Commit نامعلوم، پیشرفت Saga، جبران و حالت partial/quarantine تفکیک می‌کند.

## قواعد fail-closed

- Distributed transaction پیش‌فرض نیست و نوشتن مستقیم جدول ماژول دیگر ممنوع است.
- موفقیت Child/Participant موفقیت Parent نیست؛ Parent فقط پس از Receipt همهٔ گام‌های اجباری موفق می‌شود.
- Effect خارجی پیش از Commit و Receipt پایدار محلی ممنوع است.
- Commit نامعلوم پیش از reconciliation نه Retry و نه Compensation می‌شود.
- Compensation یک Business action مستقل، idempotent، versioned و audited است؛ Database rollback محسوب نمی‌شود.
- Effect غیرقابل‌جبران یا نامعلوم نیازمند Quarantine و مالک انسانی است و blocking unknown اجازهٔ Success/Readiness نمی‌دهد.

## وضعیت فعلی

Pattern انتخاب‌شده، مالک نام‌دار، Fault run، اثبات Atomicity، Saga کامل، Compensation اجرا/پذیرش، Owner approval، Command readiness و Pilot readiness همگی صفرند. تمام Failureها `UNEXECUTED`، Gateها `UNMET` و Roleها `UNASSIGNED` هستند؛ پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت مانده است.
