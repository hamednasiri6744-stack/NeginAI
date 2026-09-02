# مقایسه‌گر شواهد معنایی Action Aliasهای P0 ـ ۲۰۲۶-۰۸-۲۹

شش Action کاندید P0 در سطح Caseهای هم‌نوع مقایسه شدند. ۶۶ جفت Case به‌دست آمد: Authorization و Concurrency هرکدام ۹، Failure Injection تعداد ۲۰، Idempotency تعداد ۱۲، Reconciliation تعداد ۲، Scope تعداد ۸ و Success تعداد ۶.

نتیجهٔ exact comparison محافظه‌کارانه است: precondition دقیق صفر، outcome دقیق فقط دو جفت، assertion-list دقیق صفر و تطبیق کامل صفر. دو outcome برابر فقط برچسب `COMMITTED` در کاندیدهای received-cheque هستند و چون assertion و precondition برابر نیستند، پذیرش معنایی ایجاد نمی‌کنند.

تمرکز ۲۰ جفت در Failure Injection نشان می‌دهد داوری باید stage خطا، durable effect، rollback/unknown outcome و retry receipt را صریح بسنجد. برابر بودن Kind یا یک outcome label به‌تنهایی برای reuse، replacement یا Alias کافی نیست.

هر شش Comparison در وضعیت `REVIEW_REQUIRED_NOT_SEMANTIC_EQUIVALENCE` باقی مانده‌اند. Candidate acceptance، Case-pair acceptance، اجرا، افزایش شمارش و readiness صفر و lower bound طراحی ۱۴۰۴ است.
