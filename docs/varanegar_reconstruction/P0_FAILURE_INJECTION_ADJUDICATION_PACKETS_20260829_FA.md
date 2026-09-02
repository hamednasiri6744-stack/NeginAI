# Packetهای داوری Failure Injection برای P0 ـ ۲۰۲۶-۰۸-۲۹

۲۰ جفت Failure Injection از شش کاندید P0 در سه Packet عملیاتیِ طراحی گروه‌بندی شد: stock-voucher، reverse bank-reconciliation و delete received-cheque. این Packetها اجرای fault injection نیستند؛ فقط تفاوت stage و تعهدهای اثر ماندگار را برای داوری نقش‌ها صریح می‌کنند.

فقط دو جفت برچسب stage یکسان `fault_after_first_write` دارند و ۱۸ جفت، stage عمومی جدید را در برابر stageهای دقیق baseline می‌گذارند. در ۱۵ جفت baseline retry/convergence و در ۱۵ جفت منع partial effect صریح است؛ هفت جفت به audit/outbox حساس‌اند. بااین‌حال outcome دقیق، assertion دقیق و full exact همگی صفر هستند.

این اختلاف‌ها در stock شامل state-event، ledger projection، accounting request، outbox و posting dependency است؛ در bank-reconciliation شامل state transition، staging cleanup، cardex، audit/outbox و unlink است. ادغام این stageها زیر یک Case عمومی بدون receipt تراکنش، durable write-set، rollback/unknown outcome، retry و external-effect مجاز نیست.

هر سه Packet به دو نقش و دوازده فیلد disposition نیاز دارد. پذیرش جفت‌ها، اجرا، اثر شمارشی و readiness صفر و lower bound طراحی ۱۴۰۴ باقی مانده است.
