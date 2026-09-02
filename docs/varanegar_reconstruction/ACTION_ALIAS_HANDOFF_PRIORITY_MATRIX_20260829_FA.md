# ماتریس اولویت تحویل Action Alias ـ ۲۰۲۶-۰۸-۲۹

۲۹ Packet حل‌نشدهٔ Action Alias با حفظ کامل ۲۰۳ Case در پنج صف بررسی risk-first مرتب شد. این اولویت‌بندی فقط ترتیب جمع‌آوری مدرک و disposition نقش‌ها را تعیین می‌کند و نه severity عملیاتی، نه انتساب مالک حقیقی، نه پذیرش Alias و نه مجوز UAT است.

- `P0`: هفت Packet/۴۹ Case برای مرزهای برگشت‌ناپذیر، reversal، اثر بین‌ماژولی یا replication.
- `P1`: هشت Packet/۵۶ Case برای ایجاد یا transition مالی، confirm/cancel و match/unmatch.
- `P2`: شش Packet/۴۲ Case برای سیاست قیمت، ورودی قابل‌ویرایش خزانه و ورودی integration.
- `P3`: پنج Packet/۳۵ Case برای import/command/print و مرزهای stateful گزارش.
- `P4`: سه Packet/۲۱ Case برای export فقط‌خواندنی؛ Result parity همچنان Gate جداگانه و اثبات‌نشده است.

هر تحویل دو role type و نه فیلد evidence دارد؛ در مجموع ۵۸ تخصیص نقش طراحی شده است. `named_owner_assignment`، handoff پذیرفته‌شده، disposition پذیرفته‌شده، اجرای Case و اثر افزایشی همگی صفر هستند. lower bound طراحی ۱۴۰۴ و پایهٔ ریسک/ردیابی ۸۴/۳۴۳ ثابت مانده است.

تا وقتی Alias نسخه‌دار، نگاشت precondition/outcome/assertion، receipt hash، سیاست expiry و disposition صریح نقش‌ها ارائه نشده باشد، وضعیت هر Packet `WAITING_FOR_ROLE_DISPOSITION_AND_VERSIONED_ALIAS` باقی می‌ماند.
