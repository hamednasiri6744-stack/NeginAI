# قرارداد Outcome/Retry انتشار و بازیابی Platform

این بسته شش فرمان provider-neutral برای `approve`، `reject`، `retry_job`، انتشار و rollback نسخه و ثبت گواهی Restore Drill تعریف می‌کند. سه فرمان نخست از Blueprint موجود می‌آیند؛ سه فرمان بعدی کنترل لازم برای Release/Recovery را بدون انتخاب Stack مشخص می‌کنند.

مرز اصلی این است که Commit پایگاه کنترل، وقوع Deployment/Restore/Job خارجی را ثابت نمی‌کند. هر اثر خارجی به Receipt مرحله‌ای، read-back سلامت و reconciliation نیاز دارد و وضعیت مبهم فقط `UNKNOWN_EXTERNAL_EFFECT_REQUIRES_READBACK` است. Rollback یک فرمان تازه به manifest شناخته‌شده است و تاریخ را بازنویسی نمی‌کند.

اسکن ایستا ۸۵۳ فایل استقرار را با صفر reference بیرونی pin می‌کند، اما نبود reference نام‌دار، route پویا را رد نمی‌کند. Stack، Database، Hosting، RPO/RTO، ظرفیت و مالک استقرار همچنان تصمیم‌گیری‌نشده‌اند؛ هیچ گزینهٔ پیشنهادی در این سند Approval محسوب نمی‌شود.

هیچ Deployment، Job retry، Restore، Failover یا Rollback اجرا نشده و credential، endpoint secret، PII یا مقدار خام تجاری خوانده/ذخیره نشده است.
