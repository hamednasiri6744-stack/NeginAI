# Shortlist شواهد Baseline برای P3 ـ ۲۰۲۶-۰۸-۲۹

پنج Packet/۳۵ Case فرمان گزارش در baseline بازسازی‌شده بررسی شد و هر پنج Packet دست‌کم یک candidate family دارد. شش Action reference شامل ۳۱ Case پایه و ۲۶ kind-overlap است: دو سطح statement برای import/command بانکی، سه completion command چاپ و یک export-file برای healthy cardex.

برای مقایسه، `happy_path` و `export` به Success، `fault_injection` و `partial_failure` به Failure Injection و `versioning` به Concurrency نرمال شده‌اند. این normalization فقط هم‌ترازی تحلیلی است؛ Print، Export، Completion و Statement mutation همچنان اثرهای متمایزند.

هیچ Action string دقیق، semantic equivalence، result parity، acceptance یا اجرا از shortlist استنتاج نشده است. lower bound طراحی ۱۴۰۴، Risk/Trace برابر ۸۴/۳۴۳ و readiness صفر باقی می‌ماند.
