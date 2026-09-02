# قرارداد Capacity، Timeout، Backpressure و Degradation مقصد

دوازده بُعد Capacity برای چهارده ماژول ۱۶۸ assignment و دوازده مرحلهٔ lifecycle نیز ۱۶۸ assignment دارد. Capacity policy بیست‌ودو، Timeout/Retry budget بیست، Overload receipt بیست‌ودو و Degradation receipt بیست فیلد دارد.

شانزده Failure case تعداد ۲۲۴، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ assignment دارد. Inflight/Queue/Batch/Payload/Pool بی‌کران، child timeout بزرگ‌تر از parent و retry بدون idempotency/budget/jitter ممنوع است.

Queue overflow نباید Effect را خاموش حذف یا reorder کند. Degraded mode حق bypassکردن Authorization یا invariant مالی/انبار/پرداخت ندارد و Recovery پیش از drain/replay/reconciliation مجاز نیست.

هیچ Traffic/Metric/Queue/Resource/Dependency عملیاتی خوانده و هیچ Load/Fault/Overload/Degradation اجرا نشد. Policy/Rehearsal/Recovery/Approval/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
