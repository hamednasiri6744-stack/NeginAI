# ارزیاب مرجع مصنوعی دارایی ثابت

این ارزیاب pure و قطعی، CAPITALIZE، DEPRECIATE، IMPAIR، REVALUE، TRANSFER، DISPOSE و RECONCILE را فقط با booleanهای مصنوعی می‌سنجد. هیچ داده عملیاتی دارایی، ارزش، استهلاک، مالیات یا دفتر خوانده یا تغییر داده نشده است.

precedence از schema/scope/component، version/idempotency، unknown commit و blocking unknown به NBV invariant و سپس policy/period/lineage عملیات می‌رسد. NBV منفی، depreciation بیش از basis، CIP بدون lineage، روش یا دوره نامعتبر، impairment/revaluation بدون evidence، transfer خارج scope و disposal بدون derecognition همگی fail-closed هستند.

هفت مسیر مثبت و ۱۹ مسیر منفی، جمعاً ۲۶ بردار، باید outcome دقیق بسازند. provider، command-ready و pilot-ready همچنان صفر هستند.
