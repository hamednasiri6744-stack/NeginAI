# Golden Case و UAT Design حسابداری — ۱۴۰۵/۰۶/۰۷

برای شش فرمان اصلاح‌شدهٔ حسابداری، ۴۲ case مصنوعی طراحی شد: authorization، stale version، idempotency، failure injection، scope، success و یک حالت ویژه برای هر فرمان.

حالت ویژهٔ transfer، business-error همراه durable cleanup را صریح می‌آزماید؛ retry تا read-back ممنوع است. خانوادهٔ `manual_voucher.cancel` کاملاً حذف شده، چون آن مسیر فقط UI-close است. Manual Save نیز invalid balance/ledger dimension دارد.

هیچ case اجرا نشده و هیچ تأیید مالک وجود ندارد. اجرا فقط در target test database ایزوله، با fixture مصنوعی و اجازهٔ جداگانه مجاز است؛ Clone یا Production وارانگار هرگز مقصد mutation نیست.
