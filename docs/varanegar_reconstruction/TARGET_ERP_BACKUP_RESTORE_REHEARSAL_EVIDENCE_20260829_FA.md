# قرارداد شواهد Backup/Restore Rehearsal برای ERP مقصد

تاریخ: ۲۰۲۶-۰۸-۳۱

## مسئله

ریسک بحرانی `R-019` می‌گوید وجود Backup، Restorable بودن را ثابت نمی‌کند. قرارداد Platform قبلی Command و Golden Case عمومی داشت، اما برای هر چهارده ماژول، Asset، RPO/RTO، Reconciliation و Receipt مستقل Restore را کامل نکرده بود. این بسته فقط قرارداد شواهد را می‌سازد؛ هیچ Backup یا Restore اجرا نشده است.

## پوشش

- چهارده ماژول ERP مقصد؛
- شش Asset class برای هر ماژول، یعنی ۸۴ obligation؛
- دوازده سناریوی Rehearsal برای هر ماژول، یعنی ۱۶۸ assignment؛
- Recovery objective با هجده فیلد و Rehearsal evidence با بیست فیلد؛
- چهارده Gate برای هر ماژول، یعنی ۱۹۶ assignment؛
- پنج Role برای هر ماژول، یعنی ۷۰ assignment؛
- هشت Typed outcome.

Assetها Transactional store، Evidence/Object store، Config/Policy، Audit/Outbox/Inbox/Idempotency، Read model/Search و Referenceهای Key/Secret/External service را پوشش می‌دهند. وجود Asset در این فهرست به معنی انتخاب Stack یا Provider نیست؛ applicability هر مورد به تصمیم مالک نیاز دارد.

## قواعد پذیرش

بالاآمدن سرویس یا Load شدن Schema به معنی Restore success نیست. پذیرش به Manifest معتبر، محیط isolated و disposable، SoD، Version pinning، بازیابی referenceهای حساس بدون ذخیرهٔ material، Reconciliation Outbox/Inbox، Reconciliation بین‌ماژولی، RPO/RTO اندازه‌گیری‌شده، اختلاف صفر و Cleanup/Repeatability نیاز دارد.

## وضعیت فعلی

- RPO و RTO هر چهارده ماژول `UNAPPROVED` است.
- همهٔ ۱۶۸ سناریو `UNEXECUTED`، تعداد ۱۹۶ Gate `UNMET` و تعداد ۷۰ Role `UNASSIGNED` است.
- Stack، Database، Hosting، Storage، Key Provider، Recovery owner و Target انتخاب نشده‌اند.
- Backup set خوانده یا ساخته نشد؛ Restore/Failover/Drill صفر است.
- Recovery ready، Command ready و Pilot ready هر چهارده ماژول صفر است.
- هیچ اتصال، Endpoint، Credential، Key، PII یا مقدار تجاری استفاده نشده و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

