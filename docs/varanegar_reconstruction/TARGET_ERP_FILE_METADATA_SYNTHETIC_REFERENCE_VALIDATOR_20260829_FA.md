# Reference Validator مصنوعی File Metadata مقصد

Validator خالص و بدون I/O روی Metadata ثابت، Name/path، Size، Digest، Declared/Detected MIME، Archive limits، Scanner/DLP، Quarantine access، Download authorization، Derivative lineage، Formula injection و Retention را ارزیابی می‌کند.

پنج مسیر حفاظتی/مثبت و چهارده Mutation منفی، جمعاً ۱۹/۱۹، PASS است. Scanner Unknown به Quarantine و هر Access به فایل Quarantine‌شده به `QUARANTINED_ACCESS_BLOCKED` می‌رود.

Path traversal، Size/Hash/MIME mismatch، Archive unsafe، Download بدون Auth/TTL، Derivative بدون digest مستقل، Formula injection و Retention stale Outcome جدا دارند.

هیچ byte فایل، archive، document یا payload باز نشد. فقط metadata مصنوعی پردازش شد؛ Reference implementation یک و Operational scanner/parser/receipt/readiness صفر است.
