# Comparator معنایی Action Aliasهای P1 ـ ۲۰۲۶-۰۸-۲۹

چهار نگاشت صریح command-to-capability بانکی به ۵۵ جفت Case هم‌نوع تبدیل شد: Authorization پنج، Concurrency هفت، Failure Injection نوزده، Idempotency یازده، Scope نه و Success چهار جفت.

با وجود lineage نام‌گذاری صریح در state-machine، exact precondition، exact outcome، exact assertion-list و full exact همگی صفر است. بنابراین نگاشت‌های `CancelSession`، `ConfirmSession`، `MatchInstrument` و `UnmatchInstrument` هنوز فقط کاندید reuse هستند و Semantic equivalence ثابت نشده است.

هیچ Candidate یا Case-pair پذیرفته نشد؛ UAT اجرا، Owner approval، اثر افزایشی، command-ready و pilot-ready صفر است و lower bound طراحی ۱۴۰۴ و پایهٔ Risk/Trace برابر ۸۴/۳۴۳ باقی می‌ماند. مرحلهٔ بعد باید ۱۹ جفت Failure Injection و سپس ۳۶ جفت کنترل را با واژگان Outcome و خانواده‌های Effect تفکیک کند.
