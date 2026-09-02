# ارزیاب مرجع مصنوعی ساخت و MRP

این ارزیاب pure و قطعی PLAN، RELEASE، MATERIAL، OUTPUT، QUALITY، COST و RECONCILE را فقط با booleanهای مصنوعی می‌سنجد. هیچ BOM/routing/order/material/WIP/quality/cost/ledger عملیاتی خوانده یا تغییر داده نشده است.

schema/scope، version/idempotency، unknown commit و blocking unknown مقدم‌اند؛ سپس BOM/routing و pegging، order approval، material/WIP balance، yield/genealogy/quality، cost version/period و WIP/GL reconciliation fail-closed ارزیابی می‌شوند.

هفت مسیر مثبت و ۱۹ مسیر منفی، جمعاً ۲۶ بردار، باید outcome دقیق بسازند. provider و command/pilot readiness صفر است.
