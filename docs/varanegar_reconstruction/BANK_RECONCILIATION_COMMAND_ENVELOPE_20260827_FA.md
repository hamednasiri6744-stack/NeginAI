# Command envelope مقصد مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS طراحی؛ پنج Command هنوز مسدود و پیاده‌سازی‌نشده‌اند**

## نتیجه

Match، Unmatch، Confirm، Cancel و Reverse یک Envelope مشترک دارند: ده Field
درخواست، ده Guard ترتیبی، نه Field پاسخ، یازده Error پایدار و دوازده Invariant.
هر Command Capability و State مستقل و Mutation set اتمیک خود را دارد.

ترتیب Guard از Authentication/Capability/Feature/Scope/OperationDate شروع می‌شود،
سپس Version/Idempotency/State/Domain را داخل Transaction کنترل و Mutation، Audit
و Outbox را یک‌جا Commit می‌کند. Scope denial وجود Aggregate را افشا نمی‌کند و
Repository مجاز به Commit مستقل نیست.

Errorهای مقصد پایدارند و شماره خطا، نام Procedure، SQL خام یا Exception payload
Legacy را به API نشت نمی‌دهند. Retry پاسخ مبهم نتیجهٔ Commit قبلی را برمی‌گرداند
و همان Key با Payload متفاوت Conflict است.

این Contract اجازهٔ شروع Command نمی‌دهد: ۱۱۶ Acceptance case اجراشده صفر، هفت
تصمیم مالک تأییدشده صفر، Runtime parity/UAT/Failure injection نیز بازند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/negin_erp_bank_reconciliation_command_envelope_20260827.json`
- `scripts/windows/build_negin_erp_bank_reconciliation_command_envelope.py`
- `tests/test_varanegar_ui_evidence.py`

Source وارانگار در تمام این طراحی فقط‌خواندنی مانده است.
