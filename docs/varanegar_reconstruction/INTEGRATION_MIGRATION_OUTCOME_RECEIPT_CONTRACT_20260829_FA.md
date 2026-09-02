# قرارداد Outcome و Receipt در Integration/Migration — ۲۰۲۶۰۸۲۹

شش قرارداد مقصد برای POS Receipt، NGT Sale، NGT Payment، Compensation، Rule Package و Migration Slice ساخته شد. مراحل `STAGED / VALIDATED / READY_TO_APPLY / APPLIED / RECONCILED / ACKNOWLEDGED / QUARANTINED_OR_UNKNOWN` مستقل‌اند و موفقیت Transport یا اجرای Script به‌تنهایی Ack کسب‌وکاری نیست.

Package/Capture identity، Content hash، Scope، Sequence و Previous-receipt hash immutable هستند. هر Item و هر اثر Cross-module Receipt جدا دارد. Crosswalk write-back نتیجهٔ مستقل است؛ Ack فقط پس از Reconciliation بدون اختلاف ناشناخته یا Quarantine کامل صادر می‌شود. Compensation یک فرمان append-only است و History اصلی را حذف نمی‌کند. Migration تنها از Checkpoint پایدار Slice قبلی Resume می‌شود.

۳۴ Case موجود reuse شدند: ۲۰ POS، هفت NGT Payment و هفت Rule publication. شش Gate Transport شامل Authentication، Receipt idempotency، Ordering/Gap، Center scope، Quarantine/Retry و Rollback observability هنوز اثبات‌نشده‌اند. هیچ Package، FTP، Snapshot، Import یا Procedure اجرا نشده است.
