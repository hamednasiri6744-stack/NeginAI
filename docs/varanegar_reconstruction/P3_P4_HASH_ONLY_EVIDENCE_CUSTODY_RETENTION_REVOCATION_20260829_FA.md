# قرارداد Custody، Retention، Expiry، Revocation و Supersession شواهد P3/P4

تاریخ: ۲۰۲۶-۰۸-۳۱

## هدف

ماتریس Handoff به Custody Receipt جاری و منقضی‌نشده نیاز داشت، اما قرارداد ۲۹۰ Receipt فقط metadata پایهٔ expiry/supersession را تعریف کرده بود. این بسته زنجیرهٔ custody را برای ۵۴ اتصال Channel-to-Receipt زیر CG-05 کامل می‌کند.

## پوشش

- هشت Capture Pair، شانزده Channel و ۲۷ Receipt slot؛
- ۵۴ Custody requirement یکتا؛
- Schema بیست‌فیلدی؛
- نه State و دوازده Transition؛
- ده Gate برای هر requirement، یعنی ۵۴۰ assignment؛
- چهار Role برای هر requirement، یعنی ۲۱۶ assignment؛
- هشت Rule مربوط به retention و دوازده Rejection code.

Stateها از `MISSING` شروع می‌شوند و مسیر عادی به Created، Transfer Pending، In Custody، Review Pending و Accepted Current می‌رود. Expired، Revoked و Superseded terminal برای استفاده در Handoff معتبر نیستند. هیچ Transition خودکاری مجاز نیست و هر تغییر به Receipt و شاهد نقش نیاز دارد.

## Retention و Disposition

Retention نسخه‌دار و محدود است؛ expiry خودکار تمدید نمی‌شود؛ revocation Gate وابسته را دوباره باز می‌کند؛ supersession به لینک hash دوطرفه نیاز دارد؛ مواد خام موقت پیش از پذیرش Custody باید نابود شوند؛ Hold حقوقی یا Incident به Receipt جداگانه نیاز دارد؛ disposition فقط tombstone مبتنی بر hash و lineage را حفظ می‌کند.

## وضعیت فعلی

- هر ۵۴ requirement در `MISSING` است.
- هر ۵۴۰ Gate assignment در `UNMET` و هر ۲۱۶ Role assignment در `UNASSIGNED` است.
- Custody receipt ساخته/منتقل/پذیرفته/منقضی/revoke/supersede نشده است.
- هیچ شاهد خارجی، Payload، فایل، مقدار تجاری، PII، Credential، Endpoint، Key یا Signature ذخیره نشده است.
- Handoff، Comparison، Result parity، CG-05 closure و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.

