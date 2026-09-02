# گراف وابستگی گزارش‌ها از UI تا Business و DataAccess

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای Static trace؛ Runtime و Result parity صفر**

۲۰ سطح گزارش روی Package کامل فقط‌خواندنی تا Business و DataAccess دنبال شد؛
Assemblyها فقط Parse شدند و هیچ Type، Report، Query یا فرمانی Load/Execute نشد.

## نتیجه

- ۶۷۴ Edge فرست‌پارتی از UI؛
- ۷۶ Edge UI→Business به ۲۵ Business type با ۳۷۷ Method body؛
- ۲۳۹ Edge Business→DataAccess به ۲۷ DataAccess type با ۴۰۰ Method body؛
- ۱۳ Report دارای مسیر Business→DataAccess؛
- ۲ Report فقط مسیر مستقیم UI→DataAccess در این عمق دارند؛
- در مجموع ۴ Report حداقل یک Coupling مستقیم UI→DataAccess دارند؛
- ۵ Report در Trace یک‌مرحله‌ای DataAccess پیدا نکردند؛
- صفر Hash mismatch، Metadata error، Method-body error و unresolved first-party type.

پنج سطح بدون مسیر یک‌مرحله‌ای:

- دو Dashboard عمومی؛
- `FormPrintInvoice`؛
- دو Selector گزارش موجودی (`FormSelectGoodsType` و `FormSelectMainReport`).

این پنج مورد احتمالاً Shell/Selector/Base-engine/Caller-driven هستند؛ نبود Edge در
این عمق دلیل نبود Query نیست. تا Trace ارث‌بری/Caller یا شاهد Runtime، Result
semantics آن‌ها باز می‌ماند.

## کشف معماری

Cardex مشتری/ارزی، Supplier cardex، Print batch/factor/return، Healthy cardex،
Production reports و Statement مسیرهای Business/DataAccess مشخص دارند. بااین‌حال
چهار Surface هنوز Coupling مستقیم DataAccess از UI دارند؛ این الگو نباید وارد Web
ERP شود. UI مقصد فقط Query/Command API را صدا می‌زند و DataAccess مالک ماژول است.

## مرز شاهد

Static call edge اجرای Branch، SQL نهایی، محاسبه‌ی Amount، Filter semantics،
Authorization مؤثر یا برابری خروجی را اثبات نمی‌کند. قراردادهای ۱۷۵ Case هنوز
تا Golden valueهای مالک کسب‌وکار Synthetic باقی می‌مانند.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_report_dependency_graph_20260827.json`

Extractor:
`scripts/windows/extract_varanegar_report_dependency_graph.py`

