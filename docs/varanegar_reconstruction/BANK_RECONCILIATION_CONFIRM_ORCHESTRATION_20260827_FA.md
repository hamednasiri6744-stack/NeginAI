# Orchestration کامل Confirm مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ UI→Entity→Cardex→Transaction ایستا اثبات شد، اجرای واقعی صفر است**

## مسیر موفق Legacy

`Ok` پس از Prompt، `DoAccept` را فراخوانی می‌کند. ترتیب دقیق مسیر موفق:

1. `Transaction.Start`؛
2. `Reconcile.Amount = Decimal.Zero`؛
3. `ConfirmerId = current AppUserId`؛
4. `ConfirmDate = DateTime.Now`؛
5. `Reconcile.Update`؛
6. `UpdateBankAccountCardex(ReconcileId, out ErrorNo)`؛
7. اگر `ErrorNo==0`، `Transaction.Commit` و `true`؛ سپس فرم بسته می‌شود.

اگر ErrorNo غیرصفر باشد Rollback/false و در Exception نیز Rollback، پیام عمومی و
false رخ می‌دهد. در `DoAccept` هیچ Permission یا OperationDate guard call دیده
نشد؛ Parent/client gate برای مقصد کافی نیست.

## ترکیب با Defect Procedure

Entity Update و اولین Instrument update در یک Physical transaction مشترک‌اند،
اما Procedure Cardex پس از اولین Update موفق `ErrorNo=0` و Return می‌دهد. بنابراین
Outer `DoAccept` Commit می‌کند و نتیجهٔ قابل‌وقوع ایستا این است:

- Session دارای `ConfirmerId/ConfirmDate` است؛
- فقط یک Instrument، نامرتب و غیردترمینیستیک، `IsReconciled=1` شده؛
- Linkهای باقی‌مانده ممکن است Instrumentهای Reconciledنشده داشته باشند؛
- `Amount=0` هیچ‌یک از یازده نتیجهٔ Summary نیست.

این «ممکن بودن» از ترکیب دو Definition/IL قطعی است؛ Frequency واقعی Production
در این بررسی اندازه‌گیری نشده است.

## قرارداد مقصد

- Confirm یک Command صریح و Server-side است و Capability/Scope/Date/State/
  ExpectedVersion را دوباره بررسی می‌کند.
- قبل از اولین Mutation، تمام Linkها و دقیقاً یک Reference نوع‌دار برای هر Link
  Validated می‌شوند.
- تمام Instrumentها، State، Audit و Outbox یا کامل Commit یا کامل Rollback می‌شوند.
- خطای Link گمشده/متعارض باید Reason type پایدار بدهد، نه Boolean/پیام عمومی.
- `Amount` باید تعریف مستقل و تأییدشده داشته باشد و Legacy zero کورکورانه کپی نشود.
- Defect یک‌لینکی Regression test است، نه Target behavior.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_confirm_orchestration_20260827.json`
- `scripts/windows/extract_varanegar_bank_reconciliation_confirm_orchestration.py`
- `tests/test_varanegar_ui_evidence.py`

دو Method و ۱۲۹ Instruction تحلیل شدند؛ فقط چهار Command key امن ثبت شد و هیچ فرم،
Transaction، Entity update یا Procedure اجرا نشد.
