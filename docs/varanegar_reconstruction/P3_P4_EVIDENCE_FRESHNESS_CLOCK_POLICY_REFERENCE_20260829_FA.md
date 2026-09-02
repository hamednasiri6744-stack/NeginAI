# قرارداد مرجع Freshness، Clock و مرزهای زمانی شواهد P3/P4

تاریخ: ۲۰۲۶-۰۸-۳۱

## هدف

عبارت‌های Current و Unexpired بدون تعریف Clock و مرز زمانی مبهم‌اند. این بسته یک Evaluator خالص با timestampهای ثابت و مصنوعی می‌سازد. هیچ System clock، سرویس زمان یا Receipt واقعی خوانده نمی‌شود.

## قرارداد زمانی

- چهار نوع Temporal artifact: Capture Authorization، Redaction Attestation، Custody Receipt و Comparison Handoff؛
- هشت Outcome: Missing، Not Yet Valid، Current، Expired، Revoked، Superseded، Clock/Interval Invalid و Policy Version Mismatch؛
- Envelope شانزده‌فیلدی و ده Clock policy rule؛
- `valid_from` شامل مرز است؛
- `expires_at` خارج از بازه و بنابراین exclusive است؛
- Timestamp بدون timezone رد می‌شود؛
- Interval معکوس، Clock نامعتبر و Policy mismatch fail-closed هستند؛
- Revocation و Supersession بر بازهٔ زمانی مقدم‌اند؛
- expiry خودکار تمدید یا reaccept نمی‌شود.

## آزمون مصنوعی

دوازده Vector شامل وسط بازه، دقیقاً روی valid-from، قبل از آن، دقیقاً روی expiry، بعد از expiry، revoked، superseded، missing، clock نامطمئن، policy mismatch، interval معکوس و timestamp بدون timezone است. هر Vector برای چهار نوع Artifact اجرا شد؛ ۴۸/۴۸ PASS و fail صفر است.

برای ۵۴ Custody requirement و چهار نوع Artifact، تعداد ۲۱۶ Freshness obligation ساخته شد. وضعیت فعلی همه `MISSING_TEMPORAL_EVIDENCE` است.

## محدودیت

- Reference Evaluator فقط یک پیاده‌سازی مصنوعی و بدون I/O است.
- Real clock evaluation، Current evidence و Accepted freshness صفر است.
- حتی Outcome برابر `CURRENT` به‌تنهایی Acceptance، Handoff، Result parity، CG-05، UAT یا Readiness را ثابت نمی‌کند.
- هیچ اتصال، اجرا، Mutation یا دادهٔ حساس استفاده نشده و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

