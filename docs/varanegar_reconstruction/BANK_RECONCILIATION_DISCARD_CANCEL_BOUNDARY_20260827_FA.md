# مرز Discard ردیف‌های بانک در برابر Cancel Session

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ Cancel واقعی Legacy همچنان اثبات نشده است**

## رفتار Save و Delete در Setup

`SaveData` وقتی Header جاری Null است، Reconcile را با Account/Date/File/Comment/
User/ModifiedDate می‌سازد، `Reconcile.Update` را قبل از Parser اجرا و ID تولیدشده
را روی فرم نگه می‌دارد. اگر Header از قبل وجود داشته باشد، Save آن را Update نمی‌کند.

`btnDelete_Click`:

1. همهٔ BankBillهای ReconcileId را می‌گیرد؛
2. ReconcileItemهای آن Billها را می‌شمارد؛
3. اگر Link وجود داشته باشد Discard را رد می‌کند؛
4. پس از Prompt فقط `BankBillS.Delete/Update` را اجرا می‌کند.

هیچ `Reconcile.Delete`، Setter وضعیت/Header، Permission، OperationDate، Confirmer
یا ConfirmDate call در این مسیر دیده نشد. پس Header حذف یا Cancel نمی‌شود.

## پیامد

- Parser failure پس از Commit Header می‌تواند Header بدون ردیف بگذارد؛
- Discard موفق نیز ردیف‌ها را حذف ولی Header را نگه می‌دارد؛
- این دکمه Cancel Session نیست؛
- State صریح برای Header خالی در Legacy اثبات نشده است.

دو Method و ۹۰ Instruction تحلیل شدند. هیچ Delete/Update واقعی اجرا نشد.

## قرارداد مقصد

- `discard_imported_statement` و `cancel_session` Commandهای جدا هستند.
- Cancel فقط روی Unconfirmed، بدون Active link، با Capability/Scope/Date/State/
  ExpectedVersion مجاز است.
- Cancel باید Header و Rows را اتمیک Transition/Archive کند؛ Header فعال یتیم نماند.
- Confirmed session Physical delete نمی‌شود و Reversal جدا و Owner-approved می‌خواهد.
- Parser failure باید صفر Header و Rows Persist کند.
- Cancel باید Idempotent و Audited باشد.

شش Case Discard/Cancel به Acceptance تفاضلی افزوده شد؛ هیچ‌کدام اجرا نشده‌اند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_discard_cancel_boundary_20260827.json`
- `scripts/windows/extract_varanegar_bank_reconciliation_discard_cancel_boundary.py`
- `tests/test_varanegar_ui_evidence.py`

نبود Cancel در این مسیر، نبود مسیر Dynamic/External را ثابت نمی‌کند؛ سه Root و
مالک فرایند همچنان Gate نهایی‌اند.
