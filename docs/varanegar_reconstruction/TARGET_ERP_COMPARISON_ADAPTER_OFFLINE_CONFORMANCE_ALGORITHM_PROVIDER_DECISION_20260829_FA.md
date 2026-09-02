# Harness آفلاین Comparison Adapter و Decision Record الگوریتم/Key Provider

تاریخ: ۲۰۲۶-۰۸-۳۱

## نتیجه

یک Harness مرجع کاملاً محلی برای بردارهای مصنوعی Comparison Adapter ساخته شد. این Harness برای هشت Profile و دوازده بردار مثبت، ۹۶ محاسبهٔ digest انجام می‌دهد و هر ۹۶ مورد باید با SHA-256 مورد انتظار برابر باشند. شانزده بردار منفی نیز برای هر Profile، یعنی ۱۲۸ مورد، فقط از نظر عضویت در taxonomy خطای قرارداد lint می‌شوند؛ هیچ خطای Runtime تزریق نمی‌شود.

این PASS فقط بازتولیدپذیری بردارهای مصنوعی و سازگاری taxonomy را ثابت می‌کند. پیاده‌سازی Adapter مقصد، برابری خروجی Legacy/Target، اصالت امضای رمزنگاری، CG-05، UAT و readiness را ثابت نمی‌کند.

## Decision Record باز

چهار خانوادهٔ الگوریتم به‌عنوان Candidate و نه انتخاب ثبت شدند:

- RSA-PSS با SHA-256؛
- ECDSA P-256 با SHA-256؛
- Ed25519؛
- ML-DSA صرفاً به‌عنوان Candidate مهاجرت و Crypto Agility.

چهار الگوی Provider نیز بدون انتخاب ثبت شدند: KMS با کلید غیرقابل‌استخراج، HSM، Keystore بومی پلتفرم و سرویس امضای جداگانه. این نام‌ها الگوی معماری‌اند و محصول یا Vendor مشخصی را توصیه نمی‌کنند.

هر هشت Candidate با چهارده معیار بررسی می‌شود؛ در مجموع ۱۱۲ انتساب معیار داریم. ده Gate شامل تأیید Platform/Security، انطباق، Threat Model، Trust Boundary، شواهد non-exportability، benchmark مصنوعی، برنامهٔ rotation/revocation/DR، Crypto Agility و UAT ایزوله باز هستند. تا بسته‌شدن همهٔ Gateها انتخاب خودکار ممنوع است.

## مبنای استاندارد

- [NIST FIPS 186-5](https://csrc.nist.gov/pubs/fips/186-5/final) برای خانواده‌های امضای دیجیتال کلاسیک؛
- [NIST SP 800-57 Part 1 Rev. 5](https://csrc.nist.gov/pubs/sp/800/57/pt1/r5/final) برای مدیریت چرخهٔ کلید؛
- [RFC 8017](https://www.rfc-editor.org/info/rfc8017/) برای RSASSA-PSS؛
- [RFC 8032](https://www.rfc-editor.org/info/rfc8032/) برای EdDSA/Ed25519؛
- [NIST CSWP 39upd1](https://csrc.nist.gov/pubs/cswp/39/upd1/considerations-for-achieving-crypto-agility/final) برای Crypto Agility؛
- [NIST FIPS 204](https://csrc.nist.gov/pubs/fips/204/final) برای ML-DSA.

وجود Candidate به معنی مناسب‌بودن آن برای محیط نهایی نیست. نسخهٔ Runtime، کتابخانه، Provider، الزامات حقوقی/انطباقی، latency، availability، نگهداری بلندمدت Receipt و برنامهٔ مهاجرت باید با شاهد محیط واقعی و تأیید مستقل بسته شوند.

## مرز ایمنی

- هیچ کلید خصوصی یا عمومی ساخته، خوانده یا ذخیره نشد.
- هیچ signature bytes تولید یا verify نشد.
- هیچ اتصال به وارانگار، ERP، دیتابیس، Share یا سرویس Key Provider برقرار نشد.
- هیچ فرم، گزارش، Query، Procedure یا Assembly اجرا نشد.
- همهٔ مقادیر بردارها token مصنوعی‌اند و هیچ مقدار تجاری، هویتی، Credential یا PII ندارند.
- Operational adapter run، Signing، Verification، Receipt acceptance، Result parity، Command readiness و Pilot readiness همگی صفرند.
- پایهٔ ریسک ۸۴، انتساب ریسک/نیاز ۳۴۳ و lower bound طراحی ۱۴۰۴ تغییر نکرد.

