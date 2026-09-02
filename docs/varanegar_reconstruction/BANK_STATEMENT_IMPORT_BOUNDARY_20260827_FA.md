# مرز Import فایل صورت‌حساب بانکی وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS استاتیک؛ Desktop parser نباید به وب کپی شود**

## نتیجهٔ اصلی

شش Method مسیر Import مغایرت بانکی ردیابی شد. سه Parser
`getDataFromDBF/getDataFromTXT/getDataFromXLS` هر سه
`OleDbConnection`، `OleDbCommand` و `DataAdapter.Fill` می‌سازند. Dispatch اصلی
هم‌زمان `FormatExtension`، `HDR`، `SchemaFile` و `SQLStatement` را لمس می‌کند؛
بنابراین رفتار Import به Profile/Query پیکربندی‌شده وابسته است.

دو Side effect دسکتاپی نیز قطعی است:

- `WriteSchemaFile` فایل ایجاد/حذف و Line می‌نویسد؛
- `SaveAsExcel` Excel Interop را باز می‌کند، Workbook را SaveAs می‌کند، فایل
  Copy/Delete می‌کند و `Process.Kill` فراخوانی می‌کند.

این Callها به‌تنهایی Injection یا فایل مخرب واقعی را اثبات نمی‌کنند. آن‌ها مرز
اجرای Provider/Query، فایل‌سیستم و Process را ثابت می‌کنند و برای نسخه وب نیازمند
طراحی متفاوت‌اند.

## قرارداد مقصد

### Profile نسخه‌دار Import

مدل منبع موجود نشان می‌دهد Profile قدیمی از سه جدول صفرردیف Clone ساخته شده است:

- `BankBillFormatType`: پسوند فایل؛
- `BankBillFormat`: Bank، نوع حساب، StartRow، Separator، Arabic، HDR و همچنین
  دو مقدار پرریسک `SQLStatement` و `SchemaFile`؛
- `BankBillFormatItem`: نگاشت ReconciliationColumn به StartColumn/EndColumn.

صفرردیف بودن Clone یعنی نمونهٔ واقعی Profile برای parity نداریم. مقصد باید این
ساختار را به `ImportProfileVersion` داده‌محور و allowlist‌شده تبدیل کند: parser
type، encoding، delimiter/header، start row و mapping ستون‌ها. `SQLStatement`،
provider arbitrary و path مربوط به SchemaFile هرگز ورودی اجرایی Profile وب نیستند.

Pipeline امن مقصد:

1. Upload به Object store ایزوله؛
2. کنترل Size، Signature و نوع واقعی فایل؛
3. انتخاب Bank-format profile نسخه‌دار و تأییدشده؛
4. Parser sandboxed بدون Office Automation؛
5. تبدیل به Canonical statement row؛
6. Validation تاریخ/مبلغ/Schema/Duplicate؛
7. Preview یا Quarantine؛
8. Commit idempotent به Staging؛
9. Match و Confirm به‌صورت Commandهای جدا.

در مقصد، Provider string، File path یا Query خام از Browser قابل اجرا نیست.
Templateهای Query باید Server-owned، allowlisted و نسخه‌دار باشند. Import نیز
مستقیماً Ledger حسابداری را تغییر نمی‌دهد.

## ایمنی و حدود

- DLL فقط Parse شد و Load/Execute نشد؛ Hash با Inventory منطبق بود؛
- هیچ فایل ایجاد/حذف/باز نشد و هیچ Process Office شروع/کشته نشد؛
- هیچ Connection دیتابیس یا Command برنامه اجرا نشد؛
- Provider string، SQLStatement، Path، محتوای فایل و ردیف کسب‌وکار ذخیره نشد.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_statement_import_boundary_20260827.json`
- `scripts/windows/extract_varanegar_bank_statement_import_boundary.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_bank_statement_import_boundary.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_statement_import_boundary_20260827.json
```
