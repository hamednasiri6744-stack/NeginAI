# دفتر شکاف و مسیر بستن شواهد گزارش‌ها

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای Crosswalk آفلاین؛ هیچ گزارش آماده پیاده‌سازی/Pilot نیست**

چهار شاهد مستقل—قرارداد مقصد، گراف لایه‌ها، مسیر متدی و کاندیدهای کاتالوگ SQL—
برای هر ۲۰ سطح گزارش کنار هم قرار گرفتند. این Crosswalk کاملاً آفلاین است.

## سطح فعلی شواهد

- ۷ گزارش L0: Shell/Selector/Caller/Base path هنوز حل نشده؛
- ۳ گزارش L1: مسیر متد انتهایی داریم، ولی نشانه اجرای Query نداریم؛
- ۱ گزارش L2: نشانه اجرای Query داریم، ولی کاندید SQL نامی نداریم؛
- ۹ گزارش L3: هم نشانه اجرای متد انتهایی و هم کاندید نامی SQL داریم؛
- ۱۳ گزارش مسیر متد انتهایی، ۱۰ گزارش Execution signal و ۱۱ گزارش SQL candidate دارند؛
- ۴ گزارش Coupling مستقیم UI→DataAccess دارند؛
- ۲ گزارش به مرز Command جدا نیاز دارند: PrintBatch و StatementDataEntry؛
- Result parity، Implementation-ready و Pilot-ready همگی صفر هستند.

L3 به معنی آماده‌بودن نیست. هنوز برای هر ۲۰ گزارش SQL identity/parameter binding،
Effective scope، Golden value مالک کسب‌وکار و برابری نتیجه اثبات نشده است.

## ترتیب بستن شکاف

1. مسیرهای L0 از Caller/Base report engine/Delegate/Inheritance بدون اجرای برنامه دنبال شود.
2. متد انتهایی به Query/View دقیق و پارامترها با Metadata فقط‌خواندنی یا Specification مالک متصل شود.
3. Snapshot منبع با Watermark، Provenance و کنترل حریم خصوصی منجمد شود.
4. ورودی و Aggregate مورد انتظار توسط مالک کسب‌وکار تأیید شود.
5. Row count، Total، Null، Round، Business date، Scope، Fault و Concurrency روی Target تطبیق داده شود.
6. Pilot فقط بعد از بسته‌شدن تمام P0ها و تأیید صریح مالک مجاز است.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_report_evidence_gaps_20260827.json`

Builder:
`scripts/windows/build_varanegar_report_evidence_gap_register.py`
