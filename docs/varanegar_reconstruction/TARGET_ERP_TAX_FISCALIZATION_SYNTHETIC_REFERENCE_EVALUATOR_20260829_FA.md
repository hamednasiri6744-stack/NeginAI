# Reference Evaluator مصنوعی Tax Fiscalization

این evaluator طراحی مهندسی jurisdiction-neutral و غیرمشاورهٔ حقوقی/مالیاتی/حسابداری است. فقط Boolean/Provider-state مصنوعی را پردازش می‌کند و هیچ ارسال یا دادهٔ عملیاتی ندارد.

ترتیب تصمیم Schema، Regime/Registration، Schema/Identifier/Classification، Tax/Rounding، Fiscal identity، Digest/Signature/Certificate، Idempotency/Payload identity، Human/Machine/Archive parity، Unknown، Provider outcome، Contingency، Correction/Cancellation و Reconciliation است.

هشت مسیر مثبت/حفاظتی و بیست‌ویک mutation منفی تعریف شده‌اند. Unknown نتیجهٔ reconciliation، Contingency نیازمند scope/expiry، Correction نیازمند lineage/period/provider state و ACK نیازمند control-total reconciliation است.

Operational implementation/read/run/receipt و Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
