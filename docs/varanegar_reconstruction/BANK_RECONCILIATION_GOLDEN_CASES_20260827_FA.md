# Golden caseهای مغایرت بانکی ERP نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۹۳ Case مصنوعی PASS از نظر ساخت؛ Commandهای مقصد هنوز پیاده‌سازی نشده‌اند**

## پوشش

برای پنج Command زیر ۹۳ Acceptance case بدون اجرای Source/Target ساخته شد:

- `bank_reconciliation.import_statement`؛
- `bank_reconciliation.match_instrument`؛
- `bank_reconciliation.unmatch_instrument`؛
- `bank_reconciliation.confirm`؛
- `bank_reconciliation.cancel`.

ترکیب Caseها:

- ۴۰ Case مشترک Success/Auth/Scope/Version/Idempotency/Context/Reconciliation؛
- ۱۵ Failure injection در نقاط Parse، Write، State، Cardex و Outbox؛
- ۳۰ Case دامنه‌ای شامل فایل جعلی/فرمت نامعتبر، Profile تأییدنشده، Parser fault،
  لینک صفر/چندSource، Cross-account، Match رقابتی، Date/Amount mismatch، Session
  تأییدشده، Cardex mismatch، ردیف Quarantine و Cancel ناقص؛
- ۸ Case برابری اثر پس از Commit برای موجودیت‌های وابسته به ثبت کاردکس.

هر Case الزام می‌کند Source وارانگار دست‌نخورده بماند. محیط مجاز فقط دیتابیس
آزمایشی ایزوله با Fixture مصنوعی است؛ Clone و Production صریحاً ممنوع‌اند.

## مرز آمادگی

PASS فعلی یعنی Caseها یکتا، کامل و قابل‌ردیابی‌اند؛ به معنی وجود API، Transaction،
Parser یا UI مقصد نیست. مالک فرایند کاندید `P06_COLLECTION_AND_RECEIVED_CHEQUE`
است و پیش از اتصال به Process Atlas نیازمند تأیید کسب‌وکار است.
نام `bank_reconciliation.cancel` نیز provisional است: شاهد Legacy فعلی فقط
Unmatch لینک و Discard ردیف Import را اثبات می‌کند، نه Cancel مستقل Session.
بنابراین این Caseها تا sign-off مالک نباید به API عملیاتی تبدیل شوند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_golden_cases_20260827.json`
- `scripts/windows/build_negin_erp_bank_reconciliation_golden_cases.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\build_negin_erp_bank_reconciliation_golden_cases.py `
  --source-model G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_source_model_20260827.json `
  --command-guards G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_command_guards_20260827.json `
  --import-boundary G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_statement_import_boundary_20260827.json `
  --transaction-boundary G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_transaction_boundary_20260827.json `
  --cardex-sql-boundary G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_cardex_sql_boundary_20260827.json `
  --delete-semantics G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_delete_semantics_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\negin_erp_bank_reconciliation_golden_cases_20260827.json
```
