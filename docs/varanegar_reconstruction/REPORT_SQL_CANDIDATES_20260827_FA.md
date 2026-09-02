# نامزدهای SQL گزارش‌ها در Clone

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای Catalog candidate؛ Execution path و Result parity اثبات نشده**

از ۲۷ DataAccess type و Memberهای گزارش، ۴۰ Search term معنادار استخراج و فقط در
کاتالوگ Clone فقط‌خواندنی جست‌وجو شد. هیچ Query/Procedure/View/Trigger اجرا نشد؛
Definition و Literal نیز ذخیره نشده است.

## نتیجه

- ۴۰ Search term؛ ۲۲ Term دارای Candidate و ۱۸ Term بدون Name match؛
- ۵۱۸ Object یکتا: ۱۱۲ Table و ۴۰۶ Module؛
- ۱۱ Report حداقل یک Candidate دارد و ۹ Report ندارد؛
- ده Term به سقف ۴۰ Candidate رسیدند؛ یعنی Search نامی برای واژه‌های عمومی مثل
  Sale/Customer گسترده و عمداً بریده شده است؛
- شش Exact normalized match مهم: `dbo.AccYear`، `dbo.Customer`، `dbo.Goods`،
  `dbo.ProductionOrderItem`، `dbo.ServerConfig` و `dbo.Supplier`.

از Memberها Candidateهای مشخص‌تری مثل `inv.usp_sdsn_GetCardexReport`، خانواده‌ی
`CustomerCardex`، `SupplierCardex` و `ICA.USP_VchHealthyCardex_GetList` دیده شد.
این‌ها هنوز Name candidate هستند. Termهایی مثل `CallCenterProductCustomerReport`،
`ProductQtyReport`، `PrintInvoice` و `TRSReport22/23` Name match ندارند؛ DataAccess
می‌تواند از Dynamic SQL، نام عمومی، Report engine یا Dataset تزریق‌شده استفاده کند.

## قاعده‌ی استفاده

هیچ‌کدام از ۵۱۸ Object نباید صرفاً با Name match به Query مقصد تبدیل شود.
Candidate تنها فهرست بررسی است. برای اثبات Anchor باید حداقل DataAccess method →
SQL object، پارامتر/فیلتر، Business date و Golden result توسط شاهد مستقل وصل شود.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_report_sql_candidates_20260827.json`

Extractor:
`scripts/sql/extract_varanegar_report_sql_candidates.py`
