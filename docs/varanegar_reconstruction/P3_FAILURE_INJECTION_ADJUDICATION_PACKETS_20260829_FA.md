# داوری Failure Injection برای P3 ـ ۲۰۲۶-۰۸-۲۹

هجده جفت Failure Injection در پنج Packet و شش candidate report-command تفکیک شد. پانزده Case جدید شامل Render failure، Completion/receipt failure و Partial batch در برابر شش Case پایهٔ post-commit، file-creation و statement-transaction قرار گرفت؛ fault-stage دقیق صفر است.

هر ۱۸ جفت در baseline قرارداد retry/recovery و unknown/partial disposition دارد. ۱۵ جفت به Audit/Outbox و ۱۲ جفت به File/Print/Completion حساس است. این پوشش‌ها همسان نیستند و normalization خطا نباید مرز Render، Completion، فایل خارجی، تراکنش statement یا per-item outcome را حذف کند.

Outcome/assertion/full exact و acceptance صفر است؛ هیچ گزارش یا فرمانی اجرا نشده و Result parity ادعا نمی‌شود. lower bound طراحی ۱۴۰۴، Risk/Trace برابر ۸۴/۳۴۳ و readiness صفر باقی می‌ماند.
