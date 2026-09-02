# مسیر متدی گزارش‌ها تا لایه داده

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای ردگیری استاتیک متدها؛ اجرای Runtime و برابری نتیجه صفر**

برای ۲۰ سطح گزارش، بدنه متدهای همان فرم و سپس فقط Business methodهای واقعاً
فراخوانی‌شده و DataAccess methodهای مقصد بررسی شد. Assemblyها فقط Parse شدند؛
هیچ فرم، گزارش، Query یا Command اجرا نشد و هیچ مقدار عملیاتی خوانده یا ذخیره نشد.

## نتیجه

- ۱۲۵ Edge از متدهای UI به Business یا DataAccess؛
- ۲۵ Business type فراخوانی‌شده و ۶۲ Edge محدودشده از Business method به DataAccess؛
- ۱۶ DataAccess type و ۴۷ DataAccess method انتهایی؛
- ۲۶ متد انتهایی دارای نشانه اجرای Query/Reader/Scalar؛
- ۲۳ Edge مستقیم UI→DataAccess که در ERP وب نباید تکرار شود؛
- صفر Business/DataAccess method حل‌نشده، صفر خطای Method body و صفر Hash mismatch؛
- صفر اجرای Runtime و صفر اثبات Result parity.

نمونه Anchorهای قوی‌تر که اکنون تا متد انتهایی رسیده‌اند شامل Cardex مشتری و
مشتری ارزی، Cardex تأمین‌کننده، Cardex/Batch/سفارش باز موجودی، Healthy Cardex،
گزارش مشتری Call Center، مسیرهای PrintInvoice و کنترل نوع Statement هستند.

## مرز Query و Command

یک متد انتهایی دارای نشانه Mutation پیدا شد: `Thunderstruck.DataContext.Commit`.
مسیرهای رسیدن به آن از عملیات ثبت تکمیل چاپ و ذخیره Statement می‌آیند. بنابراین:

- Preview، Search، Paging و Export قرارداد Query فقط‌خواندنی هستند؛
- «علامت‌زدن چاپ به‌عنوان تکمیل‌شده» یک Command مستقل، idempotent و versioned است؛
- ذخیره Statement یک Command مستقل با مجوز، validation و optimistic concurrency است؛
- هیچ‌یک از این Commandها در تحلیل حاضر اجرا نشده‌اند و تا Golden value و UAT مجوز
  پیاده‌سازی یا Pilot ندارند.

## نتیجه برای ERP شخصی نگین

مرز پیشنهادی Web UI → Query/Command API → مالک ماژول → Repository است. دسترسی
مستقیم UI به DataAccess حذف می‌شود. این Trace فقط مسیر نام و Call را ثابت می‌کند؛
پارامتر، Branch مؤثر، SQL نهایی، Scope مجوز، محاسبات مبلغ و Result parity همچنان
نیازمند قرارداد و شاهد جدا هستند.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_report_method_paths_20260827.json`

Extractor:
`scripts/windows/extract_varanegar_report_method_paths.py`
