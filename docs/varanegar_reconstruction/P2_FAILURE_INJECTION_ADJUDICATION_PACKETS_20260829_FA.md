# Packetهای داوری Failure Injection در P2 ـ ۲۰۲۶-۰۸-۲۹

پانزده جفت Failure Injection در پنج Packet و شش Candidate comparison تفکیک شد. پنج Case جدید در برابر یازده Case پایه قرار دارد؛ دو stage label برابر و سیزده stage متفاوت یا schema-normalized است.

از متن assertionهای baseline، ده جفت retry/convergence، ده جفت no-partial-effect و سیزده جفت حساس به audit/outbox استخراج شد. این شواهد شامل version/aggregate stage، commit-before-response، publish/replication و مسیرهای change-status/undo است و اجرای Runtime نیست.

Outcome/assertion/full exact و acceptance صفر است. lower bound طراحی ۱۴۰۴، پایهٔ ۸۴/۳۴۳ و readiness صفر باقی می‌ماند.
