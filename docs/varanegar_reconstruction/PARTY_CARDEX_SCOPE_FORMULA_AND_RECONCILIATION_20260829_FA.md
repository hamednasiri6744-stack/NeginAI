# مرز Scope، Formula و Reconciliation کاردکس طرف‌حساب

این موج سه گزارش `RPT-05`، `RPT-07` و `RPT-08` را بدون اجرای فرم، گزارش، View،
Procedure یا درخواست دوردست به شواهد دقیق‌تر متصل کرد. دو DLL فقط با PE/CLR metadata
و IL ایستا خوانده شدند و Catalog فقط‌خواندنی Clone پس از کنترل `READ_ONLY`،
`can_update=0` و deny-write بررسی شد.

## یافته‌های قطعی

- `RPT-05` به `dbo.usp_sdsnet_SupplierCardex` متصل است.
- `RPT-07` از `dbo.usp_sdsnet_CustomerCardex_Currency` و دو lookup
  `GNR.vwCust` و `SLE.vwFreeInvoiceHdr` استفاده می‌کند.
- `RPT-08` مسیر محلی `dbo.usp_sdsnet_CustomerCardex` دارد، اما مسیر
  `CustomerCardexCentralized` Query محلی نیست و به `FararuHelper.ExecuteRequest`
  تفویض می‌شود.
- پنج شیء SQL دارای ۳۹ پارامتر و ۶۶ dependency ثبت‌شده در Catalog هستند.
- ۴۵۵ candidate نامی قبلی جای binding دقیق را نمی‌گیرند.

## مرزی که هنوز اثبات نشده است

وجود نام‌های debit/credit/remain، aggregate و currency در تعریف‌ها هویت و شکل
Projection را تقویت می‌کند، ولی Formula نهایی، علامت مانده افتتاحیه، rounding،
نرخ ارز و Result parity را ثابت نمی‌کند. هیچ مقدار تجاری، متن خام SQL یا هویت شخصی
ذخیره نشده است. مسیر مرکزی نیز ممکن است stale یا unavailable باشد؛ مقصد حق ندارد
بی‌صدا نتیجه محلی را جایگزین آن کند.

## قرارداد مقصد ERP

Ledger movement باید fact منبع بماند و Cardex یک Projection نسخه‌دار و قابل بازسازی
باشد. Scope شامل سال مالی، DC، کاربر/مجوز، وضعیت، fetch reason، تاریخ تجاری، طرف،
دفتر فروش و فیلتر گزارش است. گزارش ارزی باید transaction currency، base currency،
rate source/date و rounding را مستقل نگه دارد. هر پاسخ باید filter hash و source
watermark داشته باشد و دسترسی deny-first باشد.

## Playbook اختلاف

ابتدا Hash منابع و branch محلی/مرکزی، سپس Scope و تاریخ، بعد key-set اسناد و در
مرحله آخر opening/period/closing و currency مقایسه می‌شود. اختلاف باید در یکی از
کلاس‌های scope، date basis، central staleness، currency/rate، opening policy،
sign/rounding یا projection drift قرار گیرد؛ Projection گزارش مجوز اصلاح Ledger نیست.

شش Golden Case ناشناس برای تفکیک ارز، قطع منبع مرکزی، مانده تأمین‌کننده، Scope
سازمانی، تکرار read در watermark ثابت و اختلاف Formula ثبت شد. Result parity و UAT
همچنان صفر است. ریسک تازه‌ای ساخته نشد و یافته‌ها به `R-002/R-008/R-009/R-013/
R-021/R-023/R-031/R-036` متصل شدند؛ شمارش ریسک ۸۴ باقی ماند.
