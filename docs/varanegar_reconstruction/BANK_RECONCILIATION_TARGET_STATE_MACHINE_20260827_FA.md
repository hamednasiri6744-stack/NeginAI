# State machine مقصد مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS طراحی؛ Transitionها هنوز پیاده‌سازی یا Owner-approved نشده‌اند**

## نتیجه

Lifecycle Header از پیشرفت Match جدا شد. پنج State عبارت‌اند از
`OPEN_UNCONFIRMED`، `CONFIRMED`، `CANCELLED`، `REVERSED` و `QUARANTINED`؛ چهار
مقدار Progress محاسبه‌شده از بدون Link تا Ready/Ambiguous داریم. Match/Unmatch
فقط Progress را تغییر می‌دهند و State Header را دست نمی‌زنند.

هفت Transition/Capability جدا برای Import، Match، Unmatch، Confirm، Cancel،
Reverse و Quarantine ثبت شد. Cancel با Unmatch/Discard/Reverse یکی نیست و Reverse
Capability و SoD مستقل دارد. `CANCELLED/REVERSED` Stateهای مقصدند و از Markerهای
Legacy استنتاج نمی‌شوند.

Confirm باید همهٔ Linkها را پیش از Mutation اعتبارسنجی و همه Instrumentها را در
یک Transaction Update کند. Marker ناسازگار، Typed reference صفر/چندتایی یا
Confirmed/Instrument mismatch به Quarantine می‌رود.

تصمیم‌های `BR-DEC-006/007` برای Reverse و Cancel هنوز بازند؛ پیش‌فرض محافظه‌کارانه
توصیه است نه Approval. ۱۴ Invariant و ۱۸ Acceptance obligation این مرزها را حفظ
می‌کنند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_state_machine_contract_20260827.json`
- `scripts/windows/build_negin_erp_bank_reconciliation_state_machine_contract.py`
- `tests/test_varanegar_ui_evidence.py`

هیچ Transition، UI action، DB command یا هویت واقعی در این Builder اجرا/خوانده
نشده است.
