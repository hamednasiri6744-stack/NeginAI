# Reference Codec مصنوعی برای خطاهای Comparison Adapter

تاریخ: ۲۰۲۶-۰۸-۳۱

## هدف

بستهٔ قبلی شانزده بردار منفی را فقط از نظر عضویت در taxonomy کنترل می‌کرد. این بسته یک Validator مرجع و خالص می‌سازد تا همان شانزده خطا را با Envelopeهای کاملاً مصنوعی اجرا کند. این Codec هیچ I/O ندارد و Adapter عملیاتی ERP مقصد نیست.

## نتیجهٔ قابل‌بازتولید

- هشت Profile با یک Baseline مصنوعی سالم اجرا شدند و ۸/۸ پذیرفته شدند.
- برای هر Profile شانزده Mutation تک‌فیلدی اجرا شد؛ جمعاً ۱۲۸ اجرای منفی و ۱۲۸/۱۲۸ نتیجهٔ مطابق Error code و Typed status مورد انتظار ثبت شد.
- هر بردار دقیقاً یک Control field را تغییر می‌دهد.
- تقدم خطاها با فهرست شانزده‌تایی ثابت و fail-fast تعریف شده است؛ در صورت چند خطای هم‌زمان اولین خطای قرارداد برمی‌گردد.
- Trigger ناشناخته رد می‌شود و هیچ Payload خامی وارد Codec نمی‌شود.

## چیزی که PASS ثابت می‌کند

PASS نشان می‌دهد یک پیاده‌سازی مرجع کوچک و مستقل می‌تواند قواعد کنترل مصنوعی را با ترتیب و taxonomy قرارداد بازتولید کند. این نتیجه محدودیت lint-only بستهٔ قبلی را برای دادهٔ مصنوعی می‌بندد.

PASS موارد زیر را ثابت نمی‌کند:

- درستی پیاده‌سازی Adapter واقعی در ERP مقصد؛
- برابری خروجی Legacy و Target؛
- اجرای Failure Injection در وارانگار یا ERP؛
- صدور یا اصالت Receipt؛
- CG-05 closure، UAT، Command readiness یا Pilot readiness.

## مرز ایمنی

- Reference Codec فقط Boolean، Count، Status و token مصنوعی پردازش می‌کند.
- هیچ مقدار تجاری، شناسه، PII، Credential، SQL، فایل یا Payload خام دریافت یا ذخیره نمی‌شود.
- هیچ اتصال شبکه، دیتابیس، Share، فرم، گزارش، Query، Procedure یا Assembly وجود ندارد.
- Reference Codec implementation برابر یک است؛ Operational adapter implementation و run هر دو صفرند.
- Capture، Receipt، Acceptance، Result parity و Readiness صفر است.
- پایهٔ ۸۴ ریسک، ۳۴۳ انتساب و lower bound طراحی ۱۴۰۴ تغییر نکرد.

