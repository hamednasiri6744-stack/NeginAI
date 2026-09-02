# ماتریس ردیابی نیازمندی، شاهد، تست و ریسک ERP نگین

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای ردیابی طراحی؛ صفر ماژول Command-ready/Pilot-ready/Production-ready**

این ماتریس ۱۴ ماژول مقصد را به ده منبع ماندگار وصل می‌کند: ماتریس آمادگی،
ریسک‌ها، Backlog فاز P0، شش خانواده‌ی Golden case و ۱۴ بلوک فعالیت سه‌ماهه.
همه‌ی ۸۷۷ Golden case، هر ۵۶ ریسک، هر ۲۶ آیتم P0 و تمام Domainهای فعالیت بدون
مورد گمشده ردیابی شدند. ۹ ماژول شاهد مستقیم فعالیت سه‌ماهه دارند.

## نمای فشرده

| ماژول | Golden case | ریسک باز | ریسک بحرانی | P0 مستقیم |
|---|---:|---:|---:|---:|
| platform | 0 | 17 | 12 | 14 |
| organization_context | 64 | 3 | 1 | 1 |
| identity_authorization | 19 | 6 | 5 | 2 |
| configuration | 36 | 15 | 9 | 1 |
| master_data | 114 | 6 | 1 | 0 |
| pricing_rules | 82 | 4 | 0 | 0 |
| sales | 97 | 23 | 12 | 0 |
| inventory | 79 | 25 | 17 | 0 |
| distribution | 74 | 8 | 7 | 0 |
| receivables_treasury | 69 | 17 | 14 | 0 |
| procurement_payables | 50 | 13 | 11 | 0 |
| accounting | 18 | 35 | 25 | 0 |
| reporting_documents | 175 | 10 | 1 | 1 |
| integration_migration | 0 | 39 | 23 | 7 |

تعداد Assignment ریسک ۲۲۱ است چون یک ریسک می‌تواند چند ماژول را درگیر کند.
نبود Golden case مستقیم برای Platform و Migration به معنی بی‌شاهدبودن نیست؛
این‌ها فعلاً با قرارداد Foundation/Backlog/ریسک ردیابی شده‌اند. ۳۶ Case انتشار
تنظیمات به مالک درست یعنی Configuration متصل است؛ همه Caseها پیش از پیاده‌سازی
باید در Harness ایزوله اجرا شوند.

## نتیجه برای ساخت

- P0 باید از Platform، Context، Authorization، Configuration، Migration و
  Read-model شروع شود؛ این ترتیب ادعای آماده‌بودن Commandهای مالی نیست.
- Sales، Inventory، Treasury، Accounting و Integration بیشترین تراکم ریسک بحرانی
  را دارند و بدون Reconciliation و Fault-injection نباید Write فعال بگیرند.
- هر Ticket پیاده‌سازی باید حداقل یک Evidence ref، یک Risk/Control و یک Golden
  case یا Gap صریح داشته باشد؛ «صفحه ساخته شد» به‌تنهایی Definition of Done نیست.

## محدودیت

این Artifact روابط شواهد موجود را ردیابی می‌کند، نه اینکه رفتار Runtime را اجرا
یا تایید کند. UAT مالک کسب‌وکار، انتخاب Stack، RPO/RTO، Restore، Performance و
پایلوت هنوز بازند.

Artifact:
`artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260827.json`

Builder:
`scripts/windows/build_negin_erp_requirements_traceability.py`
