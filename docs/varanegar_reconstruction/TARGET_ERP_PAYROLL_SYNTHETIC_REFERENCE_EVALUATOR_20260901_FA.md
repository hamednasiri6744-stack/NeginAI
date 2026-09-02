# ارزیاب مرجع مصنوعی حقوق و دستمزد

این ارزیاب pure و قطعی، INPUT، CALCULATE، RETRO، PAYSLIP، PAYMENT، TERMINATE و RECONCILE را فقط با booleanهای مصنوعی می‌سنجد. هیچ داده پرسنلی، حضور، حقوق، حساب بانکی یا دفتر خوانده یا تغییر داده نشده است.

precedence با schema/scope، version/idempotency، unknown commit و blocking unknown آغاز می‌شود. قرارداد یا زمان تأییدنشده، فرمول/statutory/rounding/period نامعتبر، retro بدون lineage، فیش بدون privacy، پرداخت بدون token/approval، خاتمه ناقص و payroll/GL mismatch همگی fail-closed هستند.

هفت مسیر مثبت و ۱۹ مسیر منفی، جمعاً ۲۶ بردار، باید outcome دقیق بسازند. این مرجع provider یا ادعای readiness نیست؛ command-ready و pilot-ready صفر است.
