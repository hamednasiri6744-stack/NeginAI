# قرارداد Evidence intake برای Result/Formula parity گزارش‌ها — CG-05

این قرارداد ۲۰ سطح گزارش را بر اساس مالک واقعی نتیجه تفکیک می‌کند؛ وجود یک Form، Viewer، Shell، Selector یا Command orchestrator به معنی مالکیت Query یا Formula نیست.

- ۱۱ سطح، مالک نتیجهٔ مستقل دارند و `RESULT_PARITY_PACKET` می‌خواهند.
- دو سطح Command هستند ولی مالک نتیجهٔ Query مستقل نیستند و `COMMAND_OUTCOME_PACKET` می‌خواهند.
- هفت سطح Viewer/Shell/Selector/Route هستند و `ROUTING_VIEW_PACKET` می‌خواهند.
- از هشت سطح Command، شش سطح هم مالک نتیجه‌اند؛ برای این شش، Receipt فرمان جای Formula/Result parity را نمی‌گیرد.

Packet نتیجه ۱۴ Field مرجعی/Hash دارد: مالک نتیجه، Fixture، digest خروجی Legacy/Target، مجموعه کلید، Formula، Grain، Scope، Rounding، Null، Watermark، Difference manifest و Owner approval. مقدار خام تجاری، هویت، Credential یا Endpoint در Artifact ذخیره نمی‌شود.

قبولی Result parity نیازمند ورودی ایزوله و Frozen، Policy تصویب‌شدهٔ Formula/Grain/Scope/Rounding/Null، برابری کلید/Aggregate/Output و صفر اختلاف توضیح‌نداده‌شده است. اختلاف معنایی تصویب‌شده باید صریحاً در Manifest immutable ثبت شود و نباید بی‌صدا normalize شود.

Command packet فقط Authorization، Outcome، Retry و Partial failure را می‌بندد. Routing/View packet فقط Route، Permission، Lifecycle، Failure isolation و Downstream owner را می‌بندد. هیچ‌کدام به‌تنهایی Result parity نیستند.

CG-05 از نظر منطقی می‌تواند موازی با پذیرش CG-06 آماده شود، ولی بدون محیط Runtime ادعایی ندارد. در Snapshot فعلی مالکیت ۲۰/۲۰ بسته است؛ ۸۸ Golden fixture و ۵۶ Case فرمان طراحی شده‌اند، اما اجرا، Packet پذیرفته‌شده، Result parity، Owner Golden/Approval، Command readiness و Pilot readiness همگی صفرند. پایهٔ ۸۴ ریسک/۳۴۳ انتساب ثابت است.

هیچ گزارش، Query، Export، Print یا Command اجرا نشده و هیچ اتصال دیتابیس یا دسترسی نوشتن ایجاد نشده است.
