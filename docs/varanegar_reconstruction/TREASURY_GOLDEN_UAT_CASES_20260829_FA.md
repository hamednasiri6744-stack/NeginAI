# Golden/UAT خزانه — ۱۴۰۵/۰۶/۰۷

برای ۱۲ فرمان envelope خزانه، ۸۴ case طراحی شد: denial، stale version، duplicate command id، fault injection، scope، success و یک حالت ویژه برای هر فرمان.

حالت‌های ویژه، اختلاف receipt/detail، branch Undo، نبود transaction اثبات‌شده در Delete، underallocation، crosswalk partial write، tolerance تطبیق بانکی، scope لینک، partial confirm، سیاست Cancel و separation-of-duties در reversal را پوشش می‌دهند. Outcomeهای `REJECTED_WITH_DURABLE_EFFECT` و `UNKNOWN_REQUIRES_READBACK` صریحاً آزمون‌پذیر شده‌اند.

هر ۸۴ مورد `DESIGNED_NOT_EXECUTED` است. اجرای runtime، نتیجهٔ قبول‌شده و owner approval صفر است و تنها محیط مجاز، target ایزوله با دادهٔ مصنوعی و fault injection خواهد بود.
