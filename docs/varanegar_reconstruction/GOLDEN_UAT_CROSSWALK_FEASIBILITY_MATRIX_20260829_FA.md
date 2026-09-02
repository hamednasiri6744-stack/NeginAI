# ماتریس امکان‌سنجی Crosswalk کیس‌های Golden/UAT ـ ۲۰۲۶-۰۸-۲۹

Baseline پنج ماژول unresolved از هفت منبع Case-level بازسازی شد: ۵۱۱ Case و ۵۱۱ Case ID یکتا. مجموعهٔ جدید نمایندگی‌شده ۳۰۲ Case یکتا دارد.

فقط ۶۴ Case قیمت‌گذاری Exact-ID reuse هستند. در Distribution، Treasury، Accounting و Reporting هم‌پوشانی Exact-ID صفر است. ۳۰ ردیف با `casefold(action)+kind` هم‌پوشانی کاندید دارند، اما این تطبیق معادل‌بودن شرط، Outcome، Assertion یا Effect را ثابت نمی‌کند.

۴۴۷ Case baseline و ۲۳۸ Case جدید unmatched باقی مانده‌اند. برای هر ماژول سه Packet لازم است: Alias map نسخه‌دار، disposition معادل‌بودن سطح Case و تعیین حالت `EXACT_NEW/EXACT_REUSE/SEMANTIC_REPLACEMENT/DEPRECATED/UNRESOLVED`. تا پذیرش این Packetها، additive count صفر و lower bound طراحی ۱۴۰۴ ثابت است.

هیچ Case اجرا یا تأیید نشده و هیچ Runtime parity، Command readiness یا Pilot readiness ایجاد نشده است.
