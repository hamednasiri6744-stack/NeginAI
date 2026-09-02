# Runbook اجرای UAT احراز‌شدهٔ مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS طراحی؛ حساب تست Provision نشده و اجرای UAT صفر است**

## نتیجه

صد Case بدون هویت اکنون در پنج Wave قابل اجرا هستند: ۴۲ Assignment، ۳۰ Context،
۱۵ State/Profile، هفت SoD و شش Non-inference. هفت Principal slot همهٔ شش Role
و یک Deny baseline را پوشش می‌دهد؛ Artifact فقط Slot را نگه می‌دارد و نگاشت به
هویت واقعی فقط هنگام اجرای مجاز داخل Identity provider/Secret store انجام می‌شود.

پانزده Fixture slot برای Scope داخل/خارج، تاریخ باز/بسته، Fiscal/DC درست/غلط،
Feature روشن/خاموش، Version جاری/کهنه، Profile approved/unapproved و Stateها
تعریف شد. Evidence سیزده Field امن دارد و ذخیرهٔ نام/ایمیل/Personnel id، Credential،
SQL/Stack trace، Account/Amount/Business ID یا Screenshot آلوده ممنوع است.

هر نشت Scope، Mutation روی Deny، دورزدن SoD، اختلاف Audit/Outbox یا ثبت Evidence
ممنوع بلافاصله Waveهای بعد را متوقف می‌کند. Pilot فقط با Pass هر ۱۰۰ Case و
Signoff مالک مجاز است.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_authenticated_uat_runbook_20260827.json`
- `scripts/windows/build_negin_erp_bank_reconciliation_authenticated_uat_runbook.py`
- `tests/test_varanegar_ui_evidence.py`

این Runbook هیچ حساب، Grant، Credential، Fixture تجاری یا Command واقعی نمی‌سازد.
