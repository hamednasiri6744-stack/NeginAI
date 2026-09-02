# داوری Outcome Vocabulary کنترل‌های P1 ـ ۲۰۲۶-۰۸-۲۹

۳۶ جفت غیرخطای بانکی در پنج Packet کنترل تفکیک شد: Authorization پنج، Concurrency هفت، Idempotency یازده، Scope نه و Success چهار جفت.

واژگان جدید فقط سه label جهانی دارد، درحالی‌که baseline شانزده عبارت متمایز دارد. `REJECTED_NO_EFFECT` در ۲۱ جفت و `COMMITTED_ORIGINAL_OUTCOME_ONLY_ONCE` در ۱۱ جفت متمرکز است. outcome exact صفر است و هر ۳۶ جفت به mapping و disposition کامل نیاز دارد؛ assertion/full exact نیز صفر است.

هیچ Pair پذیرفته یا اجرا نشده، lower bound طراحی ۱۴۰۴ و پایهٔ Risk/Trace برابر ۸۴/۳۴۳ ثابت است و readiness صفر می‌ماند.
