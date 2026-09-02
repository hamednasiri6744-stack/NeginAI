# قرارداد مقصد Parser و Staging صورت‌حساب بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS طراحی؛ هنوز Parser/Storage/Command پیاده‌سازی نشده است**

## نتیجه

Slice دوم مجاز با چهار Entity/۴۰ Field، هشت State، هشت مرحله Pipeline، چهارده
Invariant، شش Command و شانزده تعهد Acceptance بسته شد. Parsing فقط در Worker
محدود و Staging ایزوله انجام می‌شود؛ تا Commit صریح و موفق هیچ Header یا Row
عملیاتی ساخته نمی‌شود.

Pipeline از Upload bounded و Hash شروع می‌شود، Signature/Format و Profile
Approved را کنترل می‌کند، شش ستون Canonical را Parse/Validate می‌کند، Diagnostic
پایدار و Preview hash-bound می‌سازد و فقط سپس Header/Rows/Audit/Outbox را در یک
Transaction مقصد Commit می‌کند.

SQL خام، Provider، Connection string، Office automation، Shell و Path تنظیمی
هیچ‌وقت اجرا نمی‌شوند. Dedup به Account/ProfileVersion/SourceHash/Ordinal و مقادیر
Canonical scoped است؛ Replay همان نتیجه را برمی‌گرداند.

تصمیم‌های `BR-DEC-002/003/004` هنوز `NOT_APPROVED` هستند: Debit+Credit هم‌زمان،
مبلغ صفر و Optionهای HDR/StartRow/Separator/TextDirection هیچ رفتار پنهانی ندارند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_statement_staging_target_contract_20260827.json`
- `scripts/windows/build_negin_erp_bank_statement_staging_target_contract.py`
- `tests/test_varanegar_ui_evidence.py`

Clone فعلی Profile/Statement واقعی برای Parity ندارد و این سند Runtime readiness
یا مجوز Pilot نیست.
