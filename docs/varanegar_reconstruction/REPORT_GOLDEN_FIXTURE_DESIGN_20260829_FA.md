# طراحی Golden Fixture برای ۲۰ سطح گزارش — ۱۴۰۵/۰۶/۰۷

برای هر ۲۰ سطح گزارش چهار fixture پایه طراحی شد: empty scope، یک aggregate معتبر، مرز cancel/delete و cross-scope. برای هشت سطح command-bearing نیز case جداگانهٔ partial/atomic failure اضافه شد؛ مجموع ۸۸ case.

Assertion براساس ownership متفاوت است: Queryهای دقیق schema/value/filter/formula؛ templateها hash/parameter/connection/render؛ shell/selector فقط route و filter propagation؛ خروجی‌های transactional نیز durable effect، completion audit و retry را بررسی می‌کنند. برای shellها value parity مستقل اختراع نشده است.

هیچ case اجرا یا owner-approved نشده و result parity اثبات‌شده همچنان صفر است. Promotion فقط بعد از fixture approval، capture ایزولهٔ legacy/target، مقایسهٔ بدون اختلاف توضیح‌نداده‌شده و signoff مالک انجام می‌شود.
