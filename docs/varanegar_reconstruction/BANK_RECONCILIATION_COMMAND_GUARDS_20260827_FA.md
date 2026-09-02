# Guardهای فرمان مغایرت بانکی وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS استاتیک؛ نتیجهٔ نقش احرازشده و Commit واقعی هنوز UAT نشده**

## نتیجهٔ اصلی

ده Method حساس در چهار فرم خوشهٔ مغایرت بانکی به‌صورت IL فقط‌خواندنی ردیابی شد.
سه مرز مهم برای ERP مقصد به دست آمد:

1. مجوز فرم List با Alias قدیمی `TransferList.AddNew/Edit/Delete` و وضعیت بسته
   بودن تاریخ عملیات ترکیب می‌شود؛
2. فرم Setup از Alias `ReconciliationSetup.Edit/Delete` استفاده می‌کند و
   Validation آن حساب بانکی، تاریخ بانک و فایل بانک را لمس می‌کند؛
3. حذف یک ReconcileItem در فرم Detail دارای Signal صریح
   `Transaction.Start/Commit/RollBack` است، ولی مسیر Import/Save در لایه UI چنین
   Signal صریحی ندارد.

Alias `TransferList` نام قابلیت مقصد نیست. این یک reuse تاریخی در مجوز Legacy است
و کپی مستقیم آن به Role/Capability وب می‌تواند دسترسی حواله را ناخواسته به
مغایرت بانکی گره بزند.

## قراردادهای Method-level

- `frmBankReconciliationList.SetFormPermission`:
  `TransferList.get_AddNew/Edit/Delete`، تاریخ عملیات و
  `OprDate.get_IsClosed`؛
- `frmReconciliationSetup.SetFormPermission`:
  `ReconciliationSetup.get_Edit/Delete` و کنترل‌های Accept/Delete؛
- `frmReconciliationSetup.DataIsValid`:
  `cmbBankAccountName`، `txtBankDate` و `txtBankFile`؛
- `frmReconciliationSetup.btnAccept_Click`:
  Dispatch به DBF/TXT/XLS، Schema writer، SaveData، ایجاد/به‌روزرسانی BankBill و
  بازکردن Detail؛
- `frmReconciliationSetup.btnDelete_Click`:
  Confirmation، بارگیری BankBill/ReconcileItem و Delete/Update Collection؛
- `frmReconciliation.btnDelete_Click`:
  Confirmation، حذف Link و Start/Commit/RollBack صریح.

وجود Call ایستا ترتیب کامل Branch، موفقیت Commit، Scope نقش یا Rollback تمام
Side effectها را ثابت نمی‌کند.

## الزام مقصد

- Capabilityهای مستقل `import/edit/delete/confirm/cancel` برای مغایرت بانکی تعریف
  شوند؛ Aliasهای Legacy فقط Crosswalk evidence هستند.
- Authorization نهایی Permission را با سال مالی، DC، حساب بانکی، تاریخ عملیات و
  State transition ترکیب کند.
- Import/Save و حذف Aggregate یک Transaction owner سرویس‌محور و Idempotency key
  صریح داشته باشد؛ UI مالک Transaction یا CRUD جدول نیست.
- Cascade حذف، وضعیت لینک‌های چندنوعی، Audit و Reconciliation پیش از فعال‌سازی
  Command اثبات شود.

## ایمنی و حدود

- Hash `TreasuryOld.Forms.dll` با Inventory ۶۲ فایل منطبق بود؛
- چهار Type و هر ده Method انتخاب‌شده پیدا شد؛ خطای Parse صفر بود؛
- هیچ DLL/Form/Command/Procedure/Trigger اجرا نشد؛
- هیچ مقدار ردیف کسب‌وکار، String literal یا Config payload ذخیره نشد.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_command_guards_20260827.json`
- `scripts/windows/extract_varanegar_bank_reconciliation_command_guards.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_bank_reconciliation_command_guards.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_command_guards_20260827.json
```
