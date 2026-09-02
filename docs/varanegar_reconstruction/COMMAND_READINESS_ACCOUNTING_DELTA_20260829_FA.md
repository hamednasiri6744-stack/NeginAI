# Delta آمادگی فرمان — حسابداری — ۱۴۰۵/۰۶/۰۷

برای حفظ زنجیرهٔ بدون چرخه، ledger تاریخی ۱۴ماژولی دست‌کاری نشد. این delta فقط یک تغییر را ثبت می‌کند: `accounting.outcome_retry_idempotency.target_contract` از `false` به `true` رسید، چون inventory اصلاح‌شده شش مسیر و outcome/retry design آن‌ها را مستند کرده است.

تعداد ماژول‌های دارای outcome contract طراحی‌شده از سه به چهار رسید. runtime proof، command-ready و pilot-ready همچنان صفرند. این ارتقای پوشش طراحی است، نه مجوز پیاده‌سازی یا اجرای فرمان.
