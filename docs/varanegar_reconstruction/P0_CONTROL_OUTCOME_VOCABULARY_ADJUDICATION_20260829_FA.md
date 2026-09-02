# داوری Outcome Vocabulary برای کنترل‌های P0 ـ ۲۰۲۶-۰۸-۲۹

۴۶ جفت غیرخطای P0 در شش Packet کنترلی تفکیک شد: Authorization=۹، Concurrency=۹، Idempotency=۱۲، Reconciliation=۲، Scope=۸ و Success=۶. مجموعهٔ جدید هشت Outcome label جهانی دارد، درحالی‌که baseline از ۲۳ عبارت متمایز استفاده می‌کند.

برچسب عمومی `REJECTED_NO_EFFECT` در ۲۳ جفت Authorization/Concurrency/Scope و `COMMITTED_ORIGINAL_OUTCOME_ONLY_ONCE` در ۱۱ جفت Idempotency دیده می‌شود. این فشرده‌سازی vocabulary ممکن است تفاوت denial، stale-version، scope disclosure، replay و payload-conflict را پنهان کند و به mapping صریح نیاز دارد.

فقط دو جفت Success برچسب outcome برابر `COMMITTED` دارند؛ assertion-list و full match در همهٔ ۴۶ جفت صفر است. بنابراین حتی این دو برچسب برابر، effect equivalence یا reuse را اثبات نمی‌کنند. ۴۴ جفت به mapping صریح label نیاز دارند و هر ۴۶ جفت باید precondition/assertion/effect disposition داشته باشند.

پذیرش Outcome pair، اجرا، اثر شمارشی و readiness صفر و lower bound طراحی ۱۴۰۴ باقی مانده است.
