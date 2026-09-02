# داوری Failure Injection برای P4 ـ ۲۰۲۶-۰۸-۲۹

شش جفت Failure Injection فقط برای دو Export-file Production و Stock تشکیل شد؛ Candidate بانکی Read هیچ جفت خطای Export ندارد. شش Case جدید Render/Completion/Partial در برابر دو Case پایهٔ post-file-creation قرار گرفت و stage دقیق صفر است.

هر شش جفت پایه retry/recovery، partial-file quarantine، source immutability و file/artifact sensitivity را صریح دارد. این قراردادها با سه stage جدید یکسان نیستند و نبود failure pair بانکی نیز شکاف شاهد است، نه اثبات رفتار.

Outcome/assertion/full exact، Result parity و acceptance صفر است. هیچ Export اجرا نشده؛ lower bound طراحی ۱۴۰۴، Risk/Trace برابر ۸۴/۳۴۳ و readiness صفر باقی می‌ماند.
