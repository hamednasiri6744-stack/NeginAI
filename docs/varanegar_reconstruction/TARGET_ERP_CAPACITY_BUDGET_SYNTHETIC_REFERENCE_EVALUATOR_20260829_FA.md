# Reference Evaluator مصنوعی Capacity Budget مقصد

Evaluator خالص و بدون I/O برای parent/child timeout، retry safety/budget، inflight، queue backpressure، dependency circuit، degradation invariant و recovery drain/reconciliation ساخته شد.

شش مسیر مثبت Capacity/Backpressure/Retry/Circuit/Degradation/Recovery و سیزده Mutation منفی، جمعاً ۱۹/۱۹، PASS است. Blocking unknown و Unknown commit پیش از retry و سایر تصمیم‌ها بررسی می‌شوند.

Child budget از Parent عبور نمی‌کند؛ Retry بدون idempotency/backoff/jitter یا پس از budget رد می‌شود. Degradation ناقض invariant و Recovery پیش از drain/reconciliation Outcome مستقل دارند.

فقط budget/count/boolean/state مصنوعی پردازش شد. هیچ Traffic/Metric/Queue/Resource عملیاتی خوانده و هیچ Load/Fault/Overload اجرا نشد؛ Reference implementation یک و Operational implementation/Receipt/Readiness صفر است.
