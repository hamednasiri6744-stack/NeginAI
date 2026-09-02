# Golden/UAT خروجی‌های گزارش — ۱۴۰۵/۰۶/۰۷

برای هشت سطح خروجی، ۵۶ Case مصنوعی طراحی شد: Deny، نسخه/Watermark/Template کهنه، CommandId تکراری، شکست Render، شکست Completion، Batch جزئی و موفقیت. هر Case نتیجهٔ Render، Completion، Audit، فایل و فرمان واگذارشده را جدا مقایسه می‌کند.

Caseهای ویژه تضمین می‌کنند Preview Completion نسازد، Retry چاپ تکراری کور نباشد، Export ERP fact را تغییر ندهد، signed metric بانکی حفظ شود و Import بانکی Receipt مالی موفق را دوباره اجرا نکند.

همهٔ Caseها `DESIGNED_NOT_EXECUTED` هستند؛ اجرا، owner approval، runtime retry proof و readiness صفر باقی مانده‌اند.
