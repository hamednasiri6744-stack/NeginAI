# قرارداد Snapshot/Delta/Reconciliation برای Cutover ERP مقصد

این بسته چهارده ماژول را در دوازده فاز Cutover از Scope/Authorization تا Snapshot، Delta، Reconciliation، Rollback و Write enablement پوشش می‌دهد. ۱۶۸ انتساب فاز و ۱۶۸ انتساب دوازده بُعد تطبیق داریم.

Snapshot manifest دارای ۲۲ فیلد، Delta receipt دارای ۲۰ فیلد و Cutover decision دارای ۱۸ فیلد است. هجده Gate برای هر ماژول ۲۵۲ انتساب و شش Role برای هر ماژول ۸۴ انتساب می‌سازد.

Clone کهنه هرگز Live نیست؛ Snapshot بدون Watermark مجاز current نیست؛ Delta دارای gap/overlap/order conflict اعمال نمی‌شود؛ Replay برابر اثر تازه نمی‌سازد؛ `blocking_unknown` به‌خاطر زمان‌بندی waive نمی‌شود؛ Operator self-approval ندارد و Target writes پیش از Source fence و Receipt نهایی فعال نمی‌شود.

هیچ Snapshot/Delta خوانده، Capture یا Import نشده و هیچ Reconciliation/Fence/Cutover اجرا نشده است. تمام اجرا، پذیرش، Owner approval، Write enablement و Readiness صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
