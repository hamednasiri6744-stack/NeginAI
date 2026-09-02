# مرز مشترک مدیریت تاریخ قطعی فروش، خرید، مالی و تنخواه

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای قرارداد Static؛ Runtime effect، Transaction parity و Golden execution صفر**

## نتیجه

پنج Route پیکربندی‌شده برای تاریخ قطعی شعب/فروش، خرید، مالی، خزانه و تنخواه
وجود دارد؛ دو Route فروش به Form runtime منطبق و سه Form خرید/مالی/تنخواه در
Package حاضر ولی Runtime-unmatched هستند. Form فروش ۱۹ Method دارد و Save،
Validate و مرزهای AccYear/DC/User/Last/Open date را صدا می‌زند.

سه Capability افزونه‌ی خرید، مالی و تنخواه همگی مسیر Business mediation دارند
و direct UI→DataAccess آن‌ها صفر است. Handler مشترک چهار Update و پنج Validation
و DataAccess چهار Update و چهار Validation دارد. Clone نیز چهار Edge مصرف‌کننده
نامی مرتبط با FinalDateManagement در سال/مرکز/انبار نشان می‌دهد؛ این اسامی اثر
Runtime یا Atomicity را ثابت نمی‌کنند.

## قرارداد مقصد

این قابلیت باید چهار Command مستقل باشد:

1. `configuration.set_sales_final_date`
2. `configuration.set_purchase_final_date`
3. `configuration.set_financial_final_date`
4. `configuration.set_petty_cash_final_date`

هر Command با DC و FiscalYear نسخه‌گذاری می‌شود. Open date و Final date یکی
نیستند؛ عقب‌بردن مرز به Command صریح Reopen و دلیل/Audit نیاز دارد. قبل از Commit
باید مصرف‌کنندگان فروش، خرید، خزانه، تنخواه و حسابداری ارزیابی شوند؛ تغییر مرز
نباید اسناد عملیاتی را بی‌صدا بازنویسی کند. Commit نسخه، Audit و Outbox اتمیک و
Replay با همان CommandId تک‌اثر است.

## Gate و محدودیت

- Artifact: `varanegar_final_date_management_boundary_20260827.json`
- Builder: `build_varanegar_final_date_management_boundary.py`
- Gate: معنای تاریخ مورد تأیید مالک، inventory دقیق اثر SQL، تست‌های
  stale/reopen/overlap/failure، UAT احرازشده و Reconciliation روی Target ایزوله.
- هیچ تاریخ واقعی، سند تحت اثر، هویت، Validation result یا Command effect خوانده
  یا ذخیره نشد و هیچ Procedure/Command اجرا نشد.
