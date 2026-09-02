# قرارداد Evidence intake نهایی Owner-UAT — CG-04

CG-04 آخرین Gate است و تنها پس از پذیرش پنج Gate `CG-06`، `CG-05`، `CG-01`، `CG-02` و `CG-03` قابل اجرا است. مجموع ورودی لازم ۷۰ Slot/Packet بالادست است: هشت تصمیم Platform، بیست سطح گزارش و سه مجموعهٔ چهارده‌ماژولی Authorization/Atomicity/Effect.

برای هر ۱۴ ماژول یک Packet شانزده‌فیلدی تعریف شد: Obligation manifest، پنج مجموعهٔ شاهد بالادست، Run/Receipt، Difference/Exception، Risk disposition، Approvalهای Business/Security/Control و Promotion/Rollback snapshot.

نه بُعد پذیرش شامل کامل‌بودن پیش‌نیازها، پوشش Obligation، Receipt اجرا، صفر اختلاف توضیح‌نداده‌شده، Risk/Exception disposition، سه لایه Approval و مرز Promotion/Rollback است.

Artifact یا Test آفلاین PASS، Golden design یا Hash-pinned evidence به معنی UAT اجراشده نیست. Approval عمومی معتبر نیست و باید Run، Difference، Risk و Snapshot دقیق را ارجاع دهد. Approved exception نیز صفر اختلاف نیست؛ باید محدود، صریح و دارای مالک باشد.

CG-04 فقط با پذیرش پنج Gate، اجرای ۱۲۲۹ Obligation، ۱۴ Packet نهایی، صفر اختلاف توضیح‌نداده‌شده و Approvalهای پاسخ‌گو بسته می‌شود. تنها پس از آن Readiness دوباره بررسی می‌شود.

در Snapshot فعلی هر پنج Gate باز، پذیرش بالادست ۰/۷۰، اجرای Obligation صفر، Owner/Promotion approval صفر و Command/Pilot readiness صفر است. پایهٔ ۸۴ ریسک/۳۴۳ انتساب ثابت است.

هیچ UAT، Command، Report، Procedure، Mutation یا External effect اجرا نشده، هیچ Approval شخصی جمع نشده و هیچ اتصال دیتابیس یا Write access ایجاد نشده است.
