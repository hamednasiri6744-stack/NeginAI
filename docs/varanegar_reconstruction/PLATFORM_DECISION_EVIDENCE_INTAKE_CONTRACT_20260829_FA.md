# قرارداد دریافت شواهد تصمیم‌های Platform برای CG-06

این قرارداد تعیین نمی‌کند از چه Stack، Database، Hosting یا Recovery target استفاده شود. فقط تعریف می‌کند چه شاهدی لازم است تا یک تصمیم خارجی از Proposal به `APPROVED_CURRENT` برسد.

هشت Slot تصمیم وجود دارد:

1. Stack برنامه و سرویس؛
2. پلتفرم Database؛
3. توپولوژی Hosting/Network؛
4. نقش پاسخ‌گوی Deployment، بدون ثبت هویت شخص؛
5. Policy تصویب‌شدهٔ RPO؛
6. Policy تصویب‌شدهٔ RTO؛
7. محیط ایزولهٔ شواهد Runtime با دادهٔ مصنوعی؛
8. Policy آزمون بازیابی و قرارداد Receipt سلامت/Reconciliation/External effect.

هر Packet یازده Field مرجع و Hash دارد: شناسه، Slot، Version، Status، Scope، گزینهٔ انتخاب‌شده، Approval، Role پاسخ‌گو، Effective window، Supersedes و Evidence manifest. نام شخص، Credential/Secret، Endpoint یا Connection string خام، قرارداد/پیشنهاد فروشنده و مقدار خام تجاری ممنوع است.

`PROPOSAL` هرگز Approval نیست. Approval ناقص، دو Approval جاری متعارض، تصمیم Superseded و Slot وابسته با Dependency تصویب‌نشده پذیرفته نمی‌شوند. یک Role code نیز هویت یا Effective authority شخص را اثبات نمی‌کند.

CG-06 فقط زمانی بسته می‌شود که هر هشت Slot `APPROVED_CURRENT` باشند، ترتیب وابستگی رعایت شود و Conflict صفر باشد. حتی در آن حالت، انتخاب Platform به‌تنهایی Deployment، Restore، Failover یا Runtime parity را ثابت نمی‌کند.

در Snapshot حاضر هر هشت Slot `UNSELECTED`، Packet پذیرفته‌شده صفر و CG-06 باز است. شش فرمان Platform، ۴۲ Case طراحی و هفت Playbook حفظ شده‌اند؛ Implementation، Restore drill، Runtime effect parity، Owner approval، Command readiness و Pilot readiness صفر و پایهٔ ۸۴ ریسک/۳۴۳ انتساب ثابت است.

هیچ اتصال دیتابیس، شبکه، استقرار، بازیابی، Drill، فرم، گزارش یا Procedure اجرا نشده و هیچ دسترسی نوشتن ایجاد نشده است.
