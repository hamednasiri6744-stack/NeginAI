# داوری Outcome Vocabulary کنترل‌های P4 ـ ۲۰۲۶-۰۸-۲۹

هشت جفت غیرخطای Export/Read در سه Packet تفکیک شد: Authorization سه، Idempotency دو و Success سه جفت. سمت جدید سه outcome label دارد و baseline فقط assertion-array بدون outcome label صریح است.

سه جفت `REJECTED_NO_EFFECT` و دو جفت `COMMITTED_ORIGINAL_OUTCOME_ONLY_ONCE` است. Outcome exact صفر و هر هشت جفت به mapping مستقل Read/Export/File/Result نیاز دارد.

Result parity، acceptance و اجرا صفر است؛ lower bound طراحی ۱۴۰۴، Risk/Trace برابر ۸۴/۳۴۳ و readiness صفر باقی می‌ماند.
