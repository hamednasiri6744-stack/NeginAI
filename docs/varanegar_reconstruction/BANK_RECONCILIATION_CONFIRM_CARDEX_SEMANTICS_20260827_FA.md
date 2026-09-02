# معنای Redacted به‌روزرسانی Cardex در Confirm مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ Defect کنترل‌جریان اثبات شد، Procedure هرگز اجرا نشد**

## کشف بحرانی

`dbo.DoReconcile_UpdateBankAccountCardex` با Cursor تمام `ReconcileItem`های
Session را از Join با `BankBill` انتخاب می‌کند، اما در هر شش Branch نوع‌دار هم در
حالت `@@ROWCOUNT=0` و هم در حالت موفق بلافاصله `RETURN` دارد. بنابراین:

- در هر اجرای Procedure حداکثر **یک** ابزار `IsReconciled=1` می‌شود؛
- `FETCH NEXT` دوم پس از اولین Link نوع‌دار قابل‌دسترسی نیست؛
- Cursor هیچ `ORDER BY` ندارد، پس اگر Session چند Link داشته باشد انتخاب آن یک
  Link قطعی نیست؛
- Procedure Transaction داخلی ندارد و به Wrapper ایستای Caller متکی است.

این نتیجه از Definition جاری ۲٬۴۴۲-Character و دوازده `RETURN` استخراج شد. هیچ
Cursor یا Procedure اجرا و هیچ ردیفی خوانده نشد.

## شش Branch و Error code

| Reference | جدول Update | تغییر | خطای صفر ردیف |
|---|---|---|---:|
| PChequeID | PCheque | IsReconciled=1 | ۱ |
| PWithDrawId | PWithDraw | IsReconciled=1 | ۲ |
| RBankDraftId | RBankDraft | IsReconciled=1 | ۳ |
| RCashDraftId | RCashDraft | IsReconciled=1 | ۴ |
| RChequeId | RCheque | IsReconciled=1 | ۵ |
| TransferId | Transfer | IsReconciled=1 | ۶ |

موفقیت هر Branch `ErrorNo=0` می‌دهد و همان‌جا Return می‌کند. Procedure شش Update،
شش `@@ROWCOUNT`، دو `FETCH NEXT` و صفر Transaction statement دارد.

## معنای مهاجرت

هدف مقصد «Parity با Defect» نیست. Confirm باید:

- همهٔ Linkهای Scope را پیش از Mutation Load کند؛
- برای هر Link دقیقاً یک Reference نوع‌دار را الزام کند؛
- همهٔ ابزارها را Update کند یا همه‌چیز Rollback شود؛
- affected count را با تعداد Linkهای یکتا برابر بداند؛
- ابزار گمشده/متعارض را Domain error پایدار کند؛
- State، همهٔ Instrumentها، Audit و Outbox را در یک Transaction بنویسد؛
- پس از هر نوع ابزار و قبل از Commit، Failure injection داشته باشد.

سیاست «ابزار از قبل Reconciled» هنوز نیازمند تصمیم مالک فرایند است. برای سنجش
اثر واقعی Defect، فقط Aggregate count یا Fixture موردتأیید مجاز است؛ این Artifact
هیچ اثر Production را ادعا نمی‌کند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_confirm_cardex_semantics_20260827.json`
- `scripts/sql/extract_varanegar_bank_reconciliation_confirm_cardex_semantics.py`
- `tests/test_varanegar_ui_evidence.py`

متن خام SQL ذخیره نشده، String literal ذخیره‌شده صفر و Source دیتابیس READ_ONLY
با `can_update=0` بوده است.
