# مرز Navigation و precedence تنظیمات سیستم

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای قرارداد طراحی؛ Effective value/precedence و اثر Runtime فرمان‌ها صفر**

## نتیجه

ریشه‌ی «تنظیمات سیستم» پنجاه Route دارد. پانزده Route به FormInfo/AccessNode
پیکربندی‌شده وصل‌اند، اما فقط چهار مورد به Form type موجود در بسته Runtime
منطبق شدند؛ یازده مورد Runtime-unmatched باقی ماندند. این سطح شامل پنج مسیر
مدیریت تاریخ قطعی، پنج مسیر انتشار/Integration تنظیمات، دو مسیر سال مالی و
Close/Reopen، دو مسیر دسترسی/نگهداری ویژه و یک مسیر Template/version است.

شاهد دامنه‌ی فقط‌خواندنی نیز ۱۴ جدول تنظیمات، ۱۷۷ کلید General، ۳۳۴ کلید
Server، چهل کلید فقط‌تاریخی، ۲۲ Rule key میان‌ماژولی، دو ردیف DC config، ۵۱
Field تنظیم مشتری و چهل Device setting را نشان می‌دهد؛ ۲۳ Device setting حذف‌شده
است. هیچ مقدار تنظیم، مقدار تاریخچه، Credential، URL، Path، Host یا مالک Device
در این قرارداد ذخیره نشده است.

## اثر معماری مقصد

ERP نگین باید precedence صریح `global → server → DC → device → app → user
exception` داشته باشد و برای هر تصمیم Effective، Key، Scope، Version، Hash
غیرمحرمانه‌ی مقدار، Source policy و زمان ارزیابی را Explain کند. Draft و
Published version جدا هستند؛ تاریخ قطعی و Close مالی Command مستقل‌اند و نباید
مثل ویرایش ساده‌ی Setting پیاده شوند. Web-service secret فقط در Secret store
می‌ماند و کلیدهای History-only تا تصمیم Retain/Rename/Retire قرنطینه‌اند.

اولین Slice مجاز، کاتالوگ فقط‌خواندنی Effective setting و Explain بدون Value یا
Secret است. Write تا Review مالک روی precedence، نگاشت دقیق Consumer، UAT
احرازشده، Rollback و Reconciliation روی Target ایزوله مسدود می‌ماند.

## شواهد و محدودیت

- Artifact: `varanegar_system_configuration_navigation_contract_20260827.json`
- Builder: `build_varanegar_system_configuration_navigation_contract.py`
- Source domain: `configuration_and_rule_flags_20260826.json`
- هیچ Save/Close/Reopen/Publish/Apply-system-change/Send/Receive اجرا نشده است.
- نام Route، Key یا Dependency به‌تنهایی Effective value یا precedence را ثابت
  نمی‌کند.
