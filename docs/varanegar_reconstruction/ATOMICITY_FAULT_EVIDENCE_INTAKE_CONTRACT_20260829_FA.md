# قرارداد Evidence intake برای Fault-injection و Atomicity — CG-02

این قرارداد Runtime atomicity را برای هر ۱۴ ماژول تعریف می‌کند، ولی هیچ Fault injection یا Transaction واقعی اجرا نمی‌کند. دوازده ماژول شاهد Legacy-static یا Target design دارند؛ Identity و Integration فقط Target design دارند و Complete legacy/static proof آنها صفر است.

هر ماژول باید ده مرز خطا را در محیط ایزوله پوشش دهد: پیش از Transaction، میان Mutationهای وابسته، پیش از Audit/Outbox، پس از Commit و پیش از Ack، اثر خارجی پیش از Commit، Commit پیش از اثر خارجی، شکست خود Rollback، Idempotency هم‌زمان، Expected version کهنه و Retry پس از Partial/Unknown outcome.

Packet هفده Field مرجعی/Hash دارد: Command، Transaction owner، Mutation set، Fault plan/point، Before/After digest، Outcome، Commit/Rollback، Unknown readback، Retry، Quarantine/Compensation، External effect، Difference و Approvalهای Technical/Business owner.

فراخوانی Rollback، Catch شدن Exception یا Boolean return اثبات موفقیت Rollback نیست. Commit بدون Ack برابر `UNKNOWN_OUTCOME` است تا Readback immutable انجام شود. Database و سیستم خارجی Atomic commit مشترک ندارند مگر مستقل اثبات شود. شکست Rollback باید Automation را متوقف و Escalate کند.

اجرای CG-02 به پذیرش ۸/۸ CG-06 وابسته است و بعد از آن می‌تواند موازی با CG-01 اجرا شود؛ نتیجهٔ یکی از دیگری استنتاج نمی‌شود. CG-02 فقط با ۱۴ Packet پذیرفته، هر ده دسته، Approval و صفر Partial effect توضیح‌نداده‌شده بسته می‌شود.

Snapshot فعلی Runtime atomicity، Packet پذیرفته، Owner approval، Command readiness و Pilot readiness همگی صفر است. ۱۲۲۹ obligation طراحی‌اند و پایهٔ ۸۴ ریسک/۳۴۳ انتساب ثابت است.

هیچ Database connection، Fault injection، Commit، Rollback، Retry، Procedure یا External effect اجرا نشده و هیچ Write access ایجاد نشده است.
