# Playbook تخصصی هویت و مجوزدهی

هفت مسیر تشخیصی برای conflict allow/deny، endpoint بدون تصمیم نام‌دار، admin bypass، cross-owner scope، نشست پس از revoke، assignment ناقص و SoD/break-glass تعریف شده است.

هر مسیر نه گام evidence-first دارد و فقط از policy/assignment/session epoch و receiptهای hash‌شده استفاده می‌کند. نتیجه یکی از `NATURAL_BEHAVIOR/DATA_DEBT/BUG/UNPROVEN` است. تشخیص پیش از هر grant، revoke، role edit، session invalidation، token access، impersonation یا repair متوقف می‌شود.

این Playbook هیچ رخداد واقعی را تشخیص نداده و هیچ هویت، credential یا grant مؤثر فعلی را ادعا نمی‌کند.
