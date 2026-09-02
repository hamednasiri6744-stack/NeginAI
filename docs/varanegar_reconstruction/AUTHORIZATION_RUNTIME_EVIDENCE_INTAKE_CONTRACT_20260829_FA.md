# قرارداد Evidence intake برای Runtime authorization/scope — CG-01

این قرارداد شواهد authenticated authorization را برای هر ۱۴ ماژول تعریف می‌کند. طراحی Authorization در ۱۴/۱۴ وجود دارد، اما Runtime proof در ۰/۱۴ است. اجرای این قرارداد فقط پس از پذیرش ۸/۸ Slot تصمیم CG-06 در محیط ایزوله مجاز و معتبر است.

هر ماژول باید هشت دسته سناریو را با Principal مصنوعی اجرا کند: Allow معتبر، تقدم Deny صریح، Capability مفقود، Scope ناسازگار، Session epoch منقضی پس از Revoke، تضاد SoD، Break-glass خارج از محدوده/زمان و تفاوت UI visibility با Server enforcement.

Packet پانزده Field مرجعی/Hash دارد: Module، Scenario set، Principal مصنوعی، Role template، Capability، Resource scope، Session epoch، Policy version، Expected decision، Actual decision، Server enforcement، Audit، Negative cases و Approvalهای Security/Business owner.

UI Guard یا دیده‌شدن کنترل هرگز جای Server decision receipt را نمی‌گیرد. برابری Count هویت Principal/Role/Membership/Grant را ثابت نمی‌کند. Action capability، Scope، Session epoch و SoD مستقل‌اند و Deny صریح بر Allow مستقیم، گروهی، inherited و admin مقدم است.

در Identity، ۶۰ Endpoint بدون declaration روشن، ۳۸ Endpoint تغییردهنده در همان گروه و ۵۸ Scope mismatch شناخته شده باقی است؛ این Blockerها به معنی Incident در تمام ۱۴ ماژول نیستند. ۱۸۴ Case قبلی و ۴۲ Case Delta، مجموع ۲۲۶، به‌علاوه هفت Playbook فقط طراحی‌اند.

CG-01 تنها پس از CG-06 پذیرفته‌شده، ۱۴ Packet پذیرفته، پوشش هر هشت دسته، Approval مالک و Security و صفر اختلاف توضیح‌نداده‌شده بسته می‌شود. اکنون Packet، Runtime authorization، Approval، Command readiness و Pilot readiness همگی صفر و پایهٔ ۸۴ ریسک/۳۴۳ انتساب ثابت است.

هیچ Login، Session، Grant، Revoke، Assignment، فرم یا Command اجرا نشده؛ هیچ Identity/Credential/Raw grant ذخیره و هیچ اتصال دیتابیس یا دسترسی نوشتن ایجاد نشده است.
