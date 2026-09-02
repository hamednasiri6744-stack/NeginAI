# قرارداد Frozen-fixture و Output-manifest برای P3/P4 — ۲۰۲۶-۰۸-۲۹

این قرارداد هشت فرمان گزارش/Export و ۵۶ Golden/UAT Case موجود را به manifestهای hash-only متصل می‌کند. هر فرمان دقیقاً هفت Case دارد: یک Authorization، دو Failure Injection، یک Idempotency، یک Partial Failure، یک Success و یک Versioning.

## سه Manifest

برای هر Packet سه schema شانزده‌فیلدی تعریف شده است:

1. **Fixture manifest:** شناسه و hash مجموعهٔ Case، snapshot و query/template/projection version، schema پارامتر، policy/config version، watermark، scope، locale/calendar/currency/unit و redaction attestation.
2. **Output manifest:** برای هر دو سمت Legacy و Target؛ stable-key set، canonical row/item set، grain، ordering، aggregate/formula version، render/file digest، ساختار صفحه/فایل و per-item outcome.
3. **Comparison manifest:** hash اختلاف key/value/formula/order/render/file/per-item، disposition بیست بُعد، exception/conflict reference و receipt نقش‌ها.

برای هشت Packet در مجموع ۵۱۲ field assignment، ۱۶ capture side، ۵۶ acquisition-step assignment، ۱۶۰ parity-dimension assignment و ۲۷ receipt CG-05 تعریف شد. این‌ها refinement همان ۵۶ Case هستند و lower bound طراحی را افزایش نمی‌دهند.

## مرز ایمنی

قرارداد مجوز Capture یا اجرا نیست. هر Capture به مجوز جداگانه در محیط ایزوله نیاز دارد و فقط reference، hash، category اختلاف و redaction attestation می‌تواند ماندگار شود. هیچ fixture value، report output، فایل، PII، هویت یا credential در artifact ذخیره نشده است.

وضعیت هر هشت قرارداد `DESIGNED_NOT_CAPTURED_SEPARATE_AUTHORIZATION_REQUIRED` است؛ Capture، Comparison، Result parity، owner approval و readiness همگی صفرند.

Artifact:

`artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_contract_20260829.json`

Checkpoint:

`artifacts/varanegar_analysis/varanegar_p3_p4_frozen_fixture_output_manifest_checkpoint_20260829.json`
