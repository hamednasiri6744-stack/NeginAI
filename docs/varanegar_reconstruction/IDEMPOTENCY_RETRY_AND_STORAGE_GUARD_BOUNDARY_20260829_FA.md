# مرز Idempotency، Retry و Guardهای ذخیره‌سازی وارانگار

تاریخ استخراج: ۲۰۲۶-۰۸-۲۹  
وضعیت: **Catalog و Aggregate فقط‌خواندنی؛ رخداد Retry به Actor یا درخواست خاص نسبت داده نشد**

## نتیجهٔ کوتاه

ده فرمان پراثر از فروش، برگشت، توزیع، انبار، حسابداری و چاپ بررسی شدند. هیچ‌کدام
پارامتر صریحی با معنای `CommandId`، `RequestId`، `IdempotencyKey`، Attempt یا
Correlation ندارند. شش فرمان از این ده مسیر، تخصیص شناسهٔ تازه دارند. بنابراین
در سطح قرارداد عمومی فرمان، «تکرار همان درخواست» از «قصد تجاری تازه» قابل تشخیص
نیست.

این به معنی نبود همهٔ محافظ‌ها نیست. پنج جدول از هفت جدول هدف، Unique guard
معنایی دارند؛ اما هر Guard فقط یک Projection خاص را حفظ می‌کند و Receipt نتیجهٔ
قبلی را بازنمی‌گرداند. پاک‌بودن Snapshot نیز جای Command receipt را نمی‌گیرد.

## فرمان‌های منتخب

فرمان‌های تبدیل سفارش به فروش، لغو فروش، ساخت سند برگشت فروش، ساخت خروج توزیع،
تأیید/برگشت تأیید سند انبار، صدور/انتقال سند حسابداری، ساخت Snapshot ووچر فروش
و ثبت چاپ بررسی شدند.

| معیار | نتیجه |
|---|---:|
| فرمان منتخب | ۱۰ |
| دارای پارامتر صریح Idempotency | ۰ |
| دارای سیگنال تخصیص شناسه | ۶ |
| جدول هدف منتخب | ۷ |
| جدول دارای Unique guard معنایی | ۵ |

وجود `IF EXISTS/NOT EXISTS` در متن Procedure به‌تنهایی Idempotency نیست: ممکن
است فقط یک precondition، branch انتخابی یا guard جزئی باشد و نتیجهٔ نخستین اجرا
را به Retry برنگرداند.

## Guardهای واقعی و دامنهٔ پوشش

### سفارش به فروش

`SLE.tblSaleHdr` Unique معنایی برای «حداکثر یک Sale فعال به‌ازای OrderRef» ندارد.
Snapshot فعلی ۲۱۴٬۹۷۳ گروه سفارش فعال و صفر گروه چندفروش فعال دارد؛ پس invariant
جاری سالم است، اما اجرای هم‌زمان یا crash-after-commit توسط Constraint مستقل
پوشش داده نمی‌شود.

### برگشت فروش و سند ورود نوع ۱۰

- روی Header برگشت، Unique فیلترشده برای منبع برگشت فعال وجود دارد؛
- روی Voucher نوع ۱۰، Unique فیلترشدهٔ Source/Health وجود دارد؛
- ۱۳٬۹۱۳ گروه Voucher منبع/سلامت فعلی همگی یکتا هستند.

با این حال cohort جاری Headerهای دارای منبع `RetOrderRef` که با Filter اول منطبق
باشد، صفر است. پس وجود Constraint قطعی است ولی برابری Runtime آن با مسیرهای فعال
از دادهٔ فعلی آزموده نشده است.

### خروج توزیع

Unique فیلترشدهٔ `(DistRef, StockDCRef, AccYear)` برای خروج غیرلغوشده وجود دارد.
۲۴٬۰۳۵ گروه فعال، صفر duplicate و بیشینهٔ یک خروج دارند. این Guard از Projection
فعال محافظت می‌کند، اما History، Voucher، Sale link و نتیجهٔ قبلی فرمان را پوشش
نمی‌دهد.

