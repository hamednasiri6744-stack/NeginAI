# گزارش کاردکس سلامت و مرز Print Attempt — ۲۰۲۶-۰۸-۲۹

## نتیجه

`RPT-18` از ۸۵ Candidate نامی به دو Procedure دقیق کاهش یافت:

- Master: `ICA.USP_VchHealthyCardex_GetList`
- Detail: `ICA.USP_VchHealthyCardexDetails_GetList`

هر دو در Catalog Clone فقط‌خواندنی حل شدند و مجموعاً ۱۸ پارامتر و چهار dependency
دارند. Master ورودی‌های `UserRef/Username/StatusList/FilterDate` و `Where` دارد و
Dynamic SQL در تعریف آن دیده می‌شود؛ Detail فاقد Dynamic SQL است. وجود Dynamic SQL
به‌تنهایی Incident یا Injection جاری را ثابت نمی‌کند، اما مقصد باید `Where` خام را
به Filter AST نوع‌دار و allowlisted تبدیل کند.

## Truth Table چاپ

ترتیب IL مسیر `i_Click` چنین است:

1. `GetSelectedDocIds` در offset 45؛
2. `InsertInTotblSdsNetPrintDoc` در offset 72؛
3. `frmPreview2.ShowReport` در offset 124.

پس ردیف PrintDoc قدیم «درخواست/تلاش چاپ» است، نه اثبات Render یا چاپ فیزیکی موفق.
اگر Render خطا دهد یا کاربر لغو کند، Attempt ممکن است قبلاً ثبت شده باشد. Retry و
Idempotency این مسیر اثبات نشده‌اند.

## قرارداد مقصد

- Preview کاملاً Read-only و بدون Print audit؛
- Export فقط External-file event و بدون mutation در ERP؛
- چاپ فیزیکی Command جدا، idempotent و پس از confirmation؛
- رخدادهای تغییرناپذیر `PRINT_REQUESTED`، `RENDER_SUCCEEDED`،
  `PHYSICAL_PRINT_CONFIRMED` و `PRINT_FAILED_OR_CANCELLED`؛
- Authorization deny-first برای Action و DC/Stock/Goods scope؛
- Result parity روی Master/Detail key-set، quantity، status، date و scope در UAT
  ایزوله و Snapshot ثابت.

## Playbook اختلاف یا Print history کاذب

Hash دو Procedure و UI را Pin کن؛ Scope سال/DC/User/Status/Date/Goods/Stock را
همسان کن؛ `Where` را canonicalize کن؛ رابطه Master/Detail و Grain FIFO را بسنج؛
Preview، Export و Physical print را جدا کن؛ وجود PrintDoc را فقط Attempt بدان و
تکمیل `ShowReport` را مستقل اثبات کن.

Query identity و ترتیب IL تأییدشده‌اند؛ Runtime branch، Transaction، Success واقعی
و Result parity اثبات‌نشده‌اند. Risk جدید ساخته نشد و `R-017` همراه ریسک‌های موجود
reuse شد. هیچ UI/Report/Export/Procedure اجرا و هیچ داده‌ای تغییر داده نشد.
