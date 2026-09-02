# ماتریس Playbook کارشناسی وارانگار — ۱۴۰۵/۰۶/۰۷

این ماتریس ده رخداد الزامی را پوشش می‌دهد: تبدیل ناقص سفارش، ناسازگاری پس از لغو فروش، اختلاف فاکتور/Voucher/حسابداری، اختلاف StockGoods/Cardex، تاریخچه ناقص چک/Receipt، Replication تکراری یا ناقص، اختلاف گزارش و جدول عملیاتی، تخفیف/جایزه محاسبه‌نشده، رد Permission/Scope/OperationDate و Commit موفق همراه خطا یا Partial Success.

## روش مشترک

برای هر رخداد ابتدا شناسه، زمان کسب‌وکاری، سال مالی، DC و نقش بدون PII ثبت می‌شود؛ سپس hash و drift کنترل، timeline فقط‌خواندنی بازسازی، precondition/state/scope/side-effect مقایسه و نتیجه در یکی از چهار طبقه قرار می‌گیرد: رفتار طبیعی، بدهی داده، Bug یا اثبات‌نشده. هرجا اثبات به write، اجرای فرم/فرمان، داده حساس یا repair نیاز داشته باشد بررسی متوقف و UAT ایزوله طراحی می‌شود.

جزئیات ماشین‌خوان هر Playbook شامل evidence-to-collect، ترتیب تشخیص، decision rule، stop condition، پیوند ریسک و اثر قرارداد ERP مقصد در `artifacts/varanegar_analysis/varanegar_expert_incident_playbook_20260829.json` ثبت شده است.

این artifact وقوع یا علت یک incident مشخص را ادعا نمی‌کند؛ برای آن باید شواهد همان رخداد، بدون تغییر سیستم، به Playbook داده شود.
