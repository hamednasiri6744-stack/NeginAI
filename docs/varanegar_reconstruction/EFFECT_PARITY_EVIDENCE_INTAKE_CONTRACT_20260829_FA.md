# قرارداد Evidence intake برای Mutation/Result/External-effect parity — CG-03

این قرارداد ده لایهٔ اثر را برای هر ۱۴ ماژول جدا می‌کند: Mutation اصلی DB، Audit، Outbox/Job، اثر خارجی، Result/Outcome، Readback، Retry/Duplicate، Compensation/Reversal، Crosswalk/Provenance و Reconciliation/Quarantine.

دوازده ماژول شاهد Mutation Legacy-static یا Target دارند؛ Identity و Integration فقط Target mutation/effect design دارند و Complete legacy/static proof آنها صفر است. Runtime effect parity در ۰/۱۴ است.

Packet نوزده Field مرجعی/Hash دارد: Command، Mutation/Result/External contracts، Fixture، Before/DB-after، Result، Audit، Outbox، External/quarantine، Readback، Retry، Compensation، Crosswalk، Difference و Approvalهای Technical/Business owner.

Commit، Audit یا Outbox به‌تنهایی External effect را ثابت نمی‌کند. Success result بدون Readback immutable Mutation set را ثابت نمی‌کند. Retry باید outcome قبلی را پیش از اثر تازه reconcile کند. Compensation فرمان append-only است و History/Provenance اصلی را پاک نمی‌کند. اثر بدون تطبیق قرنطینه می‌شود و به‌صورت حدسی normalize یا attribute نمی‌شود.

اجرای CG-03 به پذیرش CG-06 و CG-02 وابسته است. CG-03 تنها با ۱۴ Packet پذیرفته، هر ده لایه، Approval مالک و صفر اختلاف توضیح‌نداده‌شده بسته می‌شود.

Snapshot فعلی CG-06 و CG-02 بازند؛ Runtime effect parity، Packet پذیرفته، Approval، Command readiness و Pilot readiness صفر و پایهٔ ۸۴ ریسک/۳۴۳ انتساب ثابت است.

هیچ Database connection، Command، Mutation، Retry، Compensation، Message، File یا External call اجرا نشده و هیچ Write access ایجاد نشده است.
