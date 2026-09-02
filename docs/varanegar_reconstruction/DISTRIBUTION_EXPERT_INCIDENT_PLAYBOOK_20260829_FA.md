# Playbook تخصصی رخدادهای توزیع — ۱۴۰۵/۰۶/۰۷

پنج رخداد پوشش داده شد: conflict شماره/history در Create، شکست late-cardex در Issue، نتیجهٔ نامعلوم Merge، cleanup ناقص Remove و غیبت رکورد با باقی‌ماندن audit/history.

روش مشترک، کنترل hash، read-back توزیع/خروج/سند نوع ۶۰/sale links/history/audit، مقایسه outcome با اثر durable و طبقه‌بندی چهارحالته است. هیچ پیام یا transport status به‌تنهایی rollback را ثابت نمی‌کند و repair مسیر مجاز جداگانه‌ای می‌خواهد.

هشت خروج ثبت‌شده و شش توزیع تاریخیِ غایب فقط شاخهٔ تشخیصی را فعال می‌کنند و وضعیت زنده تولید نیستند. runtime diagnosis، repair و owner approval صفر است.
