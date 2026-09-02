# قرارداد Data Provenance و Read-model Rebuild مقصد

دوازده Data class برای چهارده ماژول ۱۶۸ assignment، هشت Authority class تعداد ۱۱۲ و دوازده مرحلهٔ Rebuild lifecycle تعداد ۱۶۸ assignment دارد. Provenance receipt بیست‌وچهار، Rebuild receipt بیست‌ودو، Drift receipt بیست و Retention disposition هجده فیلد دارد.

چهارده Failure case تعداد ۱۹۶، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ assignment دارد. Read model، Cache، Report یا Export منبع حقیقت نیست؛ Direct repair ممنوع و Rebuild فقط از Authoritative source نسخه‌دار با Snapshot/Watermark معتبر مجاز است.

Gap/Overlap/Fork/Unknown و Partial rebuild، Read switch را می‌بندد. Replay نباید Effect تازه بسازد و ورودی/recipe/version یکسان باید Digest خروجی یکسان بدهد. Deletion نباید Retention مالی یا lineage tombstone را بشکند.

هیچ Dataset، Table، Row، Schema یا Sample عملیاتی خوانده نشد و هیچ Rebuild/Replay/Repair/Deletion/Read-switch اجرا نشد. Lineage/Drift/Approval/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
