# نقشهٔ اولویت Gateهای شواهد خارجی و Runtime

این بسته شش Gate باز ممیزی تجمیعی را بر اساس وابستگی شواهدی مرتب می‌کند؛ هیچ Gate را اجرا یا بسته اعلام نمی‌کند.

1. `CG-06` ریشهٔ تصمیم است: Stack/Database/Hosting، RPO/RTO، محیط ایزوله و نقش مالک استقرار باید تصویب و hash-pin شوند. Proposal برابر Approval نیست.
2. `CG-05` مسیر محدود و موازی گزارش است: مالکیت ۲۰/۲۰ بسته شده، اما Result/Formula parity و Owner Golden Value هنوز صفر است. Fixture، فرمول، grain، scope، rounding/null و receipt مقایسه باید برای owner واقعی نتیجه تعریف شوند؛ shell مالک Query فرض نمی‌شود.
3. `CG-01` شاهد authenticated deny-first و resource-scope را در هر ۱۴ ماژول می‌خواهد.
4. `CG-02` fault injection، rollback، partial-failure و unknown-outcome را در محیط ایزوله می‌خواهد.
5. `CG-03` بعد از مرز atomicity، Mutation/Result/External-effect/readback و retry/compensation را reconcile می‌کند.
6. `CG-04` Gate نهایی است: ۱۲۲۹ obligation طراحی فقط پس از پذیرش Gateهای جزء اجرا و به مالک پاسخ‌گو ارائه می‌شوند.

برای هر Gate چهار جزء Evidence packet و یک Acceptance rule تعریف شده است. تا پیش از پذیرش کامل، اثر ارتقای Readiness برابر `NONE` است. Runtime authorization/atomicity/effect parity، Report parity، Owner approval، Command readiness و Pilot readiness همگی صفر می‌مانند. پایهٔ ۸۴ ریسک و ۳۴۳ انتساب تغییر نکرده است.

هیچ فرم، گزارش، Procedure، Assignment، Migration، Deployment یا اثر خارجی اجرا نشده؛ هیچ اتصال دیتابیس یا دسترسی نوشتن ایجاد نشده و هیچ هویت، Credential یا مقدار خام تجاری در Artifact ذخیره نشده است.
