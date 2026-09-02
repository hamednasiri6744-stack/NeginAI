# قرارداد Monetary، Quantity و Temporal Semantics مقصد

چهارده بُعد Decimal/Currency/Rounding/Tax/Discount/Rate/Unit/Time/Fiscal/Calendar در چهارده ماژول ۱۹۶ assignment دارد. دوازده invariant و دوازده مرحلهٔ lifecycle هرکدام ۱۶۸ assignment ایجاد می‌کنند.

Numeric policy بیست‌ودو، Calculation receipt بیست‌وچهار، Conversion receipt بیست و Temporal/Fiscal receipt بیست فیلد دارد. شانزده Failure case تعداد ۲۲۴، بیست‌ودو Gate تعداد ۳۰۸ و هفت Role تعداد ۹۸ assignment دارد.

Binary float، scale یا rounding ضمنی، residual گمشده، rate بی‌جهت/بی‌نسخه، conversion میان dimensionهای ناسازگار، timestamp بدون timezone، DST normalization خاموش و posting در دورهٔ بسته ممنوع است. تاریخ جلالی/میلادی نمایش نسخه‌دار است، نه authoritative instant.

هیچ مبلغ، مقدار، نرخ، تاریخ یا timestamp عملیاتی خوانده و هیچ Calculation/Conversion/Posting اجرا نشد. Policy approval/Runtime receipt/Reconciliation/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
