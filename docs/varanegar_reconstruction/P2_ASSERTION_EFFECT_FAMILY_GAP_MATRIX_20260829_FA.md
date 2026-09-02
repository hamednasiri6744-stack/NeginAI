# ماتریس شکاف خانواده‌های Assertion/Effect در P2 ـ ۲۰۲۶-۰۸-۲۹

۷۳ جفت Case قیمت‌گذاری/چک در دوازده خانوادهٔ اثر مقایسه شد. ۶۴ جفت حداقل یک خانوادهٔ مشترک دارند، ۹ جفت هیچ هم‌پوشانی ندارند و family-set دقیق در هیچ جفتی وجود ندارد. ۴۲۰ assignment فقط در سمت جدید و ۹۷ assignment فقط در baseline ثبت شد.

Audit جدید/پایه ۷۳/۳۶ و Outbox برابر ۷۳/۱۴ است. Source immutability برابر ۵۶/۲۸، Transaction atomicity برابر ۰/۴۶ و Version concurrency برابر ۷۳/۱۴ است. این عدم‌تقارن‌ها نشان می‌دهد دو outcome label برابر نیز قرارداد اثر معادل نمی‌سازند.

Classifier فقط routing heuristic بر متن مستند است و اجرای Runtime یا برابری معنایی را ثابت نمی‌کند. پذیرش Family/Case، اجرا، additive و readiness صفر و lower bound طراحی ۱۴۰۴ باقی مانده است.
