# ماتریس اعتبارسنجی Receiptهای شواهد Cross-Lane — ۲۰۲۶-۰۸-۲۹

این ماتریس ۲۹۰ requirement مدرک در صف intake را به ۲۹۰ slot مستقل تبدیل می‌کند. هر یک از ۲۹ مسیر دقیقاً ده slot دارد؛ توزیع چهار مسیر به‌ترتیب ۹۰، ۱۲۰، ۵۰ و ۳۰ slot است.

## قرارداد هر Receipt

هر مدرک باید چهارده metadata داشته باشد: شناسه و نوع receipt، مرجع و SHA-256 artifact، زمان و کلاس محیط جمع‌آوری، hash fixture/case-set، نقش تولیدکننده و بازبین مستقل، نسخهٔ سیاست، زمان انقضا، مرجع conflict/supersession، attestation حذف دادهٔ حساس و وضعیت validation.

ماشین وضعیت هشت حالت دارد: `MISSING`، `RECEIVED_UNVALIDATED`، `HASH_VALIDATED`، `CONTENT_VALIDATED`، `ROLE_ACCEPTED`، `REJECTED`، `EXPIRED` و `SUPERSEDED`. فقط `ROLE_ACCEPTED` اجازه می‌دهد آن slot در closure بعدی لحاظ شود؛ حتی آن نیز به‌تنهایی semantic closure یا readiness نیست.

Receipt می‌تواند چندکلاسه باشد؛ در مجموع ۱۴ slot چندکلاسه است. پنج receipt مرکب P3 با عنوان `failure_stage_and_per_item_outcome` هم‌زمان Transaction/Failure، Result/Render و Semantic/Effect هستند؛ بنابراین gateهای آن‌ها `CG-02/CG-03/CG-05/CG-04` است. با این اصلاح، ۲۷ slot از ۲۹۰ slot صریحاً تحت CG-05 قرار می‌گیرد و بخش per-item outcome دیگر در classifier تک‌کلاسه گم نمی‌شود.

## کنترل رد و ایمنی

چهارده کد رد، نبود یا عدم تطابق hash، frozen نبودن منبع، محیط نامشخص، نبود fixture hash، نقض تفکیک نقش، نسخهٔ سیاست نامشخص، انقضا، conflict/supersession حل‌نشده، وجود دادهٔ حساس خام، mismatch دامنهٔ gate، محتوای ناکافی و عدم بازتولیدپذیری را پوشش می‌دهد.

در artifact فعلی هر ۲۹۰ slot در وضعیت `MISSING` است و شمارش receipt دریافت‌شده، hash/content validated، role accepted، تصمیم بسته، اجرا، owner approval و readiness همگی صفر است. هیچ فرم، گزارش، procedure، اتصال دیتابیس یا اسمبلی اجرا نشده است.

Artifact:

`artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_matrix_20260829.json`

Checkpoint:

`artifacts/varanegar_analysis/varanegar_alias_cross_lane_evidence_receipt_validation_checkpoint_20260829.json`
