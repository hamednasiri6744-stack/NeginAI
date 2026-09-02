# Worklist نقش‌محور برای تحویل شواهد Cross-Lane — ۲۰۲۶-۰۸-۲۹

این بسته ۲۹ intake و ۲۹۰ receipt slot را بر اساس ۱۳ نوع نقش پاسخ‌گو گروه‌بندی می‌کند. چون هر Packet دقیقاً دو نقش دارد، مجموع assignmentها عمداً تکراری است: ۵۸ Packet assignment، ۴۰۶ Case assignment و ۵۸۰ receipt-slot assignment؛ مجموعهٔ زیربنایی همچنان فقط ۲۹ Packet، ۲۰۳ Case و ۲۹۰ slot است.

## نقش و انتساب

برای هر نوع نقش، dutyهای دامنه‌ای/فنی، Packetها، receipt slotها، توزیع lane و route و hash مجموعهٔ slotها ثبت شده است. انتساب واقعی فقط با roster ده‌فیلدی پذیرفته می‌شود: نوع نقش، owner/delegate reference، مرجع اختیار تصویب، دامنهٔ محیط و ماژول، بازهٔ اثر، نسخهٔ سیاست و attestation تعارض منافع.

هیچ نام شخص، شناسهٔ هویتی یا دادهٔ حساس در artifact وجود ندارد. وضعیت هر ۱۳ worklist برابر `UNASSIGNED_NAMED_OWNER` است؛ بنابراین named owner، delegate، roster پذیرفته‌شده، receipt دریافت‌شده/پذیرفته‌شده، تصمیم بسته و readiness همگی صفرند.

## مرز ادعا

این worklist فقط مسئولیت‌ها را به **نوع نقش** مسیردهی می‌کند. assignment دوگانه، Case و receipt را دو برابر نمی‌کند و هیچ semantic equivalence، result parity، UAT یا owner acceptance را ثابت نمی‌کند. هیچ عملیات وارانگار، دیتابیس یا اسمبلی اجرا نشده است.

Artifact:

`artifacts/varanegar_analysis/varanegar_alias_cross_lane_role_handoff_worklist_20260829.json`

Checkpoint:

`artifacts/varanegar_analysis/varanegar_alias_cross_lane_role_handoff_checkpoint_20260829.json`
