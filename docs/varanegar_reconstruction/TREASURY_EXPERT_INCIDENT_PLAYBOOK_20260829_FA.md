# Playbook تخصصی رخدادهای خزانه — ۱۴۰۵/۰۶/۰۷

شش رخداد تخصصی پوشش داده شد: نتیجهٔ مبهم Edit، Undo روی leaf اشتباه، Delete با نتیجهٔ ناشناخته، underallocation پرداخت تور، شکاف crosswalk پس از replication و Confirm ناقص تطبیق بانکی.

هر Playbook با capture بدون PII، کنترل drift، read-back aggregate/history/crosswalk/audit، مقایسه outcome با اثر durable، طبقه‌بندی چهارحالته و توقف پیش از repair کار می‌کند. خروجی تشخیص فقط `NATURAL_BEHAVIOR`، `DATA_DEBT`، `BUG` یا `UNPROVEN` است.

اعداد aggregate مثل ۵۷ underallocation و ۱۹ batch حذف receipt فقط شواهد کلون برای انتخاب شاخهٔ تشخیص‌اند، نه وضعیت زندهٔ تولید. هیچ رخداد واقعی تشخیص داده نشده، هیچ repair یا UAT اجرا نشده و owner approval صفر است.
