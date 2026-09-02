# Outcome/Retry خروجی‌های گزارش و چاپ — ۱۴۰۵/۰۶/۰۷

هشت سطح Command-bearing به یک envelope پنج‌حالته متصل شدند: رد بدون اثر، Render بدون Completion، Completion ثبت‌شده، Batch جزئی و نتیجهٔ مبهم نیازمند Read-back. درخواست ۱۰ فیلد و پاسخ ۹ فیلد دارد و `CommandId + Payload/Template/Filter/Watermark` مرز Retry است.

`PRINT_REQUESTED`، موفقیت Render، تأیید چاپ فیزیکی و ثبت Audit چهار وضعیت جدا هستند. Preview هیچ Completion نمی‌سازد؛ Export فقط رخداد فایل خارجی است و ERP fact را تغییر نمی‌دهد؛ Batch نتیجهٔ هر آیتم را نگه می‌دارد. Import بانکی نیز نتیجهٔ مالی را به Receiptهای فرمان خزانه واگذار می‌کند.

در شواهد موجود ۳۰۸٬۴۳۲ رخداد چاپ فاکتور فروش، ۳۴٬۸۴۰ سند با چاپ تکراری و ۱۴۳ رخداد پس از ابطال نهایی دیده می‌شود. این اعداد بدون Request identity دلیل Bug نیستند؛ برای Retry باید Audit و وضعیت سند خوانده شود. هیچ گزارش، چاپ، Export، Import یا فرمان خزانه اجرا نشده و Runtime parity/readiness صفر است.
