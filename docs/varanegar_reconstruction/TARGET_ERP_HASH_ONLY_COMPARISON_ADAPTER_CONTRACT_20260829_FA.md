# قرارداد Comparison Adapter مبتنی بر Hash برای ERP مقصد

این قرارداد مرز فنی مقایسهٔ خروجی Legacy و Target را برای هشت Packet گزارش/Export در P3/P4 تعریف می‌کند. قرارداد، پیاده‌سازی یا اجرای Adapter نیست و هیچ دادهٔ خامی را وارد Artifact نمی‌کند.

## پوشش

- هشت Adapter Profile: پنج P3 و سه P4.
- ۵۶ Golden/UAT Case.
- ۱۸ Field در Input envelope و ۱۸ Field در Output receipt.
- دوازده مرحلهٔ canonicalization.
- ۱۶ Error code و شش Typed status.
- ۱۶۰ انتساب بُعد parity، تعداد ۲۷ Receipt زیر CG-05 و ۹۶ Promotion Guard assignment.

## اصل Canonicalization

Adapter ابتدا schema، hash، version، Packet، Case-set، Dimension-set و دو سمت Capture را کنترل می‌کند. سپس type tagها، Unicode، زمان/Locale/Calendar، Decimal/Rounding/Currency/Unit، و تفاوت Null/Missing/Empty/Zero/Unknown را بر اساس Profile نسخه‌دار canonical می‌کند.

Stable-key و Row/Item digest با domain separation ساخته می‌شود. Set hash مستقل از ترتیب و Order hash جداگانه است. Grain، Aggregate، Render/File و Per-item outcome نیز digest مستقل دارند. مقایسه باید Dimension-by-Dimension باشد؛ برابری Total، Row count، پایان Render یا وجود فایل نتیجهٔ parity نیست.

الگوریتم digest برابر SHA-256 است. Float serialization مجاز نیست و Decimal فقط با Scale/Rounding policy نسخه‌دار canonical می‌شود. هیچ مقدار خامی Persist نمی‌شود.

## Idempotency

کلید Idempotency از پنج hash ساخته می‌شود:

1. نسخهٔ Adapter profile.
2. Fixture manifest.
3. Legacy output manifest.
4. Target output manifest.
5. مجموعهٔ ابعاد درخواستی.

تکرار همان Key و همان ورودی باید Receipt hash قبلی را برگرداند. همان Key با ورودی متفاوت `IDEMPOTENCY_CONFLICT` است. پس از Outcome نامعلوم، ابتدا Receipt با Key خوانده می‌شود و Retry کور مجاز نیست. Receipt قبلی overwrite نمی‌شود و تغییر فقط با Receipt جدیدِ superseding ممکن است.

## خروجی و Error taxonomy

Output فقط Reference، Hash، Count دسته‌ای، Typed status، Error-code-set hash و Adjudication reference دارد. Statusها Match candidate، Difference، Invalid evidence، Unsupported profile/schema، Conflict/Supersession و Partial/Unknown هستند.

Error taxonomy مرزهای Manifest، Hash، Schema/Profile، Fixture/Case-set، Capture side، Dimension-set، Scope، Locale/Time، Decimal/Currency، Stable key، Grain، Serialization، Partial outcome، Idempotency و تلاش برای Persist payload خام را پوشش می‌دهد.

## منع نگهداری دادهٔ خام

نگهداری Row/Item، مقدار تجاری/Aggregate، Stable key یا شناسهٔ واقعی، هویت مشتری، Document/File، پارامتر گزارش، Credential/Connection string/Token، متن Rule/Formula/SQL، Endpoint و Note بدون Redaction ممنوع است.

## وضعیت فعلی و مرز ایمنی

- پیاده‌سازی Adapter: صفر.
- Request، Canonicalization run و Comparison run: صفر.
- Receipt تولیدشده یا پذیرفته‌شده: صفر.
- Result parity، UAT، Command readiness و Pilot readiness: صفر.

این قرارداد هیچ اتصال Database یا Network، اجرای فرم/گزارش/Stored Procedure، Load/Execute اسمبلی، تغییر داده یا ایجاد Write access انجام نداده است. `PASS` فقط انسجام طراحی را ثابت می‌کند. پایهٔ ۸۴ ریسک، ۳۴۳ Trace assignment و lower bound برابر ۱۴۰۴ تغییر نکرده است.
