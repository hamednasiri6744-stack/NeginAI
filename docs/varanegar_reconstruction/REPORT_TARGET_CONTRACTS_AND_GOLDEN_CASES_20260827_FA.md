# قرارداد مقصد و Golden case گزارش‌ها

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای طراحی مصنوعی؛ Result parity و UAT هنوز صفر**

برای هر ۲۰ سطح گزارش/داشبورد/چاپ، Query contract مقصد ساخته شد و ۱۷۵ Golden
case مصنوعی تولید شد. هیچ گزارش یا Print در وارانگار اجرا نشده است.

## پوشش

- ۲۰ Query surface؛
- ۳ Export-to-file؛
- ۳ Command مستقل `mark_print_completed`؛
- ۲ Command مستقل `statement.create_or_update`؛
- ۱۷۵ Case شامل Authorization، Scope، Pagination، Freshness، Privacy، Filter
  boundary، Export، Idempotency، Concurrency و Fault injection.

## قواعد غیرقابل‌مذاکره

- هر Query با Actor/Context/Scope، Filter allowlist، Date bound، Page-size cap و
  Stable cursor اجرا می‌شود؛
- Response باید Query id، Filter hash، Source watermark، Generated time، Row
  count و Privacy class داشته باشد؛
- Preview و Export مطلقاً ERP state یا `print-completed` را تغییر نمی‌دهند؛
- `mark_print_completed` یک Command جدا با Permission، `command_id`،
  `expected_version`، Audit و Outbox است؛
- دو فرم Statement که Save signal دارند، Query و Command جدا می‌گیرند؛
- Export فقط File event خارجی با Receipt/Hash/Expiry است و ERP mutation نیست.

## مرز شاهد

Static IL وجود فرم، Filter call، Print/Export/Save signal و Permission پیشنهادی
را نشان می‌دهد؛ منطق Query و برابری عدد نهایی همه گزارش‌ها هنوز اجرا و اثبات
نشده است. ازاین‌رو `result_parity_proven_contract_count=0` باقی مانده و برای هر
گزارش Golden value تأییدشده‌ی مالک کسب‌وکار لازم است.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_report_target_contracts_golden_cases_20260827.json`

Builder:
`scripts/windows/build_varanegar_report_target_contracts_and_golden_cases.py`

