# ورودی‌های Shell و Selector گزارش‌ها

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای اسکن کامل Metadata/IL؛ Runtime و Result parity صفر**

۷ گزارش L0 در تمام ۶۲ Assembly فعال (۷٬۶۵۰ Type و ۸۱٬۴۷۳ Method body) برای
Caller، Constructor، Inheritance و نام دقیق جست‌وجو شدند. Assemblyها Load یا
Execute نشدند.

## یافته‌ها

- ۴ Shell دارای Entry-point استاتیک شدند و ۳ مورد هنوز بدون ورودی Package IL ماندند؛
- `FormZoomChart` از شش Chart گزارش داشبورد و در رخداد Zoom ساخته می‌شود؛
- `FormStockGoods.OtherButtonClick`، `FormSelectMainReport` را باز می‌کند؛
- `FormSelectMainReport.MenuButtonSelect_Click` به `FormSelectGoodsType` و
  `FormProductionDetailReport` می‌رسد؛
- `FormMainDashboard`، `FormPrintInvoice` و `FormStatement` ورودی خارجی مستقیم در
  IL Package ندارند و احتمال Route engine، Framework base یا Reflection باز است؛
- ۱۰ Reference خارجی، ۹ Constructor reference، صفر Hash mismatch و صفر خطای
  غیرمنتظره ثبت شد.

این یافته ساختار Navigation/Caller را بهتر می‌کند، اما Query، Branch مؤثر یا خروجی
گزارش را ثابت نمی‌کند. مرحله بعد، خود Callerهای پیدا‌شده و Business/DataAccessهای
آن‌ها را دنبال می‌کند.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_report_shell_entrypoints_20260827.json`

Extractor:
`scripts/windows/extract_varanegar_report_shell_entrypoints.py`
