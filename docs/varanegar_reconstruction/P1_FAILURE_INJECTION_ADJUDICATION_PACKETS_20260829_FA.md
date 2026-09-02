# Packetهای داوری Failure Injection در P1 ـ ۲۰۲۶-۰۸-۲۹

نوزده جفت Failure Injection چهار نگاشت بانکی P1 به چهار Packet تبدیل شد. پنج Case جدید در برابر پانزده Case پایه قرار گرفت و هیچ fault-stage دقیق وجود ندارد؛ هر ۱۹ جفت generic/different-to-detailed هستند.

در baseline، پانزده جفت retry/convergence، شانزده جفت منع partial effect و نه جفت stage حساس به audit/outbox را صریح می‌کنند. Stageهای پایه شامل state transition، link write/load/unlink، bank-cardex، staging cleanup، candidate validation و audit/outbox است؛ برچسب‌های جدید این تفکیک را جذب نمی‌کنند.

Outcome exact، assertion exact و full exact همگی صفر است. هیچ Pair پذیرفته یا اجرا نشده، اثر افزایشی و readiness صفر است و lower bound طراحی ۱۴۰۴ و پایهٔ ۸۴/۳۴۳ ثابت می‌ماند.
