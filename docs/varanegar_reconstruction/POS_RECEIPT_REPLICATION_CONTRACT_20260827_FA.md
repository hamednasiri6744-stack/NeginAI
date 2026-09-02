# قرارداد Batch دریافت و Replication رسیدهای POS در ERP مقصد

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS — طراحی مقصد؛ اجرا، UAT، پایلوت و Production صفر**

این قرارداد جایگزین پورت مستقیم `usp_ReplicateSalesReceipt` است. Procedure Legacy
به ۶۶ Dependency و ۱۷ Mutation candidate وصل است؛ مقصد آن را به Batch قابل
Resume، Command مستقل هر رسید، Crosswalk، Quarantine و Reconciliation می‌شکند.

## State machine Batch

`RECEIVED → VALIDATING → READY_TO_APPLY → APPLYING → RECONCILING`

حالت‌های نهایی:

- `ACCEPTED`: همه Receiptهای واجد شرایط Reconcile شده‌اند؛
- `PARTIALLY_QUARANTINED`: اثرهای پذیرفته‌شده برابرند و هر مورد دیگر پرونده
  Quarantine کامل دارد؛
- `BLOCKING_UNKNOWN`: نتیجه Commit/Response یا اختلاف نامعلوم است و Acceptance
  ممنوع می‌ماند؛
- `REJECTED`: Batch پیش از هر نتیجه پذیرفته‌شده رد شده است.

از `BLOCKING_UNKNOWN` فقط با شاهد فقط‌خواندنی تازه می‌توان به `RECONCILING`
بازگشت؛ زمان‌بندی یا Retry کور اجازه Acceptance نمی‌دهد.

## Idempotency هر رسید

کلید پایدار:

`source_system + source_session_id + source_receipt_id + source_receipt_version`

Payload hash بخشی از Receipt فرمان است. همان کلید با Payload متفاوت Conflict
می‌گیرد؛ Retry همان Payload نتیجه اصلی را برمی‌گرداند و هیچ Order/Return/Payment/
Voucher/Credit/Session effect تکراری نمی‌سازد.

## شش مرز اثر

1. Order/Sale زیر مالکیت `sales`؛
2. Sales return زیر مالکیت `sales`؛
3. Payment/Allocation زیر مالکیت `receivables_treasury`؛
4. Inventory voucher زیر مالکیت `inventory`؛
5. Credit consumption/reversal زیر مالکیت `receivables_treasury`؛
6. Session status به‌عنوان Projection قابل Rebuild.

هر Aggregate یک Transaction محلی Event/Current-pointer/Outbox دارد. اثر میان
ماژول‌ها با Inbox idempotent اعمال می‌شود؛ Dual write و Transaction توزیع‌شدهٔ
مبهم پذیرفته نیست.

## نه Reconciliation اجباری

- تعداد Receipt بر حسب Batch/Type؛
- Gross/Discount/Net amount بر حسب Currency/Type؛
- یکتایی Source-target crosswalk؛
- تعداد Sale/Return/Payment/Voucher ساخته‌شده؛
- Payment allocation و Credit balance؛
- Inventory ledger/projection؛
- Duplicate effect count؛
- Outbox/Inbox delivery؛
- کامل‌بودن Quarantine همه موارد غیرپذیرفته.

همه Checkها Blocking هستند؛ Difference بدون Evidence/Owner/Reason قابل قبول
نیست.

## مرز منبع

Ingest فقط Staging تغییرناپذیر محلی مقصد می‌سازد. هیچ ACK، Status update یا
Write به وارانگار انجام نمی‌شود. هر Integration write-back آینده Scope و مجوز
جدا می‌خواهد و در این قرارداد مجاز نشده است.

## Gate پیاده‌سازی

- ۲۰ Golden case این Command باید در Target harness ایزوله executable شود؛
- Fault در Batch/Receipt/Crosswalk/Outbox باید به یک نتیجه یا Quarantine صریح
  همگرا شود؛
- Duplicate delivery موازی باید صفر اثر تکراری بدهد؛
- نه Reconciliation check اختلاف نامعلوم صفر داشته باشند؛
- Role/Scope UAT، Performance، Restore و Expected value مالک کسب‌وکار تأیید شوند.

Artifact:
`artifacts/varanegar_analysis/ui/negin_erp_pos_receipt_replication_contract_20260827.json`

Builder:
`scripts/windows/build_negin_erp_pos_receipt_replication_contract.py`
