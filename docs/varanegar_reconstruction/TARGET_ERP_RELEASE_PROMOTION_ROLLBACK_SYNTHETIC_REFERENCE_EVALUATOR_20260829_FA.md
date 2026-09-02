# Reference Evaluator مصنوعی Promotion/Rollback مقصد

یک Evaluator خالص و بدون I/O روی Envelope دقیق، سه مسیر مثبت UAT/Production/Rollback و بیست‌وسه Mutation منفی را اجرا می‌کند. هر ۳ مثبت، هر ۲۳ منفی و جمع ۲۶/۲۶ PASS است.

تقدم خطا از Schema و Digest تا Supply chain، Test، Token، Window، Migration/Recovery، Canary/Kill-switch، Redaction، Unknown/Residual، Health/SLO/Business invariant، UAT، Production approval، Role separation و Rollback safety قطعی است.

UAT به Production approval نیاز ندارد اما مجوز Production محسوب نمی‌شود. Production به UAT acceptance، approval مستقل و جدایی Role نیاز دارد؛ Rollback ناامن به `FORWARD_FIX_REQUIRED_ROLLBACK_UNSAFE` می‌رود.

فقط hash ثابت، boolean و count مصنوعی پردازش شد. هیچ Manifest/Artifact/Registry/Environment/Receipt عملیاتی خوانده و هیچ Build/Deploy/Promotion/Rollback/Health-check اجرا نشد؛ Operational implementation و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
