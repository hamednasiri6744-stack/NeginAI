# مرز ذخیره‌سازی Import صورت‌حساب بانکی — ۱۴۰۵/۰۶/۰۵

## نتیجه

زنجیرهٔ استاتیک UI تا SQL برای ذخیره Import چنین است:

```text
frmReconciliationSetup.SaveData
  -> Reconcile.Update
  -> Reconcile.UpdateDetailTables
  -> BankBillS.Update
  -> BankBill.Update
  -> BankBillAdapter.Update
  -> CRUD dbo.BankBill
```

`SaveData` Header تطبیق را مقداردهی می‌کند و `Reconcile.UpdateDetailTables` مجموعه
BankBill را cascade می‌کند. `Reconcile.Update` و `BankBill.Update` هر دو از
Transaction nesting قدیمی استفاده می‌کنند. این ساختار شاهد الزام Atomicity است،
نه الگویی که static transaction آن در وب کپی شود.

## مرز SQL

در `BankBillAdapter.InitCommandCollection` هفت fingerprint بدون متن خام ثبت شد:

- چهار SELECT از `dbo.BankBill2`؛
- یک INSERT، یک UPDATE و یک DELETE روی `dbo.BankBill`.

پارامترهای اصلی با مدل کاتالوگی هم‌بسته‌اند: BankBillId، ReconcileId، تاریخ،
شرح، بدهکار، بستانکار، شماره سند و مانده. متن SQL، module definition، business
row و connection string ذخیره نشده است.

Adapter نام سه hook را دارد: `BeforeBankBill`، `AfterBankBill` و
`DoBankBill_DeleteReconcileItem`. در کاتالوگ Clone فقط مورد سوم وجود دارد؛ دو
Hook Before/After غایب‌اند. این الگوی کشف اختیاری Procedure در Runtime نباید به
مقصد منتقل شود، چون رفتار محیط‌ها را نامرئی و غیرنسخه‌دار می‌کند.

## قرارداد مقصد ERP نگین

- Upload و Parse ابتدا در staging/quarantine انجام می‌شود و حق commit مستقیم به ledger ندارد.
- Header session و تمام ردیف‌های معتبر BankBill در یک transaction سرویس commit می‌شوند.
- repository حق commit مستقل ندارد و از UnitOfWork فرمان استفاده می‌کند.
- identity فایل/Hash و retry باید idempotent باشد؛ duplicate یا payload conflict صریح است.
- Hookها به domain event/outbox handler صریح، نسخه‌دار و قابل تست تبدیل می‌شوند؛ کشف Procedure اختیاری در Runtime ممنوع است.
- خطای هر batch/row باید کل نتیجه پذیرفته‌شده را rollback یا در وضعیت recoverable صریح نگه دارد.

## محدودیت شاهد

- Call graph و fingerprint رفتار Runtime موفق یا parity ردیف زنده را ثابت نمی‌کند.
- نبود Before/After در Clone، نبود آن‌ها در دیتابیس عملیاتی را ثابت نمی‌کند.
- هیچ فرم، Parser، transaction، SQL command، procedure یا business row اجرا/خوانده نشد.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_statement_persistence_boundary_20260827.json`
- `scripts/sql/extract_varanegar_bank_statement_persistence_boundary.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_bank_statement_persistence_boundary.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --source-model G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_source_model_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_statement_persistence_boundary_20260827.json
```

وضعیت Artifact: `PASS`؛ ۱۰ Method، هفت fingerprint، سه Hook name، صفر mismatch/parse/validation error.
