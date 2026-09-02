# ماتریس سیاست Formula و Grain برای Result-ownerهای گزارش

این ماتریس فقط ۱۱ سطحی را پوشش می‌دهد که مالک مستقل نتیجه‌اند. از ۲۰ سطح گزارش، هشت مورد Query-bound، دو مورد Template-owned و یک مورد Bank typed read/summary هستند. نه سطح Viewer/Shell/Selector/Command-only خارج از زیرGate فرمول باقی می‌مانند و با این سند به Result owner تبدیل نمی‌شوند.

## مرز شواهد

- در ۹ سطح، شکل ایستای Grain معلوم است ولی سیاست مالک هنوز تصویب نشده است.
- در `RPT-11` و `RPT-12`، Query، Subreport، Formula field و Grain داخل Template خارجی‌اند و استخراج نشده‌اند؛ بنابراین Grain آنها `UNKNOWN_UNTIL_TEMPLATE_EXTRACTION` است.
- `RPT-19` یازده Formula طراحی‌شده دارد، اما وجود Formula design به معنی Runtime parity یا Approval مالک نیست.
- برای این ۱۱ سطح، ۵۰ Golden fixture طراحی شده و اجرای آنها صفر است.

## چهارده بُعد سیاست

هر سطح باید Grain/key، تاریخ و Watermark، Scope، Status/Cancel/Delete، Null، Sign، Decimal/Rounding، Unit/Currency، Ordering/Pagination/Total و Version identity را تعیین کند. بسته به نوع گزارش، Opening/Closing، Mode discriminator، Template internals یا Master-detail reconciliation نیز اضافه می‌شود. مجموع این تخصیص‌ها ۱۲۳ الزام سیاستی است.

## قواعد پذیرش

مقایسه ابتدا روی Stable key set و سپس روی Measure انجام می‌شود؛ برابری Total نمی‌تواند حذف یا جابه‌جایی Row را پنهان کند. Null به صفر، Sign معکوس، Round در سطح Row یا Aggregate و تبدیل Currency/Unit فقط با Policy نسخه‌دار معتبر است. Status و Business date نیز ورودی Formula هستند.

Packet هر سطح بیست Field مرجعی/Hash دارد و باید Source/Target run receipt، Fixture/Filter/Scope/Watermark، Key set و Delta manifest را به نسخهٔ Grain/Formula/Null/Sign/Rounding/Currency/Status متصل کند. مقدار خام گزارش، PII و Approval mutable ممنوع است.

Snapshot فعلی: Packet پذیرفته ۰/۱۱، Fixture اجراشده ۰/۵۰، Formula owner approval صفر، Result parity صفر و Command/Pilot readiness صفر. این Matrix فقط زیرGate Result-owner در `CG-05` است و نه Packet غیرنتیجه‌ای دیگر را نمی‌بندد.
