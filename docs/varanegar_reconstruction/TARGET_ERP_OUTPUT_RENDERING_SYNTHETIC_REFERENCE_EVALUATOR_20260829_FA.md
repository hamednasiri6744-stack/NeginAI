# Reference Evaluator مصنوعی Output Rendering

این evaluator فقط Boolean/State مصنوعی را پردازش می‌کند و هیچ template، snapshot، سند، PDF، barcode، printer یا receipt عملیاتی را باز یا اجرا نمی‌کند.

ترتیب تصمیم Schema، Template/Data، Renderer، Font/RTL، Locale/Numeric، Layout/Pagination، Barcode/Machine scan، QR، Authorization/Redaction، Copy/Watermark/Lineage، PDF/Digest/Signature، Accessibility، Blocking unknown، Print delivery و Acceptance است.

شش مسیر مثبت File/Print/Unknown/Preview/Reprint/No-barcode و بیست‌ویک mutation منفی تعریف شده‌اند. Font/RTL، locale/rounding، layout/page، barcode decode، QR policy، redaction، reprint lineage، PDF signature و accessibility همگی fail-closed هستند.

این یک reference implementation است، نه renderer یا scanner. Operational implementation/read/run/receipt و Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
