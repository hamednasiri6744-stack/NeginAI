# قرارداد Role/UAT بدون هویت برای مغایرت بانکی

## نتیجه

هفت Capability مغایرت بانکی به شش Role template پیشنهادی و ۱۰۰ Case مصنوعی
وصل شد. این خروجی برای جلوگیری از برداشت نادرست از Permissionهای Legacy است؛
هیچ هویت، عضویت گروه، حق فردی، حساب واقعی یا Credential استفاده نشده و هیچ UAT
احراز هویت‌شده اجرا نشده است.

وضعیت: `DESIGN_ONLY_NOT_AUTHENTICATED_OR_EXECUTED`.

## Capabilityها

- `bank_reconciliation.view`
- `bank_reconciliation.import_statement`
- `bank_reconciliation.match_instrument`
- `bank_reconciliation.unmatch_instrument`
- `bank_reconciliation.confirm`
- `bank_reconciliation.cancel`
- `bank_reconciliation.reverse_confirmed_session`

Aliasهای `TransferList` و `ReconciliationSetup` فقط شاهد Legacy هستند. `Edit`
حق Confirm و `Delete` حق Cancel یا Reversal نمی‌سازد. Capability هفتم Target-only
است و از نیاز Reversal ممیزی‌شده می‌آید، نه از Alias مجوز Legacy.

## Role templateهای پیشنهادی

| Role | Allow پیشنهادی |
|---|---|
| bank_reconciliation_viewer | view |
| bank_statement_importer | view, import_statement |
| bank_reconciliation_matcher | view, match_instrument, unmatch_instrument |
| bank_reconciliation_confirmer | view, confirm |
| bank_reconciliation_supervisor | view, cancel موقت |
| bank_reconciliation_reversal_authorizer | view, reverse_confirmed_session موقت |

تمام Roleها `NOT_APPROVED` هستند. نقش Supervisor، Reversal authorizer و خود
Cancel/Reverse تا تأیید مالک فرایند provisional هستند.

## UAT ساخته‌شده

- ۴۲ Case تصمیم Allow/Deny برای شش Role × هفت Capability؛
- ۳۰ Case منفی Context برای Account scope، OperationDate بسته، Fiscal/DC غلط،
  optimistic version کهنه و entitlement خاموش؛
- ۱۵ Case State/Profile شامل Confirm/Reverse marker ناقص، Profile تأییدنشده، تغییر نسخه
  پس از Preview، ورودی SQL/provider/path، فرمت جعلی و parity تأییدنشده؛
- هفت Case تضاد وظیفه؛
- شش Case منع استنتاج از Legacy؛
- جمعاً ۱۰۰ Case، بدون شناسه تکراری.

تصمیم Authorization مقصد:

```text
Capability
AND Feature entitlement
AND Fiscal/DC/BankAccount scope
AND OperationDate
AND State transition
AND Domain validation
```

Deny بر Allow مقدم است و Neutral به معنی Allow نیست. Allow یک Role هیچ‌کدام از
Guardهای Context/State را دور نمی‌زند.

## SoD پیشنهادی

برای یک Session/Batch یکسان، این ترکیب‌ها فعلاً نیازمند Deny یا Exception policy
تأییدشده‌اند:

- Importer و Confirmer؛
- Matcher و Confirmer؛
- Unmatcher و Confirmer؛
- Confirmer و Canceller.
- Importer، Matcher یا Confirmer و Reversal authorizer روی همان Session.

این قواعد پیشنهاد کنترلی هستند، نه سیاست مصوب. مالک کسب‌وکار و Security owner
باید expected result و exception flow را تأیید کنند.

## چه چیزی هنوز اثبات نشده است؟

- شمارش Aggregate مجوز Legacy، دسترسی هیچ فرد خاصی را ثابت نمی‌کند؛
- شش Role هنوز به حساب تست واقعی Assignment نشده‌اند؛
- Account-scope fixture، نقش‌های واقعی و Expected result مصوب نداریم؛
- authenticated UAT، Pilot و Production assignment همگی صفرند.

برای UAT واقعی باید حساب‌های تست تفکیک‌شده، Scopeهای داخل/خارج، تاریخ باز/بسته،
Sessionهای هر State و Profileهای approved/unapproved در محیط مقصد ایزوله ساخته
شوند؛ سپس همین Caseها اجرا و evidence نتیجه نگهداری شود.

## بازتولید

```powershell
.\.venv\Scripts\python.exe scripts\windows\build_negin_erp_bank_reconciliation_role_uat.py `
  --permission-catalog artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_permission_catalog_20260827.json `
  --matching-boundary artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_matching_boundary_20260827.json `
  --profile-state-boundary artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_profile_state_boundary_20260827.json `
  --golden-cases artifacts\varanegar_analysis\ui\negin_erp_bank_reconciliation_golden_cases_20260827.json `
  --general-role-uat artifacts\varanegar_analysis\ui\negin_erp_role_uat_cases_20260827.json `
  --output artifacts\varanegar_analysis\ui\negin_erp_bank_reconciliation_role_uat_20260827.json
```
