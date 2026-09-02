# Reference Evaluator مصنوعی Approval Governance

این evaluator فقط Boolean/Action مصنوعی را پردازش می‌کند و هیچ workflow/user/role/request/decision/token/effect عملیاتی را باز یا اجرا نمی‌کند.

ترتیب تصمیم Schema، Request/Policy/Threshold، Qualification/SoD/Conflict، Delegation scope/acceptance/expiry/revocation، منع auto-decision، Blocking unknown، Escalation، Break-glass، Execution token/effect، Quorum/Sequence و Acceptance است.

شش مسیر مثبت Approve/Reject/Delegate/Escalate/Break-glass/Execute و بیست‌وسه mutation منفی تعریف شده‌اند. Delegation منقضی/revoked، timeout auto-decision، break-glass بدون incident/review و token غیر single-use/fenced fail-closed هستند.

Operational implementation/read/run/receipt و Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
