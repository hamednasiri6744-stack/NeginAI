# Reference Evaluator مصنوعی Inventory/Costing

این evaluator فقط Boolean/Operation مصنوعی را پردازش می‌کند و هیچ item/lot/serial/quantity/cost/value/ledger عملیاتی را نمی‌خواند یا تغییر نمی‌دهد.

ترتیب تصمیم Schema، Scope، Lot/Serial/Date، Version/Idempotency، Unknown commit، State/Quantity، Negative policy، Unknown، Expiry/Quarantine، Cost layer، Landed cost، Transfer، Count، Revalue و Reconciliation است.

هفت مسیر مثبت و بیست‌ویک mutation منفی تعریف شده‌اند. Unknown commit، expired allocation، negative policy، cost-layer lineage/quantity، transfer ownership، count approval و stock-cost-GL reconciliation fail-closed هستند.

Operational implementation/read/run/receipt و Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
