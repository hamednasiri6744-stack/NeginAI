# قرارداد مجوز Capture ایزوله و Redaction برای P3/P4

تاریخ: ۲۰۲۶-۰۸-۳۱

## هدف

قرارداد Frozen Fixture و Promotion Guard الزام کرده بودند که Capture دو سمت Legacy و Target فقط با مجوز جداگانه و محیط ایزوله انجام شود. این بسته schema و Gate آن مجوز را تعریف می‌کند؛ هیچ مجوزی صادر یا فعال نشده و هیچ Capture واقعی انجام نشده است.

## دامنه

- هشت Packet و ۵۶ Golden Case؛
- دو سمت مستقل `LEGACY_REFERENCE` و `TARGET_CANDIDATE`؛
- شانزده Capture Channel؛
- Schema درخواست مجوز با ۲۴ فیلد؛
- Schema گواهی Redaction با ۱۸ فیلد؛
- چهارده Gate برای هر Channel، یعنی ۲۲۴ انتساب؛
- شش Role برای هر Channel، یعنی ۹۶ انتساب، همراه پنج قاعدهٔ Segregation of Duties.

هر Packet دقیقاً دو Channel و دو Authorization token جدا می‌خواهد. تأیید یک سمت به سمت دیگر سرایت نمی‌کند. Scope، Case set، Dimension set، Command allowlist، محیط، Policy، بازهٔ زمانی، تعداد Attempt و TTL همگی باید hash یا reference نسخه‌دار داشته باشند.

## Gateهای اصلی

Gateها محیط ایزوله، Read-only بودن منبع Legacy، non-production بودن Target، منع egress، allowlist فرمان Capture، توکن جدا برای دو سمت، بازه و TTL محدود، SoD، Policyهای pin‌شده، scan fail-closed، persistence فقط hash/count/status/reference، نابودی مواد موقت و برنامهٔ abort/revoke/incident را الزام می‌کنند. بازبودن هر Gate نتیجه را `DENY_CAPTURE` نگه می‌دارد.

## Redaction و Persistence

فقط reference مبهم، SHA-256، count محدود، status/error، hash نسخهٔ Policy، Receipt reference، زمان/انقضا و manifest/disposition مبتنی بر hash قابل ماندگاری است. مقدار تجاری، Row/Item، هویت و PII، Credential/Connection String، SQL/Rule/Procedure، فایل گزارش یا Export، Endpoint، Session token، Key/Signature، Sample خام، Screenshot و Backup/Log ممنوع‌اند.

## وضعیت فعلی و محدودیت

- همهٔ شانزده Channel در `NOT_REQUESTED` هستند.
- همهٔ ۲۲۴ Gate assignment در `UNMET` و همهٔ ۹۶ Role assignment در `UNASSIGNED` هستند.
- Request، Approval، Activation، Capture attempt، Captured side، Redaction attestation و Receipt acceptance همگی صفر است.
- موفقیت Capture در آینده نیز Result parity نیست و باید وارد Adapter، Diagnostic و Adjudication مستقل شود.
- Owner approval، CG-05 closure، UAT، Command readiness و Pilot readiness صفر است.
- هیچ اتصال، فرم، گزارش، Query، Procedure، Assembly، Mutation یا دادهٔ حساس در ساخت این بسته استفاده نشد.
- پایهٔ ۸۴ ریسک، ۳۴۳ انتساب و lower bound طراحی ۱۴۰۴ ثابت ماند.

