# قرارداد Version، Precedence و Rollout تنظیمات — ۲۰۲۶۰۸۲۹

پنج قرارداد مقصد برای General، Web Service، Accounting Article Template، Scoped Override و Rollback-by-new-version ساخته شد. مقدار Effective بدون `ResolutionTrace` معتبر نیست؛ Trace باید Candidate versionها، Scope match، تصمیم Null/Removed، Winner و Policy hash را ثبت کند.

Precedence مقصد بر پایهٔ Family، Scope specificity، Effective window، Published version و Stable version-id tie-breaker قطعی است. `TOP 1` بدون Order ممنوع است. Null برای هر Key یکی از `INHERIT / EXPLICIT_NULL / VALUE` است. Removed candidate انتخاب نمی‌شود، اما Reference فعال به آن تا تعیین Replacement قرنطینه می‌شود.

Secret value وارد Command، Result یا Audit نمی‌شود و فقط Vault reference دریافت می‌شود. Rollback تاریخچه را بازنویسی نمی‌کند؛ محتوای نسخهٔ قبلی را در Version تازه منتشر می‌کند و Ackهای ناموفق را حفظ می‌کند. هیچ فرم، Command، Secret access یا Consumer refresh اجرا نشده است.
