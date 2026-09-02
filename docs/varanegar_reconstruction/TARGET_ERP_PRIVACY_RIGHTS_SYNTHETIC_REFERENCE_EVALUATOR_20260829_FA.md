# Reference Evaluator مصنوعی Privacy Rights

این evaluator یک طراحی مهندسی jurisdiction-neutral و غیرمشاورهٔ حقوقی است. فقط Boolean/Action مصنوعی را پردازش می‌کند و هیچ PII یا دادهٔ عملیاتی نمی‌خواند.

ترتیب تصمیم Schema، Inventory/Subject linkage، Purpose/Basis/Jurisdiction، Notice، Consent/Withdrawal، Minimization/Sensitive guard، Rights identity، Record discovery، Third-party redaction، Legal hold/Conflict، Sharing، Automated decision، Breach، Retention/Disposition، Unknown و Acceptance است.

نه مسیر مثبت/حفاظتی و بیست‌ویک mutation منفی تعریف شده‌اند. Withdrawal، identity mismatch، incomplete discovery، legal hold، unscoped sharing، automated decision بدون human review و disposition بدون retention proof همگی fail-closed هستند.

Operational implementation/read/run/receipt و Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
