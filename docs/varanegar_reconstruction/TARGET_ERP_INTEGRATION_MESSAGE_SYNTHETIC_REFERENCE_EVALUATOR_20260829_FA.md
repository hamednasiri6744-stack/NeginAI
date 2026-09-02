# Reference Evaluator مصنوعی پیام Integration

این evaluator فقط Boolean/State/Identifier مصنوعی و ثابت را پردازش می‌کند و هیچ network، endpoint، key، message، payload، broker، quarantine یا dead-letter عملیاتی را باز نمی‌کند.

ترتیب تصمیم Schema، Transport، Signature/Key، Canonical digest، Schema compatibility، Scope، Timestamp/Nonce/Replay، Message ID/Dedup، Ordering، Blocking unknown، Payload policy، Delivery state، Retry/Unknown، Poison/Dead-letter، Redrive و Acceptance است.

هشت مسیر مثبت Inbound، Replay، Ack، Unknown delivery، Retry، Poison quarantine، Dead-letter و Redrive و بیست‌ویک mutation منفی تعریف شده‌اند. Unknown delivery خروجی typed reconciliation می‌دهد؛ retry بدون idempotency/budget، poison بدون quarantine، dead-letter بدون encryption و redrive بدون authorization/cap/loop guard رد می‌شود.

این یک reference implementation است، نه transport/broker/signature verifier. Operational implementation/read/run/receipt و Command/Pilot readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
