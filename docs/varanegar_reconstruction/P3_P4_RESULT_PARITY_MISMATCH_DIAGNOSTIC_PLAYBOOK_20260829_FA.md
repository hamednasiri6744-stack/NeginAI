# Playbook تشخیصی Mismatch برای Result parity در P3/P4 — ۲۰۲۶-۰۸-۲۹

ده Playbook hash-only برای تشخیص اختلاف‌های Fixture/Version، Key-set/Inclusion، Grain/Cardinality، Formula/Rounding/Currency، Ordering/Pagination، Render، Export schema/encoding، File digest/immutability، Per-item outcome و Conflict/Exception ساخته شد.

هر Playbook ده مرحله دارد و در اولین manifest/hash/version/scope/redaction/conflict یا اختلاف توضیح‌نداده‌شده متوقف می‌شود. Repair، Replay، Recapture یا Promotion خودکار ممنوع است. خروجی تشخیصی فقط یکی از چهار وضعیت زیر است:

- Match با شواهد hash-only پذیرفته‌شده؛
- Exception نسخه‌دار و owner-approved؛
- Evidence نامعتبر/منقضی و نیازمند recollection مجاز؛
- اختلاف توضیح‌نداده‌شده که CG-05 را باز نگه می‌دارد.

ده Playbook روی هشت قرارداد و ۵۶ Golden/UAT Case، ۷۲ Packet assignment، ۵۰۴ Case cross-link، ۱۰۰ step assignment و ۳۴ پیوند بُعد parity دارد. Render فقط پنج Packet P3 و Export schema فقط سه Packet P4 را پوشش می‌دهد.

وضعیت فعلی همهٔ Playbookها `DESIGNED_NOT_RUN_NO_CAPTURE_AUTHORIZATION` است. Diagnostic run، Match، Exception، Repair/Replay، Owner resolution، Result parity و readiness همگی صفر است.

Artifact:

`artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_playbook_20260829.json`

Checkpoint:

`artifacts/varanegar_analysis/varanegar_p3_p4_result_parity_mismatch_diagnostic_checkpoint_20260829.json`
