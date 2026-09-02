# Triage ایستای Graph تکثیر رسید POS

این موج فقط Artifact ایستای قبلی را تحلیل می‌کند. هیچ اتصال تازه به پایگاه داده، اجرای Procedure/Trigger، خواندن Definition یا مقدار تجاری و هیچ Mutationی انجام نشده است.

## مرز کامل‌نبودن Graph

Graph ذخیره‌شده ۵۰۰ گره و ۱۰۳۹ Edge دارد و به سقف ایمنی رسیده است. صف توسعه‌نیافته ۱۶۰ عضو دارد، اما هویت آن در Artifact مبدأ ذخیره نشده؛ بنابراین نمی‌توان آن را با ۱۵۱ ماژول callable موجود در مرز عمق سه یکی دانست. مرز عمق سه در مجموع ۱۸۳ گره دارد: ۱۵۱ ماژول callable و ۳۲ Table.

در ۱۵۱ ماژول مرزی، ۴۴ سیگنال lexical تراکنش، چهار TRY/CATCH و چهار Dynamic-SQL signal دیده می‌شود. اینها فقط علامت ایستا هستند و مالکیت تراکنش، Rollback موفق یا Effect parity را ثابت نمی‌کنند.

## اصلاح معنای unresolved

از ۱۷۹ نام unresolved، تعداد ۱۶۸ مورد `inserted/deleted` و در نتیجه pseudo-tableهای SQL هستند. این موارد از شمارش اصلی حذف نشده‌اند، ولی به‌عنوان Catalog object گمشده تفسیر نمی‌شوند. یازده مورد دیگر برای رفع Alias/CTE، Type یا نام بی‌schema نیازمند شاهد ایستای تکمیلی‌اند.

## چرخه‌ها و Mutation lower bound

یازده Strongly Connected Component چرخه‌ای با ۶۸ گره وجود دارد؛ بزرگ‌ترین چرخه ۱۷ گره دارد. این ۶۸ گره شامل ۴۸ Trigger، نوزده Table و یک Stored Procedure هستند. وجود چرخه ترتیب Runtime را تعیین نمی‌کند، اما برای تعیین Transaction owner و Cascade mutation باید با اولویت بررسی شود.

۴۸ Write target حل‌شده فقط lower bound هستند، چون Graph truncated است و Dynamic SQL signal نیز وجود دارد. مرحلهٔ بعد به export ایستای redacted با bound بازبینی‌شده، manifest هویت صف و crosswalk mutation/trigger نیاز دارد. تا آن زمان Atomicity، Effect parity، Command readiness و Pilot readiness صفر باقی می‌مانند.
