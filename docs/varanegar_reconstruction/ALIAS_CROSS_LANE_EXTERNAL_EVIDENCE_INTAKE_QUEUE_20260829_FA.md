# صف intake شواهد بیرونی برای مسیرهای alias میان‌مسیره — ۲۰۲۶-۰۸-۲۹

این بسته ۲۹ مسیر باز P0 تا P4 را به یک صف اجراییِ **دریافت مدرک** تبدیل می‌کند؛ نه به صف اجرای وارانگار. همهٔ تحلیل‌های packetization قبلی حفظ شده‌اند و هیچ case جدیدی به lower bound طراحی افزوده نشده است.

## نتیجهٔ اصلی

- ۲۹ آیتم صف، پوشش‌دهندهٔ ۲۰۳ case؛
- ۴ گروه تصمیم بیرونی: ۹ تصمیم alias/new-action، ۱۲ تصمیم semantic-equivalence، ۵ تصمیم effect+result parity برای فرمان‌های گزارشی، و ۳ تصمیم export effect+result parity؛
- توزیع caseها به‌ترتیب ۶۳، ۸۴، ۳۵ و ۲۱؛
- ۵۸ انتساب **نوع نقش پاسخ‌گو**، ولی صفر مالک نام‌گذاری‌شده؛
- صفر receipt دریافت‌شده یا پذیرفته‌شده، صفر تصمیم بسته، صفر case اجراشده/تأییدشده، و صفر ارتقای command-ready یا pilot-ready.

## ترتیب و معیار intake

اولویت صف از P0 به P4 است و در هر lane با شناسهٔ packet مرتب می‌شود. دریافت شواهد می‌تواند مستقل انجام شود، اما هیچ مسیر فقط با یک تأیید شفاهی یا شباهت نام فرمان بسته نمی‌شود. بستهٔ هر مسیر باید همهٔ receiptهای قابل‌اعمال، نسخهٔ سیاست، مرجع رفع تعارض و تأیید نقش‌های پاسخ‌گو را داشته باشد.

چهار گروه مسیر به gateهای از قبل تعریف‌شده متصل‌اند:

1. **Alias یا new action:** تصمیم صریح alias/new/reject، شواهد مجوز/رد، مرز transaction یا عدم‌تغییر منبع، و اثر success/failure/retry.
2. **Semantic equivalence:** disposition زوج‌به‌زوج، پیش‌شرط، واژگان outcome، خانوادهٔ effect، failure stage و مرز transaction/immutability.
3. **Report command effect + result parity:** علاوه بر موارد بالا، frozen fixture، برابری value/rowset، outcome هر آیتم و سلامت render/file.
4. **Export effect + result parity:** frozen input/query identity، schema/order/format/encoding، digest فایل، عدم‌تغییر منبع و result parity.

## مرز ایمنی و صداقت ادعا

این artifact فقط قرارداد دریافت و اعتبارسنجی شواهد است. هیچ فرم، گزارش، Stored Procedure، اتصال دیتابیس یا اسمبلی اجرا نشده و هیچ داده‌ای تغییر نکرده است. وجود آیتم در صف به‌معنی equivalence، result parity، پذیرش مالک یا آمادگی استقرار نیست.

Artifact اصلی:

`artifacts/varanegar_analysis/varanegar_alias_cross_lane_external_evidence_intake_queue_20260829.json`

Checkpoint زنجیره‌ای:

`artifacts/varanegar_analysis/varanegar_alias_cross_lane_external_evidence_intake_checkpoint_20260829.json`
