# Golden caseهای Orchestratorهای اصلی ERP مقصد

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۱۵۴ Case مصنوعی؛ اجراشده روی Runtime/DB برابر صفر**

## پوشش

برای ده Command مربوط به Order، Sales return، Supplier invoice/return و Stock
voucher مجموعاً ۱۵۴ Case ساخته شد:

- ۷۰ Case مشترک: موفقیت، Auth deny، Scope deny، stale version، duplicate
  command، Context بسته و اختلاف `blocking_unknown`؛
- ۵۴ Failure injection بعد از تک‌تک Stageهای اعلام‌شده؛
- ۳۰ Case خاص دامنه؛
- صفر شناسه تکراری و Validation برابر `PASS`.

## Caseهای خاص

Order شامل Duplicate item، Credit، Batch dates، Cancel با Downstream و تبدیل
هم‌زمان است. Return شامل Over-return، Returnability، Batch/health، Voucher و
Settlement compensation است. SupplierInvoice/Return شماره تکراری، Toll، Remaining
quantity، Voucher و Supplier status را دارد. StockVoucher نیز Negative stock،
Batch/health، Qty mismatch، Close date، Cardex، Posting و Return duplicate را
پوشش می‌دهد.

## معیار موفقیت Failure injection

خطا بعد از هر Stage نباید Business outcome ناقص ولی Accepted باقی بگذارد. Retry
با همان `command_id` باید به دقیقاً یک Aggregate/Event/Outbox/result برسد. وضعیت
Reconciliation یا صفر است یا صریحاً Pending/Recoverable؛ سکوت یا اختلاف پنهان
قبول نیست.

## محیط مجاز آینده

Caseها فقط روی Target test database ایزوله و Fixture مصنوعی قابل اجرا هستند.
اجرای آن‌ها روی وارانگار عملیاتی، Clone `NeginPakhsh_WebDev` یا Target production
صریحاً ممنوع است. در زمان اجرای Target test، وارانگار باید Disconnect و دست‌نخورده
بماند.

## مرز نتیجه

وجود Test design به معنی PASS بودن پیاده‌سازی آینده نیست. این Artifact Acceptance
contract قبل از کدنویسی است و هیچ Command یا داده کسب‌وکاری را اجرا/مصرف نکرده.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/varanegar_orchestrator_golden_cases_20260827.json`
- `scripts/windows/build_varanegar_orchestrator_golden_cases.py`
- `tests/test_varanegar_ui_evidence.py`
