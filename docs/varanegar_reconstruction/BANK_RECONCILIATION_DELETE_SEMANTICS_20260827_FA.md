# تفکیک Delete، Unmatch، Discard و Cancel مغایرت بانکی — ۱۴۰۵/۰۶/۰۵

## نتیجه

دو سطح Legacy با عنوان Delete مشاهده شد، اما معنای آن‌ها متفاوت است:

1. `frmReconciliation.btnDelete_Click` یک Link تطبیق را با transaction صریح و
   `BankBillAdapter.DeleteReconcileItem` باز می‌کند؛ این عملیات **Unmatch** است.
2. `frmReconciliationSetup.btnDelete_Click` BankBillهای یک Reconcile را می‌گیرد،
   وجود ReconcileItem را بررسی می‌کند و سپس مجموعه BankBill را Delete/Update
   می‌کند؛ هیچ فراخوانی `Reconcile.Delete` یا `Reconcile.Update` ندارد. این مسیر
   **Discard imported statement rows** است، نه Cancel قطعی Session.

روال Unmatch در Clone وجود دارد:

- `dbo.DoBankBill_DeleteReconcileItem`
- ورودی `@BankBillId int`
- خروجی `@ErrorNo tinyint`
- تنها وابستگی کاتالوگی `dbo.ReconcileItem`

## اصلاح قرارداد مقصد

چهار مفهوم باید جدا بمانند:

- `bank_reconciliation.unmatch_instrument`
- `bank_reconciliation.discard_imported_statement`
- `bank_reconciliation.cancel_session`
- `bank_reconciliation.reverse_confirmed_session`

برای `cancel_session` فرمان Legacy مستقل مشاهده نشده است؛ وضعیت parity آن
`UNPROVEN_NO_DISTINCT_LEGACY_COMMAND_OBSERVED` است. نام Cancel در Golden bundle
فعلاً provisional و نیازمند تأیید مالک فرایند است. Delete هیچ‌گاه جای Reversal
Session تأییدشده را نمی‌گیرد و Discard در حضور Link فعال مجاز نیست.

## ایمنی و محدودیت

- فقط Call contractهای از قبل redactشده و metadata کاتالوگ خوانده شد.
- متن روال، business row، فرم، transaction و command اجرا/خوانده نشد.
- نبود call استاتیک، مسیر dynamic یا خارجی Cancel را به‌طور قطعی رد نمی‌کند.
- branchهای Runtime و تصمیم کاربر مشاهده نشده‌اند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_delete_semantics_20260827.json`
- `scripts/sql/extract_varanegar_bank_reconciliation_delete_semantics.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_bank_reconciliation_delete_semantics.py `
  --command-guards G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_command_guards_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_delete_semantics_20260827.json
```

وضعیت Artifact: `PASS`؛ دو Delete surface، یک روال Unmatch، صفر فرمان مستقل Cancel و صفر خطا.
