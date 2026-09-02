# قرارداد Idempotency و همگرایی Outbox/Inbox فرمان‌های ERP مقصد

## هدف

این بسته ۴۹ فرمان تعریف‌شده در Blueprint چهارده ماژول را به قرارداد یکنواخت جلوگیری از اثر تکراری، Commit نامعلوم، Outbox دوگانه و مصرف تکراری پیام متصل می‌کند. این سند صرفاً طراحی provider-neutral است؛ هیچ Command، Message، Retry، Replay، Queue، Database یا Fault Injection اجرا نشده و هیچ Provider انتخاب نشده است.

## پوشش

- Envelope فرمان ۲۲ فیلد، Receipt idempotency بیست فیلد، رکورد Outbox شانزده فیلد و Inbox چهارده فیلد دارد؛ شواهد فقط hash/reference/count/status نگه می‌دارند.
- چهارده نقطهٔ شکست برای هر ۴۹ فرمان، یعنی ۶۸۶ انتساب، از رزرو کلید تا Commit نامعلوم، گم‌شدن پاسخ، انتشار و مصرف تکراری و Replay بازیابی تعریف شده است.
- هشت بُعد همگرایی برای هر فرمان، یعنی ۳۹۲ انتساب، یکتایی Receipt/Effect/Event/Inbox و همگرایی Watermark/Unknown outcome را می‌سنجد.
- شانزده Gate برای هر فرمان، یعنی ۷۸۴ انتساب، و پنج Role برای هر فرمان، یعنی ۲۴۵ انتساب، تعریف شده است.
- ده Outcome میان Commit نخست، Replay برابر، تعارض payload، rollback، Commit نامعلوم، publication pending، duplicate consumer و quarantine تفکیک می‌کند.

## قواعد fail-closed

- همان Key و همان Fingerprint باید Receipt نخست را برگرداند؛ همان Key با Fingerprint متفاوت Conflict است.
- Attempt/Retry اجازهٔ تغییر Key ندارد.
- Effect تجاری، Receipt و Outbox باید یک Transaction owner داشته باشند؛ Commit نامعلوم اجازهٔ Retry کور نمی‌دهد.
- Consumer تکراری نباید Effect تازه بسازد و Inbox/Effect باید اتمیک یا به‌شکل پایدار قابل‌بازیابی باشد.
- Replay پس از Restore تا تطبیق Idempotency/Watermark ممنوع است.
- وجود Code/Schema اثبات Runtime convergence یا Readiness نیست.

## وضعیت فعلی

هر ۴۹ قرارداد `DESIGNED_NOT_IMPLEMENTED`، تمام ۶۸۶ سناریوی شکست `UNEXECUTED`، همهٔ ۳۹۲ بُعد همگرایی `UNPROVEN`، تمام ۷۸۴ Gate `UNMET` و ۲۴۵ Role `UNASSIGNED` است. Implementation، Fault run، Replay proof، Outbox atomicity، Inbox convergence، Unknown reconciliation، Owner approval، Command readiness و Pilot readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
