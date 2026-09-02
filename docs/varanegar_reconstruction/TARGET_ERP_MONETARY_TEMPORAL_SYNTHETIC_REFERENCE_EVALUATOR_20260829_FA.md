# Reference Evaluator مصنوعی Monetary/Temporal مقصد

یک Evaluator خالص و بدون I/O برای Decimal quantization، Largest-remainder allocation، Conversion، Reversal و Temporal/Fiscal validation ساخته شد. ۲۰ بردار مثبت و ۱۴ بردار منفی، جمعاً ۳۴/۳۴، PASS است.

شش Rounding، چهار Allocation، چهار Conversion، سه Reversal و سه Temporal vector مثبت پوشش دارد. HALF_EVEN/HALF_UP صریح است؛ Allocation جمع کل را با residual قطعی و tie-break پایدار حفظ می‌کند.

Decimal غیررشته‌ای/نامعتبر/نامتناهی، Scale/Mode نامعتبر، Weight نامعتبر، Denominator صفر، Timestamp بدون Offset، Timezone یا Offset ناسازگار، Fiscal period بسته و Calendar authoritative fail-closed هستند.

همهٔ Amount/Weight/Rate/Date/Timestampها ثابت و مصنوعی‌اند. هیچ مقدار عملیاتی خوانده و هیچ Calculation/Conversion/Posting/Command اجرا نشد؛ Reference implementation یک و Operational implementation/Receipt/Readiness صفر است.
