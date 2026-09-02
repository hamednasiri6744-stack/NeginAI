# Reference Evaluator مصنوعی Numbering مقصد

Evaluator خالص و بدون I/O برای Scope/Series/Fiscal، Idempotency، Unknown commit، Sequence/Fencing، Draft/Reserve/Commit، Void، Offline range و Rollover ساخته شد.

هفت مسیر مثبت و سیزده Mutation منفی، جمعاً ۲۰/۲۰، PASS است. Replay پیش از Version و Unknown commit پیش از Allocation ارزیابی می‌شود؛ Draft شماره تخصیص نمی‌دهد.

Reservation منقضی بدون Void رد و با Void به Gap ledger می‌رود. Offline range خارج مرز/منقضی/هم‌پوشان و Rollover با Reservation باز یا Gap reconcileنشده رد می‌شود.

فقط State/Version/Number/Range مصنوعی پردازش شد. هیچ شماره یا سری عملیاتی خوانده و هیچ Reserve/Commit/Void/Rollover اجرا نشد؛ Reference implementation یک و Operational implementation/Receipt/Readiness صفر است.
