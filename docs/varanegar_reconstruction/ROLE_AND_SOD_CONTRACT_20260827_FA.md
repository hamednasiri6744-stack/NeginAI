# قرارداد نقش و تفکیک وظایف ERP شخصی نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **Template موقت و بدون هویت؛ نیازمند تأیید مالک کسب‌وکار**

## نتیجه

مدل مقصد با «دیدن منو» یا یک ستون Admin امن نمی‌شود. تصمیم نهایی باید حاصل
اشتراک Authentication، Capability allow، نبود Explicit deny، Data scope، Context
باز، Feature/config و Domain guard باشد. تغییر سال/مرکز نیز تمام Routeها را
دوباره مجازسنجی و Cache/Query وابسته را باطل می‌کند.

بر اساس ۱۶ Capability مشاهده‌شده، ۴۰ Node چهار Route فعال و ۲۰ Report surface،
Registry مقصد ۴۵ Capability اتمیک، ۱۵ Role template و ۱۰ قاعده SoD دارد. هیچ نام
کاربر، گروه یا Grant فردی در Artifact ذخیره نشده است.

## Role templateهای پیشنهادی

- Business reader؛
- Master-data steward؛
- Sales operator؛
- Distribution planner؛
- Warehouse exit operator؛
- Distribution exception controller؛
- Receivables operator؛
- Payables operator؛
- Treasury exception controller؛
- Financial controller؛
- Report exporter؛
- Security administrator؛
- Configuration publisher؛
- Migration operator؛
- Migration reviewer.

این‌ها عنوان شغل یا تخصیص به اشخاص واقعی نیستند. هر Template یک نقطه شروع برای
UAT و Approval کسب‌وکار است و Scope مرکز/دفتر/انبار/سال جداگانه به آن متصل می‌شود.

## ده تضاد اصلی

1. Grant نقش/Scope با هر Business mutation؛
2. ساخت/ویرایش توزیع با صدور خروج؛
3. صدور خروج با Remove/Reverse/Merge استثنایی؛
4. تغییر وضعیت چک دریافتی با Undo همان چرخه؛
5. تغییر وضعیت چک پرداختنی با Undo همان چرخه؛
6. عملیات دریافتنی و پرداختنی توسط یک نقش؛
7. Posting با Reverse/Close period؛
8. Publish تنظیم مؤثر با اجرای همان عملیات کسب‌وکاری؛
9. Capture/Import مهاجرت با Resolve quarantine؛
10. Export فایل با دسترسی بدون Scope به داده حساس.

تضادهای Critical Hard-exclusion یا Operator/Reviewer separation می‌خواهند.
تضادهای عملیاتی در شرایط کمبود نیرو فقط با Break-glass محدود، Approval مستقل،
Expiry، Reason و Reconciliation بعدی قابل عبورند.

## Approval contract

Approval باید Capability، Aggregate/Scope، Context، Reason، Evidence، زمان
انقضا، مصرف یک‌باره و Audit event داشته باشد. درخواست‌کننده نمی‌تواند درخواست
خودش را تأیید کند و Approval کلی یا دائمی برای Command مادی پذیرفته نیست.

## تست‌های منفی الزامی

- منو دیده شود ولی Command مجاز نباشد؛
- Capability مجاز ولی DC/Stock/SaleOffice Scope رد شود؛
- Explicit deny بر Allow گروه غلبه کند؛
- Context switch تصمیم قبلی را باطل کند؛
- Feature خاموش یا State نامعتبر Role مجاز را هم متوقف کند؛
- Self-grant/Self-approval، Approval منقضی یا مصرف‌شده رد شود؛
- Drill-down و Export دوباره Row/Field scope را ارزیابی کنند.

## مرز نتیجه

Evidence تجمیعی Legacy نقش مناسب هیچ شخص، Grant فردی، Staffing تولید یا
Break-glass assignee را ثابت نمی‌کند. Artifact هیچ Role یا Grant واقعی را تغییر
نداده است.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/negin_erp_role_sod_contract_20260827.json`
- `scripts/windows/build_negin_erp_sod_role_contract.py`
- `tests/test_varanegar_ui_evidence.py`
