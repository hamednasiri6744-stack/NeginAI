# دفتر Truth Table و Readiness فرمان‌های ۱۴ ماژول

این Ledger شواهد فرمان موجود را برای ۱۴ ماژول بدون اجرای فرمان تجمیع می‌کند. ۱۳
Artifact معتبر فرمان/قرارداد به ماژول‌ها نگاشت شده‌اند. ده command orchestrator،
۱۱ trace ایستای قدیمی و ۷۷ Golden Case مصنوعی ثبت شده‌اند.

دو Artifact قدیمی side-effect و Golden case فیلد `validation` ندارند؛ فقط شکل و
شمارش هش‌پین‌شدهٔ آنها استفاده شده و readiness gate نیستند. Golden case مصنوعی،
owner-approved یا executed تلقی نمی‌شود.

Truth Table مشترک هفت مرحله دارد: authorize، validate، begin unit of work، mutate،
audit/outbox، commit و retry. برای هر ماژول پنج ضلع authorization، transaction owner،
mutation set، outcome/retry/idempotency و Golden cases جدا ثبت شده است.

وضعیت صادقانه:

- owner-approved Golden Case: صفر؛
- executed Golden Case: صفر؛
- runtime authorization/atomicity/effect/retry parity: صفر ماژول؛
- command-ready و pilot-ready: صفر ماژول؛
- Risk count: ۸۴.

مرحله بعد باید UAT ایزوله و احراز‌شده، failure injection، rollback/partial-success،
idempotency و owner sign-off را برای هر command family اثبات کند. هیچ فرمان، Form،
Procedure یا Assembly در ساخت این Ledger اجرا نشده است.
