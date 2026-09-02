# ورودی تصمیم Stack و بازیابی ERP نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **Proposal؛ هنوز ADR یا RPO/RTO تأییدشده نیست**

ورودی تصمیم اکنون ۱۷ ریسک بحرانی باز را حمل می‌کند؛ انتخاب Stack هیچ‌کدام را
به‌خودی‌خود نمی‌بندد و به‌ویژه `R-033` تا `R-036` نیازمند مرز Command/Transaction مستقل از UI هستند.

## پیشنهاد من

مسیر کم‌ریسک برای شروع، **Modular Monolith** است:

- Backend: توسعه‌ی ظرفیت موجود Python/FastAPI به ماژول‌های دامنه‌ی صریح؛
- Web: پوسته‌ی جدید TypeScript و Component-based با RTL کامل؛ PWA فعلی مرجع و
  Integration باقی بماند، نه محل پیاده‌سازی ۴۴۵ فرم؛
- Database مقصد: تصمیم کاربر بین SQL Server و PostgreSQL؛ SQLite فقط برای Slice
  شخصی/Offline مناسب است و System of Record مالی چندکاربره نباشد؛
- Job: ابتدا Job دیتابیسی و Transactional Outbox/Inbox؛ Broker جدا فقط پس از
  نیاز اندازه‌گیری‌شده؛
- Deployment: یک مرز برنامه و یک DB در هر Environment پشت Reverse proxy موجود.

این پیشنهاد از Repository فعلی می‌آید: ۵۷ فایل Python برنامه، ۲۱ Route module،
۴۳ ماژول تست، FastAPI، اتصال SQL Server، SQLite محلی، PWA و Caddy از قبل وجود
دارند. بازنویسی فوری Backend به .NET قبل از تثبیت Domain semantics، هزینه و ریسک
دوباره‌کاری می‌سازد. .NET/SQL Server همچنان گزینه‌ی معتبر است اگر تیم پشتیبان
بلندمدت واقعاً روی آن مهارت و مالکیت عملیاتی بیشتری داشته باشد.

## گزینه‌ی پیشنهادی بازیابی

برای ERP مالی Write-enabled، نقطه‌ی شروع پیشنهادی:

- RPO حداکثر ۵ دقیقه؛
- RTO حداکثر ۶۰ دقیقه در ساعات پشتیبانی؛
- Backup کامل رمزگذاری‌شده روزانه + Log/WAL مکرر؛
- Restore ایزوله فصلی با Smoke test برنامه و Reconciliation.

گزینه‌ی کم‌هزینه‌تر RPO=15m/RTO=2h و گزینه‌ی HA نزدیک صفر/15m هم در Artifact
ثبت شده‌اند. انتخاب نهایی باید با هزینه‌ی توقف واقعی و مالک پشتیبانی انجام شود.

## شش تصمیمی که از کاربر لازم است

1. مالک پشتیبانی و مهارت غالب تیم؛
2. SQL Server یا PostgreSQL؛
3. Windows موجود، Windows Server جدا یا Linux VM/Container؛
4. Tier بازیابی و ساعات پشتیبانی؛
5. تعداد کاربر همزمان و رشد یک‌ساله؛
6. Offline انبار/فروشنده در Release اول لازم است یا نه.

## زمان

برآورد Blueprint فعلی برای تیم کوچک متمرکز ۲۱ تا ۳۳ هفته و برای اولین Slice
فقط‌خواندنی قابل‌استفاده ۳ تا ۵ هفته است. این برآورد بعد از انتخاب Stack، Hosting،
Recovery target و دسترس‌بودن مالک‌های کسب‌وکار باید دوباره تخمین زده شود؛ برای یک
توسعه‌دهنده به‌تنهایی نباید همان زمان تقویمی فرض شود.

Artifact:
`artifacts/varanegar_analysis/ui/negin_erp_stack_recovery_decision_input_20260827.json`

Builder:
`scripts/windows/build_negin_erp_stack_and_recovery_decision_input.py`
