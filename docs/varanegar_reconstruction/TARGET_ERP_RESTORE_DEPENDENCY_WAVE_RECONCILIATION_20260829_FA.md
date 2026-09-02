# قرارداد موج‌های وابستگی و تطبیق بازیابی ERP مقصد

## هدف

این بسته DAG وابستگی چهارده ماژول Blueprint را به ترتیب صریح بازیابی تبدیل می‌کند تا «بالا آمدن سرویس» یا «بارگذاری schema» به‌اشتباه موفقیت Restore تلقی نشود. این سند فقط طراحی provider-neutral و قابل‌بازتولید است؛ هیچ Backup خوانده نشده، هیچ Restore/Replay/Failover اجرا نشده و هیچ RPO/RTO، Stack، Storage یا مالک واقعی انتخاب نشده است.

## پوشش

- چهارده ماژول و ۳۸ Edge وابستگی در هفت موج Restore قرار گرفته‌اند؛ `platform` تنها عضو موج صفر است.
- هر Edge بالادست باید در موجی زودتر باشد و پیش از Restore وابسته، وضعیت reconcileشده و Receipt معتبر داشته باشد.
- ده مرحله برای هر ماژول، یعنی ۱۴۰ انتساب، از pin کردن مرز بازیابی تا بازبینی مستقل پیش از enablement تعریف شده است.
- چهار بُعد تطبیق برای هر ۳۸ Edge، یعنی ۱۵۲ انتساب، reference/pointer، aggregate/hash، replay/watermark و invariant مالی/عملیاتی را پوشش می‌دهد.
- چهارده Gate برای هر هفت موج، یعنی ۹۸ انتساب، و پنج Role برای هر موج، یعنی ۳۵ انتساب، تعریف شده است.
- Receipt تطبیق بیست فیلد و نتیجه نه‌حالته دارد؛ هیچ Receipt واقعی یا مقدار تجاری در Artifact نگهداری نشده است.

## قواعد fail-closed

- Dependency باید قبل از Restore ماژول وابسته reconcile شود؛ شروع شدن یا schema load کافی نیست.
- Read model منبع authoritative بازیابی نیست و فقط از state authoritative بازسازی می‌شود.
- Replay پیش از تطبیق Idempotency/Inbox/Outbox ممنوع است.
- `blocking_unknown`، اختلاف بازبینی‌نشده یا Receipt stale/revoked مانع Wave promotion و Service enablement است.
- موازی‌سازی فقط درون یک موج و میان ماژول‌های بدون Edge وابستگی مجاز است.
- Restore در Production و Promotion/Enablement خودکار ممنوع است.

## وضعیت فعلی

هر هفت موج `NOT_STARTED_NO_AUTHORIZED_REHEARSAL`، همهٔ ۱۴۰ Stage `UNEXECUTED`، همهٔ ۳۸ Edge `UNRECONCILED_NO_RESTORE_EVIDENCE`، تمام ۹۸ Gate `UNMET` و هر ۳۵ Role `UNASSIGNED` است. Restore، Reconciliation، Approval، Service enablement، Recovery readiness، Command readiness و Pilot readiness همگی صفر مانده‌اند. پایهٔ ریسک/ردیابی ۸۴/۳۴۳ و lower bound طراحی ۱۴۰۴ تغییر نکرده است.
