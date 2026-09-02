# مرز Template خارجی گزارش برگشت فروش — ۲۰۲۶-۰۸-۲۹

## اصلاح طبقه‌بندی

`RPT-11` قبلاً L3 با یک terminal execution signal و ۲۴ SQL candidate بود. شواهد
Hash-pinned فرم نشان می‌دهد این Candidateها Query دادهٔ گزارش را ثابت نمی‌کنند.
فرم فایل پیکربندی‌شده را از `ReportFileEntity.FileName` می‌گیرد، وجود فایل را
کنترل و `Application.ReportEngine.frmPreviewPrint.ShowReportFact` را اجرا می‌کند.
پس Query، Subreport و Formula در Template خارجی مالکیت می‌شوند.

چهار قرارداد متدی و ۱۱ Call لازم تأیید شد: `GetReportPathName`، `PrintCommand`،
`PrintDrfact` و `PrintDrfactColl`. مسیرها AccYear/DC، SaleOffice، بازه شماره، نوع
گزارش و Preview را حمل می‌کنند و `PrintedCompleted` را مشاهده می‌کنند؛ ترتیب دقیق
Audit بعد از چاپ از مجموعه Callها به‌تنهایی اثبات نمی‌شود.

## نتیجه کارشناسی

- ۲۴ Candidate قبلی به‌عنوان Binding دادهٔ گزارش **رد شدند**؛ ممکن است Objectهای
  واقعی دیگری باشند، اما به Template برگشت وصل نشده‌اند.
- Exact template، embedded query، Formula، cancel/delete policy و Result parity
  **اثبات‌نشده** باقی ماندند.
- مقصد باید Template hash/version، Data source و Formula را استخراج و Owner-approved
  کند؛ Preview را Read-only و ثبت چاپ فیزیکی را Command جدا نگه دارد.
- اختلاف گزارش برگشت ابتدا با Hash فایل، DC/سال/دفتر فروش/بازه، Subreport و Formula
  بررسی می‌شود؛ سپس net/gross برگشت و اتصال به فروش منبع در Watermark یکسان.

ریسک تازه ساخته نشد و `R-002/R-013/R-017/R-023/R-031/R-084` reuse شدند. هیچ فایل
Template خوانده یا اجرا نشد، هیچ نام پیکربندی یا مقدار حساس Persist نشد و Assembly
فقط از Artifact IL ایستا مصرف شد.
