# Binding جنریک گزارش‌های Shell

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای IL محدود؛ SQL identity و Result parity صفر**

از ۸ Caller type کشف‌شده، پنج EntityHelper، پنج Handler/Validator و ۱۷ Filter
member استخراج شد. دو نمودار داشبورد `GetAllView` جنریک دارند:

- ReviewOrderPoints با `GoodsViewEntityHelper` و فیلترهای StockDC/SystemPart؛
- TopDealerSale با `SaleDashboardViewEntityHelper` و فیلتر Month؛
- Selector گزارش موجودی، `CardexBatchEntityHelper` و فیلترهای AccYear، بازه تاریخ،
  DC/Stock، کالا، گروه، سازنده، وضعیت، نوع موجودی و Reserved cause را می‌سازد.

این فهرست Shape قرارداد Query مقصد را روشن می‌کند، ولی Generic token هنوز Adapter
واقعی و SQL نهایی را پنهان می‌کند. هیچ Branch یا Query اجرا نشده است.

Artifact: `artifacts/varanegar_analysis/ui/varanegar_report_generic_bindings_20260827.json`

Extractor: `scripts/windows/extract_varanegar_report_generic_bindings.py`
