# مرز Transaction تأیید مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS استاتیک؛ الگوی Transaction قدیمی برای Web مجاز نیست**

## نتیجهٔ اصلی

`frmReconciliation.DoAccept` یک Scope بیرونی باز می‌کند، سپس هم
`Reconcile.Update` و هم `ReconcileAdapter.UpdateBankAccountCardex` Scope داخلی
Start/Commit/RollBack دارند. Legacy این Nesting را با چهار Field static مدیریت
می‌کند: `TransactionLevel`، `_connection`، `ConnectionString` و `Trans`.
هیچ‌یک Attribute `ThreadStatic` ندارد؛ مقدار هیچ Field یا Connection string
خوانده/ذخیره نشد.

IL شمارنده نشان می‌دهد:

- Start فقط در Level صفر Connection را باز و Physical transaction را شروع می‌کند،
  سپس Level را زیاد می‌کند؛
- Commit فقط در Level یک Physical Commit/Close انجام می‌دهد و Level را کم می‌کند؛
- Rollback در هر Level مثبت، Level را صفر و Physical transaction را Rollback/Close
  می‌کند.

این الگو Nested callهای Desktop را در یک Scope نگه می‌دارد، اما State آن
Process-wide است. مشاهدهٔ Race واقعی انجام نشده؛ با این حال کپی آن در Web چندنخی
ایمن اثبات نشده و ممنوع است.

## قرارداد مقصد

- Transaction owner فقط Application service فرمان
  `bank_reconciliation.confirm` است؛
- Connection/Transaction/UnitOfWork باید Request/Command-scoped باشد، نه static؛
- Repositoryها فقط در UnitOfWork موجود Enlist می‌شوند و Commit داخلی ندارند؛
- تغییر State، به‌روزرسانی Cardex، Audit و Outbox در یک Local transaction قرار
  می‌گیرند؛
- Fault injection بعد از State، Cardex، Audit، Outbox و Physical commit لازم است.

## ایمنی و حدود

- دو DLL فقط Parse شدند؛ Hash هر دو با Inventory منطبق بود؛
- شش Method و چهار Field static ثبت شد؛ خطای Parse صفر بود؛
- هیچ DLL، Connection، Transaction، Command، Form یا ردیف کسب‌وکار اجرا نشد؛
- نبود `ThreadStatic` شاهد متادیتاست، نه اندازه‌گیری رفتار همزمان Runtime.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_transaction_boundary_20260827.json`
- `scripts/windows/extract_varanegar_bank_reconciliation_transaction_boundary.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_bank_reconciliation_transaction_boundary.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_transaction_boundary_20260827.json
```
