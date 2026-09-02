# ماتریس شکاف خانواده‌های Assertion/Effect در P1 ـ ۲۰۲۶-۰۸-۲۹

۵۵ جفت Case بانکی در دوازده خانوادهٔ اثر مقایسه شد. همهٔ جفت‌ها حداقل یک خانوادهٔ مشترک دارند، اما family-set دقیق در هیچ جفتی وجود ندارد. ۲۵۵ assignment فقط در سمت جدید و ۸۰ assignment فقط در baseline ثبت شد.

Audit در هر دو سمت ۵۵/۵۵ است، اما Outbox جدید/پایه ۵۵/۱۵ است. Source immutability جدید/پایه ۰/۵۵، Transaction atomicity برابر ۰/۲۵ و Version concurrency برابر ۵۵/۰ است. بنابراین شباهت کلی assertionها تفاوت بنیادی قرارداد اثر و همگرایی را پنهان می‌کند.

Classifier فقط routing heuristic بر متن مستند است و اجرای Runtime یا برابری معنایی را ثابت نمی‌کند. پذیرش Family/Case، اجرا، additive و readiness صفر و lower bound طراحی ۱۴۰۴ باقی مانده است.
