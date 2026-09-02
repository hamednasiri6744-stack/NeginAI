# ارزیاب مرجع مصنوعی فروش تا وصول

این ارزیاب pure و قطعی فقط ورودی‌های boolean و عملیات مصنوعی ORDER، FULFILL، INVOICE، RETURN، CASH، ALLOCATE، COLLECT، REVENUE و RECONCILE را ارزیابی می‌کند. هیچ داده عملیاتی خوانده یا تغییر داده نشده است.

precedence با schema/scope، سپس version/idempotency، unknown commit و blocking unknown آغاز می‌شود. credit breach، delivery بدون allocation/credit، invoice یا return بدون lineage، cash مبهم، allocation نامتوازن، collection بدون approval، aging/ECL یا revenue بدون cutoff/period و AR/GL mismatch همگی fail-closed هستند.

نه مسیر مثبت و ۱۹ مسیر منفی، جمعاً ۲۸ بردار، باید outcome دقیق بسازند. این مرجع provider یا سامانه عملیاتی نیست و command-ready/pilot-ready همچنان صفر است.
