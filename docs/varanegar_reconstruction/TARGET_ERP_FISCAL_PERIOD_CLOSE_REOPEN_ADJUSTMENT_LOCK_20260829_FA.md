# قرارداد قفل، بستن، بازگشایی و تعدیلات دورهٔ مالی ERP مقصد

## هدف و مرز

این بسته فقط طراحی شواهد است. هیچ دوره، دفتر، سند، مانده یا ثبت عملیاتی خوانده نشد؛ هیچ Close، Reopen، Adjustment، Reversal یا Posting اجرا نشد و هیچ provider انتخاب نشده است.

## قواعد قطعی

- قفل دوره باید در تمام مسیرهای command، import، batch، integration و storage یکسان باشد؛ تغییر تاریخ سند به‌تنهایی مجوز posting نیست.
- Hard close پیش از بستن ترتیبی subledgerها، هزینهٔ موجودی، مالیات، بانک، حقوق، دارایی، accrual، FX، trial balance و control total پذیرفته نیست.
- Late entry فقط با کلاس Adjustment صریح، مرجع سند اصلی، محدودیت مبلغ/تعداد، authorization مستقل و قاعدهٔ reversal پذیرفته می‌شود.
- Reopen به reason، impact، scope، expiry، تفکیک requester/approver/operator/reviewer و token کمینه، یک‌بارمصرف و غیرقابل‌انتقال نیاز دارد.
- Reclose تمام وابستگی‌های متاثر را دوباره اجرا و receipt قبلی و جدید را با lineage تغییرناپذیر supersession متصل می‌کند؛ receipt قبلی حذف یا بازنویسی نمی‌شود.

## پوشش ساختاری

چهارده بُعد برای چهارده ماژول ۱۹۶ assignment و دوازده مرحله ۱۶۸ assignment دارد. Policy شامل ۲۴ فیلد و Close/Reopen/Adjustment receipt هرکدام ۲۲ فیلد هستند. هجده failure case تعداد ۲۵۲، بیست‌وچهار gate تعداد ۳۳۶ و هفت نقش تعداد ۹۸ assignment ایجاد می‌کند؛ چهارده outcome typed تعریف شده است.

## وضعیت صادقانه

تمام obligationها باز هستند. Runtime، receipt عملیاتی، approval، Command readiness و Pilot readiness صفر است. پایهٔ ریسک ۸۴، نگاشت ۳۴۳ و lower bound برابر ۱۴۰۴ بدون ادعای افزایشی حفظ شده است.
