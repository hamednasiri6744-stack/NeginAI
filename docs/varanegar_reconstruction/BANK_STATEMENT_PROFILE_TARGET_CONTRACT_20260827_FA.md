# قرارداد مقصد Profile صورت‌حساب بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS طراحی Schema/Command؛ هنوز پیاده‌سازی یا Approval نشده است**

## نتیجه

اولین Slice قابل‌ساخت مغایرت بانکی اکنون قرارداد دقیق دارد: سه Entity با ۲۹
Field، دوازده Invariant، چهار Command و دوازده تعهد Acceptance. این قرارداد از
Profile/State و Parser واقعی Legacy و بستهٔ تصمیم‌های باز ساخته شده، اما هیچ
Profile واقعی در Clone جاری ندارد و Migration یا Runtime implementation نیست.

## Aggregate مقصد

1. `BankStatementFormatProfile`: هویت family/version، Bank/AccountType، Parser
   typed، Stateهای Draft/Pending/Approved/Retired، بازهٔ اثر، Hash و Approval؛
2. `BankStatementFieldMapping`: نگاشت typed و مرتب‌شده به شش ستون Canonical
   `Date/Comment/Debit/Credit/No1/BaLance`؛
3. `BankStatementProfileParserOptions`: گزینه‌های typed برای Header/StartRow/
   Delimiter/TextDirection با وضعیت `INERT_PENDING_APPROVAL`.

هیچ Field برای SQL خام، Provider، Connection string، عبارت اجرایی یا مسیر فایل
وجود ندارد. Preview و Commit باید همان `profile_id/version/content_sha256` را
داشته باشند و نسخهٔ Approved یا استفاده‌شده immutable است.

## Command و Capability

| Command | Capability | Transition |
|---|---|---|
| CreateProfileDraft | profile.manage | → DRAFT |
| SubmitProfileForApproval | profile.manage | DRAFT → PENDING_APPROVAL |
| ApproveProfileVersion | profile.approve | PENDING_APPROVAL → APPROVED |
| RetireProfileVersion | profile.approve | APPROVED → RETIRED |

Submitter و Approver یک Actor نیستند. Capabilityها پیشنهاد مقصدند و هنوز
Role assignment یا Owner/Security approval ندارند.

## Gateهای مهم

- دقیقاً یک Mapping برای هر شش ستون Canonical؛
- حداکثر یک نسخهٔ Approved مؤثر برای Bank/AccountType در هر لحظه؛
- رد Version کهنه، Replay idempotent و رد تغییر Hash بین Preview و Commit؛
- HDR/StartRow/Seperator/IsArabic تا تأیید `BR-DEC-004` و تست Parser مربوط فعال
  نمی‌شوند؛ حضور ستون Legacy به معنی فعال بودن نیست؛
- Retirement تاریخچهٔ Importهای قبلی را تغییر نمی‌دهد.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_statement_profile_target_contract_20260827.json`
- `scripts/windows/build_negin_erp_bank_statement_profile_target_contract.py`
- `tests/test_varanegar_ui_evidence.py`

Builder فقط سه Artifact معتبر را ترکیب می‌کند و هیچ DB/UI/Command/Identity یا
دادهٔ کسب‌وکاری را نمی‌خواند یا تغییر نمی‌دهد.
