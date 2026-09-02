# Addendum تشخیصی مشترک Identity، POS و Report parity

این Addendum جایگزین ۲۰ Playbook عملیاتی Identity/Integration/Reporting نیست. هشت سناریوی تازه صرفاً برای تشخیص مرز شواهد ایجاد شده‌اند و هیچ Endpoint، Query، Template، Procedure، Form یا Commandی اجرا نمی‌کنند.

## هشت سناریو

1. تغییر شمارش Declaration/Verb/Signal در Authorization metadata؛ تغییر عدد ابتدا Drift تلقی می‌شود، نه Fix یا Incident.
2. تغییر یا تعمیم نادرست ۵۸ Membership-user scope mismatch؛ Orphan و Key collision جدا می‌مانند.
3. اشتباه گرفتن صف opaque با Frontier قابل مشاهده در POS graph؛ ۱۶۰ با ۱۵۱ یکی نیست.
4. استنتاج Transaction owner از ۱۱ SCC و ۶۸ گرهٔ چرخه‌ای؛ Write targetهای ۴۸گانه lower bound هستند.
5. برابری Total همراه اختلاف Stable key set یا Grain در گزارش.
6. استنتاج Formula/Grain Template از Route، Filename یا Render success در `RPT-11/12`.
7. نرمال‌سازی بدون Policy اختلاف Null، Sign، Rounding، Currency، Business date یا Status.
8. مصرف Packet جزئی، Stale، Proposed یا Superseded در Handoff یک Gate پایین‌دست.

هر Playbook حداقل ده Step، Evidence request، Role escalation و چهار Stop condition دارد. نتیجه فقط یکی از `EXPECTED_BOUNDARY`، `STATIC_EVIDENCE_GAP`، `DATA_OR_CONFIGURATION_DEBT`، `CONTRACT_OR_IMPLEMENTATION_DEFECT` یا `UNPROVEN` است.

Snapshot فعلی: هشت Playbook، Duplicate ID صفر، Runtime diagnosis و Repair/Replay/Grant/Execution صفر، Packet پذیرفته صفر و Readiness صفر. پایهٔ ۸۴ Risk و ۳۴۳ Trace assignment ثابت است.
