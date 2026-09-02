# Reference Evaluator مصنوعی Concurrency مقصد

Evaluator خالص و بدون I/O برای ترتیب تصمیم Idempotent replay، Unknown commit، Deadlock retry، Expected-version، CAS cardinality، Business invariant، Sequence، Lease، Fencing و Bulk policy ساخته شد.

سه مسیر مثبت Commit/Replay/Retry و سیزده Mutation منفی، جمعاً ۱۶/۱۶، PASS است. Receipt موجود پیش از version بررسی می‌شود و Unknown commit همیشه پیش از retry به Reconciliation می‌رود.

Version mismatch از CAS cardinality، sequence غیرmonotonic، lease نامعتبر و fencing token کهنه Outcome جدا دارد. Deadlock retry فقط با همان Command identity پذیرفته می‌شود.

فقط version/count/boolean/sequence/fence مصنوعی پردازش شد. هیچ Transaction/Lock/Lease/Command عملیاتی خوانده یا اجرا نشد؛ Reference implementation یک و Operational implementation/Receipt/Readiness صفر است.
