# ماتریس یکپارچهٔ تحویل و پذیرش شش Gate بیرونی وارانگار

این سند یک طراحی فقط‌خواندنی برای تحویل Evidence بین `CG-06` تا `CG-04` است. هدف آن اجرای Runtime یا UAT نیست؛ فقط مرز مسئولیت، واحد پذیرش، وابستگی و علت رد هر Packet را یکدست می‌کند.

## تصویر فعلی

- شش Gate همگی بازند.
- مجموع واحدهای پذیرش لازم ۸۴ است: ۸ Slot پلتفرم، ۲۰ Surface گزارش و چهار مجموعهٔ ۱۴ماژولی برای Authorization، Atomicity، Effect parity و UAT نهایی.
- واحد پذیرفته‌شده صفر است.
- نه Edge وابستگی وجود دارد و هر نه مورد تا پذیرش Gate مبدأ مسدودند.
- اجرای Obligation، Approval مالک، Command readiness و Pilot readiness همگی صفرند.

## ترتیب و مرز تحویل

| Gate | واحد پذیرش | تعداد | ورودی وابسته | مصرف‌کنندهٔ مستقیم |
|---|---|---:|---|---|
| CG-06 | Platform decision slot | ۸ | ندارد | CG-01، CG-02، CG-03، CG-04 |
| CG-05 | Report surface packet | ۲۰ | ندارد | CG-04 |
| CG-01 | Authorization module packet | ۱۴ | CG-06 | CG-04 |
| CG-02 | Atomicity module packet | ۱۴ | CG-06 | CG-03، CG-04 |
| CG-03 | Effect-parity module packet | ۱۴ | CG-06، CG-02 | CG-04 |
| CG-04 | Terminal owner-UAT module packet | ۱۴ | CG-01، CG-02، CG-03، CG-05، CG-06 | نهایی |

هر تحویل فقط به Packet set دقیق و immutable با وضعیت `ACCEPTED_CURRENT` متصل می‌شود. Proposal، پذیرش جزئی، شاهد بدون Hash، شاهد منقضی یا Superseded و Approval فاقد نقش پاسخ‌گو رد می‌شوند. ورود PII، Credential، Endpoint یا مقدار خام تجاری نیز ممنوع است.

## ماشین وضعیت

وضعیت‌ها `WAITING_DEPENDENCY`، `SUBMITTED`، `REJECTED`، `ACCEPTED_CURRENT` و `SUPERSEDED` هستند. Packet جدیدِ پذیرفته‌شده Packet قبلی را Supersede می‌کند و مصرف‌کننده باید به Hash جدید دوباره Bind شود. بسته‌شدن Gate فقط پس از پذیرش تمام واحدهای همان Gate و عبور از Closure rule اختصاصی آن ممکن است.

این ماتریس هیچ Readinessی ایجاد نمی‌کند. حتی بسته‌شدن یک Gate نیز به‌تنهایی Command-ready یا Pilot-ready نیست؛ Promotion تنها پس از زنجیرهٔ کامل و Snapshot دقیقِ CG-04 قابل بازنگری است.
