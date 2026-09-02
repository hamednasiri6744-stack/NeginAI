# قرارداد Optimistic Concurrency، Version و Fencing مقصد

ده بُعد concurrency برای ۴۹ فرمان ۴۹۰ assignment و شش Strategy candidate تعداد ۲۹۴ assignment دارد. هیچ Strategy خودکار انتخاب نشده است. Concurrency receipt بیست‌ودو، Conflict receipt هجده و Lease/Fencing receipt بیست فیلد دارد.

چهارده Failure case تعداد ۶۸۶، هجده Gate تعداد ۸۸۲ و شش Role تعداد ۲۹۴ assignment دارد. Idempotency کنترل concurrency نیست؛ authoritative update باید expected-version و repository-level CAS داشته باشد و match count غیر از یک، typed conflict است.

Lost-update، silent last-write-wins، write-skew/phantom، sequence تکراری، lease منقضی و fencing token کهنه ممنوع است. Deadlock retry هویت command را عوض نمی‌کند و unknown commit پیش از reconciliation دوباره اجرا نمی‌شود.

هیچ Version/Transaction/Lock/Lease/Fencing token عملیاتی خوانده و هیچ Command/Conflict/Retry اجرا نشد. Strategy/Runtime proof/Test/Approval/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
