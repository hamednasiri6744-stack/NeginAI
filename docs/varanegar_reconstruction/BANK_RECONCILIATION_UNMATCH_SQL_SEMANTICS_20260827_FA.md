# معنای Redacted SQL برای Unmatch مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ Delete scope اثبات شد، Procedure اجرا نشد**

## رفتار واقعی Procedure

`dbo.DoBankBill_DeleteReconcileItem(@BankBillId, @ErrorNo out)` فقط این کار را
می‌کند: تمام `ReconcileItem`های دارای `BankBillId` ورودی را Delete می‌کند.

- Predicate فقط `BankBillId` است؛ `ReconcileItemId`، Reconcile، Account، State یا
  ExpectedVersion در Scope نیست.
- اگر صفر ردیف حذف شود ErrorNo=1 و در غیر این صورت ErrorNo=0 است؛ affected count
  واقعی برگردانده نمی‌شود.
- هیچ Instrument table آپدیت و `IsReconciled` Reset نمی‌شود.
- Header، Audit و Outbox تغییر نمی‌کنند و Transaction داخلی وجود ندارد.

Definition جاری ۲۶۹ Character، یک DELETE، صفر UPDATE و یک Dependency دارد. متن
خام ذخیره و Procedure اجرا نشده است.

## خطر State

این Procedure «حذف یک Link مشخص» نیست؛ اگر یک BankBill چند Link داشته باشد همه
را حذف می‌کند. Schema نیز به‌تنهایی Unique بودن BankBillId در ReconcileItem را
اثبات نمی‌کند.

مهم‌تر، استفاده پس از Confirm می‌تواند Link را پاک کند ولی Instrument را با
`IsReconciled=1` باقی بگذارد. بنابراین:

- Unmatch فقط در `IMPORTED_UNCONFIRMED` مجاز است؛
- Confirmed session باید Command مستقل Reversal داشته باشد؛
- Link deletion هرگز معادل Reversal نیست.

## قرارداد مقصد

- Unmatch با LinkId + ExpectedVersion و Error type پایدار کار کند.
- Invariant حداکثر یک Active link برای هر BankBill صریحاً در Schema/Domain enforce شود.
- Reversal همهٔ Instrumentها و Session state را در یک Transaction Reset کند.
- Legacy Procedure مستقیماً از Web قابل‌اجرا نیست.
- Caseهای Unmatch/Reverse به Acceptance تفاضلی افزوده شدند؛ اجرای آن‌ها هنوز صفر است.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_unmatch_sql_semantics_20260827.json`
- `scripts/sql/extract_varanegar_bank_reconciliation_unmatch_sql_semantics.py`
- `tests/test_varanegar_ui_evidence.py`

Cancel Session و Reversal مستقل Legacy همچنان اثبات نشده‌اند و نیازمند Owner/
Runtime evidence هستند.
