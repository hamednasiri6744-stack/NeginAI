# Playbook کارشناسی قواعد قیمت‌گذاری — ۲۰۲۶۰۸۲۹

هفت Playbook برای ابهام اولویت، شکست Publish پس از Validation، اختلاف SQL Legacy و DSL مقصد، برخورد تخصیص Linear Discount، از دست‌رفتن Provenance در Delete/Close، Explain‌ناپذیری قیمت، و نتیجهٔ نامعلوم Replication ساخته شد.

الگوی ثابت تشخیص: هویت Command/Version/Policy را بدون متن خام Rule ثبت کن؛ Hashها را کنترل کن؛ Aggregate/Compile/Calculation/Audit/Outbox/Receipt را جدا بخوان؛ Qualification و Precedence را از ورودی نوع‌دار بازسازی کن؛ نتیجه را یکی از `NATURAL_BEHAVIOR / DATA_DEBT / BUG / UNPROVEN` اعلام کن؛ و قبل از هر Publish، Close، Retry یا Repair متوقف شو. این Playbookها هیچ Incident واقعی را تشخیص نداده‌اند.
