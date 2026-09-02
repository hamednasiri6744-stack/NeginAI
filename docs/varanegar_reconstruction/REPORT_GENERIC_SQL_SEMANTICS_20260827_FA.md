# Semantic footprint پنج Anchor جنریک گزارش

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای Metadata/Definition scan؛ Procedure execution صفر**

پنج Stored Procedure یکتای مرحله قبل بدون اجرا بررسی شدند:

- مجموع ۳۲ پارامتر و ۳۲ Dependency؛
- ReviewOrderPoints به Goods/StockDC/StockGoods/ServerConfig و تابع مقدار نمایشی وابسته است؛
- SaleAmountPerInterval به Sale/Return و تبدیل تاریخ وابسته است؛
- TopDealerSales به Dealer، Sale/Return و Order item وابسته است؛
- SaleDashboard سه Procedure داشبورد و Sale/Return را Orchestrate می‌کند؛
- CardexBatch به Healthy/Damaged/Reserved/Undelivered cardex و Batch/Goods وابسته است.

در متن Moduleها ۱۱ Insert و یک Update lexical دیده شد، اما هیچ Mutation target
ماندگار در کاتالوگ حل نشد؛ Insertها عمدتاً Temp/Table-variable هستند و دو Target
TopDealerSales Alias/حل‌نشده‌اند. پس این Procedures «اثبات‌شده فقط‌خواندنی» اعلام
نمی‌شوند، هرچند هیچ Durable target مشخصی نیز ثابت نشده است.

First-result metadata برای هر پنج Module با خطای کلاس `SYNTAX` توصیف نشد؛ بنابراین
شکل خروجی و Result parity همچنان باز است. هیچ Definition یا مقدار کسب‌وکاری ذخیره نشد.

Artifact: `artifacts/varanegar_analysis/ui/varanegar_report_generic_sql_semantics_20260827.json`

Extractor: `scripts/sql/extract_varanegar_report_generic_sql_semantics.py`