### PreVoucher و صدور حسابداری

امضای کامل Line شامل Creator، Source، Article و ابعاد حساب یکتاست و در
۲٬۳۷۰٬۵۶۹ گروه هیچ duplicate ندارد. این Constraint تکرار همان Line را متوقف
می‌کند؛ Receipt سطح فرمان، Grouping batch، Warning/Rejected outcome و Reissue پس
از حذف Batch را تضمین نمی‌کند.

### چاپ

`GNR.tblPrintedDoc` فقط PK فنی دارد و روی `(DocType, DocRef)` یکتا نیست. این
رفتار لازم است چون Reprint مجاز است: ۵۵٬۷۹۲ سند بیش از یک رخداد و بیشینهٔ ۸۸
رخداد دارند. بدون `PrintAttemptId/CommandId` نمی‌توان از خود Eventها فهمید کدام
تکرار Retry همان Attempt و کدام Reprint تازه بوده است؛ هیچ duplicate incident
نسبت داده نشد.

### TourHistory در NGT

Unique روی `EntityUniqueId` فقط برای یک نوع تاریخچه اعمال می‌شود. همان نوع
۱٬۱۱۸٬۲۴۴ گروه و صفر duplicate دارد، ولی نوع فروش ۱۳۸ گروه تکراری و نوع پرداخت
۷۰ گروه تکراری با بیشینهٔ شش تاریخچه دارند. این نتیجه با بررسی‌های مستقل NGT
سازگار است و فقط ضعف Ledger/Receipt را ثابت می‌کند، نه تکرار همهٔ اثرهای مالی.

## قرارداد مقصد

هر فرمان تغییر‌دهنده باید ورودی‌های زیر را داشته باشد:

- `CommandId` تولیدشده توسط Caller و پایدار در Retry؛
- `PayloadHash` canonical از ورودی مؤثر کسب‌وکار؛
- `ExpectedVersion` یا Expected state برای کنترل رقابت؛
- Actor/Scope/OperationDate/PolicyVersion؛
- Receipt تغییرناپذیر شامل Outcome، شناسهٔ Aggregate، نسخهٔ نتیجه و Outbox refs.

رفتار اجباری:

1. همان Key و همان Payload، نتیجهٔ نخست را بدون اثر تازه برگرداند.
2. همان Key با Payload متفاوت، پیش از Write به‌عنوان Conflict رد شود.
3. دو درخواست هم‌زمان با یک Key، یک Writer و یک Receipt مشترک داشته باشند.
4. Unique constraintهای معنایی به‌عنوان آخرین Guard نگه داشته شوند، نه جایگزین
   Receipt.
5. Retry همان CommandId را نگه دارد؛ Reprint/تلاش تازه CommandId تازه و لینک به
   Attempt قبلی داشته باشد.
6. نتیجهٔ نامعلوم Commit ابتدا با CommandId reconcile شود و بعد اجازهٔ Replay
   بگیرد.

## ایمنی و محدودیت

- Clone `READ_ONLY` و حساب تحلیل فاقد مجوز Update بود؛
- هیچ Procedure، Trigger، فرم، Report یا Command اجرا نشد؛
- فقط Definition hash، پارامترها، Index metadata و Aggregate ناشناس خوانده شد؛
- Index name، Filter literal، SQL خام، ردیف/شناسه/نام کسب‌وکاری و متن پیام ذخیره نشد؛
- Static signal و Aggregate جاری، branch frequency یا علت تاریخی duplicate را
  ثابت نمی‌کند.

## خروجی بازتولیدپذیر

- Extractor:
  `scripts/sql/extract_varanegar_idempotency_guard_boundary.py`
- Artifact:
  `artifacts/varanegar_analysis/domains/idempotency_guard_boundary_20260829.json`
- Test:
  `tests/test_varanegar_idempotency_guard_boundary.py`
