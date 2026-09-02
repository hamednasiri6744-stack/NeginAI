# قرارداد اصالت پیام، Replay و Dead-letter در Integration/Webhook مقصد

این بسته فقط طراحی شواهد است. هیچ endpoint، certificate، key، token، message، payload یا dead-letter عملیاتی خوانده نشد و هیچ send/receive/ack/retry/quarantine/redrive اجرا نشد.

## قواعد قطعی

- Signature باید canonical method/path/content-type/payload digest/timestamp/nonce/audience را bind کند؛ key ناشناخته، منقضی یا revoked fail-closed است.
- Scope شامل tenant، organization، environment، audience و direction است. Message ID با fingerprint متفاوت قابل reuse نیست و Unknown delivery پیش از retry باید reconcile شود.
- Retry به idempotency، attempt/elapsed budget، backoff و jitter نیاز دارد. Poison message نه silently drop می‌شود و نه بی‌نهایت retry؛ در quarantine و dead-letter رمزگذاری‌شده قرار می‌گیرد.
- Redrive به reason، scope، authorization مستقل، idempotency key، سقف دفعات و loop guard نیاز دارد و اثر پس از اجرا reconcile می‌شود.

## پوشش و وضعیت

چهارده بُعد در چهارده ماژول ۱۹۶ assignment و دوازده stage تعداد ۱۶۸ assignment دارد. Endpoint policy و Inbound receipt به‌ترتیب ۲۴/۲۴ و Outbound/Dead-letter receipt هرکدام ۲۲ فیلد دارند. هجده failure تعداد ۲۵۲، بیست‌وچهار gate تعداد ۳۳۶ و هفت role تعداد ۹۸ assignment ایجاد کرد. Runtime، provider، receipt و readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
