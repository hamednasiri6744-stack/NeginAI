# نامزدهای SQL حاصل از Binding جنریک گزارش‌ها

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای کاتالوگ Clone؛ Linkها Name-candidate هستند**

۳۲ Term حاصل از Caller/Handler/EntityHelper در کاتالوگ Clone فقط‌خواندنی جست‌وجو
شد. ۹ Term به ۲۰۱ Object رسیدند و چهار Term پرتراکم در سقف ۵۰ بریده شدند.

پنج Term یکتای قوی‌تر:

- `ReviewOrderPoints` → `GNR.uspReviewOrderPoints`؛
- `SaleAmountPerInterval` → `GNR.SaleAmountPerInterval`؛
- `TopDealerSale` → `GNR.TopDealerSales`؛
- `SaleDashboard` → `dbo.USP_SDSNET_SaleDashboard_GetList`؛
- `CardexBatch` → `inv.UspRptCardexBatchNo6004`.

چهار Shell کاندید دارند و سه Shell بدون Term/Match باقی ماندند. یکتایی نام و حتی
هم‌خوانی فیلتر، اجرای واقعی یا برابری نتیجه را ثابت نمی‌کند.

Artifact: `artifacts/varanegar_analysis/ui/varanegar_report_generic_sql_candidates_20260827.json`

Extractor: `scripts/sql/extract_varanegar_report_generic_sql_candidates.py`
