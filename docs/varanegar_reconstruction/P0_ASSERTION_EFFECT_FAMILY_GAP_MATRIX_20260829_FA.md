# ماتریس شکاف خانوادهٔ Assertion/Effect برای P0 ـ ۲۰۲۶-۰۸-۲۹

Assertion و side-effect طراحی‌شدهٔ هر ۶۶ جفت P0 به دوازده خانوادهٔ محافظه‌کارانه تبدیل شد. هیچ جفتی family-set یکسان ندارد؛ ۶۵ جفت حداقل یک خانوادهٔ مشترک و یک جفت هیچ هم‌پوشانی ندارد. هم‌پوشانی فقط ابزار routing است و برابری معنایی را ثابت نمی‌کند.

سمت جدید در هر ۶۶ جفت Audit و Outbox را ذکر می‌کند، درحالی‌که baseline به‌ترتیب ۵۰ و ۱۴ جفت را پوشش می‌دهد. در مقابل، Source immutability در ۵۳ جفت baseline و صفر جفت جدید دیده می‌شود؛ Transaction/atomicity نیز ۲۹ baseline در برابر شش جدید است. Version/concurrency در ۵۵ جفت جدید و صفر baseline assertion ثبت شده و mutation/history scope هرکدام در ۱۳ جفت baseline و صفر جدید field-presence دارند.

در مجموع ۲۹۴ family assignment فقط در سمت جدید و ۱۲۵ assignment فقط در baseline وجود دارد. این عدم تقارن نشان می‌دهد اختلاف assertion صرفاً بازنویسی متن نیست و باید transaction، write-set، source immutability، audit/outbox، scope/version/retry و reconciliation جداگانه disposition شوند.

این classifier بر keywordهای متن مستند تکیه دارد و اثبات semantics نیست. پذیرش Family mapping/Case pair، اجرا، اثر شمارشی و readiness صفر و lower bound طراحی ۱۴۰۴ باقی مانده است.
