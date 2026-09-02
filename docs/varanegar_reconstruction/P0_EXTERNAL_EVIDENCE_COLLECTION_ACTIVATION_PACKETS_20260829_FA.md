# Packetهای فعال‌سازی جمع‌آوری شواهد بیرونی P0 — ۲۰۲۶-۰۸-۲۹

این بسته هفت مسیر پرریسک P0 و ۴۹ Case را برای **جمع‌آوری مدرک بیرونی** آماده می‌کند؛ واژهٔ activation در اینجا هرگز مجوز اجرای فرم، گزارش، Stored Procedure یا فرمان عملیاتی نیست.

## Scope و شکاف

- چهار Packet بدون کاندید baseline به تصمیم Alias/New Action و سه Packet کاندیددار به Semantic Equivalence نیاز دارند.
- سه Packet کاندیددار ۶۶ جفت هم‌نوع می‌سازند: ۲۰ Failure و ۴۶ Control. فقط دو outcome label برابر است؛ full/effect-family exact صفر است.
- هفت Packet به ۷۰ receipt slot، ۱۴ role assignment از هفت نوع نقش، ۳۵ gate assignment و ۴۹ prerequisite assignment متصل شده‌اند.

## شرط فعال‌سازی جمع‌آوری مدرک

برای هر Packet ابتدا دو owner roster دامنه‌دار باید پذیرفته شود؛ سپس case-set/candidate، policy version و expiry pin شوند. هر ده receipt slot باید به `ROLE_ACCEPTED` برسد، scope پنج gate معتبر باشد، conflict/supersession حل شود و route decision مستقل پذیرفته شود.

وضعیت فعلی هر هفت Packet `NOT_ACTIVATED_EXTERNAL_EVIDENCE_MISSING` است: برای هر Packet دو owner، ده receipt و پنج gate باز است. اجرا، owner approval، semantic closure و readiness همگی صفرند و lower bound طراحی ۱۴۰۴ تغییری نکرده است.

Artifact:

`artifacts/varanegar_analysis/varanegar_p0_external_evidence_collection_activation_packets_20260829.json`

Checkpoint:

`artifacts/varanegar_analysis/varanegar_p0_external_evidence_collection_activation_checkpoint_20260829.json`
