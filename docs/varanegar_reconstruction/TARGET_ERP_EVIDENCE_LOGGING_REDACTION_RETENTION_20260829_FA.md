# قرارداد Redaction و Retention برای Evidence/Logging در ERP مقصد

این بسته ده کانال Evidence را برای ۴۹ فرمان به allowlist سخت‌گیرانه متصل می‌کند. چهارده کلاس Credential/Token/PII/Identifier/Commercial/Payment/Payload/SQL/File/Endpoint/Key/Stack/Backup صریحاً `DENY_PERSIST` و فقط هشت کلاس hash/reference/count/status/version/time/role-type/boolean مجاز است.

- ۱۴۰ سیاست Channel-to-Prohibited-Class و ۴۹۰ انتساب Command-to-Channel داریم.
- Attestation بیست فیلد و Retention record شانزده فیلد دارد.
- چهارده بردار منفی برای هر کانال ۱۴۰ انتساب، شانزده Gate تعداد ۱۶۰ و پنج Role تعداد ۵۰ انتساب می‌سازد.
- Unknown field، nested payload، stack خام، metric label حساس، hash بدون domain separation و تمدید خودکار expiry همگی fail-closed هستند.
- Disposition فقط hash-only tombstone و lineage را نگه می‌دارد؛ revoked/superseded evidence قابل‌قبول نیست.

هیچ Log، Trace، Backup، Message، Export، فایل یا نمونهٔ Runtime خوانده نشده است. Implementation، Sample scan، Attestation، Retention approval، Disposition proof، Incident closure و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
