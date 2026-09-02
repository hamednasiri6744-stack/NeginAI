# کاتالوگ گزارش و Query surface وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۲۰ از ۲۰ Report/Analysis form با IL هدفمند؛ هیچ گزارش اجرا نشد**

## خط مبنا

- ۲۰ فرم گزارش/تحلیل؛
- ۸۸ Method گزارش/چاپ/بارگذاری؛
- ۷۸ Call edge به Business/DataAccess؛
- ۱۶ فرم با Filter contract قابل مشاهده؛
- صفر اجرای Report، صفر Export و صفر ردیف/جمع عملیاتی ذخیره‌شده.

## Dashboard عمومی

Dashboard موجود دست‌کم پنج خانواده Chart دارد:

- بازبینی نقطه سفارش کالا؛
- مبلغ چک به تفکیک وضعیت؛
- مبلغ فروش در بازه؛
- فروش و برگشت فروش ماهانه؛
- فروش Dealerهای برتر.

Call graph خود `FormMainDashboard` منبع داده را آشکار نمی‌کند؛ Chartها در
UserControlهای جدا هستند. این Dashboard برای مقصد صرفاً شاهد KPI intent است و
تا استخراج Source/metric definition نباید عددهای آن مرجع تصمیم شوند.

## Cardex طرف‌حساب

سه Query surface مهم وجود دارد:

- `FormSupplierCardex -> SupplierHandler.SupplierCardex`؛
- `FormCustCardex -> CustomerCardex / CustomerCardexCentralized`؛
- `FormCurrencyCustCardex -> CustomerCurrencyCardex / Centralized`.

فیلترها و Drill-downها شامل سال مالی، دفتر/حوزه فروش، نوع مشتری، کد رخداد،
Sale/RetSale/FreeInvoice و شماره سند هستند. Cardex ارزی Contract مستقل دارد؛
نباید با تبدیل نمایشی Currency روی Cardex ریالی بازسازی شود. حالت Centralized
نیز باید در API مقصد صریح باشد.

## گزارش‌های موجودی و تولید

`FormReportResultList` یک Report واحد نیست؛ Router چند Query است:

- Cardex و Cardex سری ساخت؛
- Batch history؛
- موجودی آسیب‌دیده؛
- سفارش خرید بدون انتقال؛
- خروج‌های تأییدنشده؛
- سفارش باز و فروش باز؛
- دلیل رزرو؛
- Free invoice.

همه با Context سال مالی/DC/انبار/کالا اجرا می‌شوند. بنابراین در وب یک Endpoint
همه‌کاره با ستون‌های Nullable مناسب نیست؛ هر Query باید Metric/column contract
و Pagination/Export policy خود را داشته باشد.

`FormProductionOrderReport` Procedure
`USP_SDSNET_ProductionOrderReport` را با بازه تاریخ تولید، کالا و انبار مصرف
می‌کند. `FormProductionDetailReport` Healthy/Waste/with-stock/without-stock و
سری ساخت را تفکیک می‌کند. `FormVchHealthyCardex` Master/Detail جدا دارد.

## چاپ فروش و توزیع یک Side effect است

`FormPrintBatch`، `FormReportFactor` و `FormReportRetSale` فقط Renderer نیستند:

- Validator چاپ و وضعیت Distribution دارند؛
- AccYear/DC/OprDate، SaleOffice، Exit/DistNo و Report type را مصرف می‌کنند؛
- مسیرهای Factor، Return order، Exit list/detail و Team distribution جداست؛
- `SetPrintCompleated...` یا Login چاپ را ثبت می‌کنند.

پس «Preview» Query است ولی «Print completed» Command/Audit است. نسخه وب باید
Preview token/نسخه داده، Permission چاپ و ثبت رویداد موفق را جدا کند؛ دانلود
PDF نباید بی‌دلیل Status چاپ را تغییر دهد.

## Statement و Preview Legacy

`frmReportPreview` و MultiReport فقط پوسته Preview روی Connection قدیمی‌اند و
Metric contract محسوب نمی‌شوند. در مقابل `FormStatementDataEntry` با
`StatementHandler/Validator`، شماره، تاریخ، نوع، سررسید، مشتری/Dealer، مبلغ
تبدیل و Context DC/سال مالی کار می‌کند؛ این صفحه در اصل Aggregate/Command خزانه
است، حتی اگر به‌علت نام در خانواده گزارش دیده شود.

## قرارداد گزارش مقصد

هر گزارش باید این موارد را صریح کند:

1. `report_id` و نسخه Metric definition؛
2. Source projection و Business date semantics؛
3. Required filters و Defaultهای مجاز؛
4. Data partition سال/DC/SaleOffice/StockDC؛
5. Permission مشاهده، Drill-down، Export و Print جدا؛
6. ستون‌ها، واحد، Currency و Sign convention؛
7. Pagination و سقف Export؛
8. Privacy aggregation/ماسک PII؛
9. Freshness و Snapshot timestamp؛
10. Reconciliation/Golden totals با منبع رسمی.

## Artifact و محدودیت

- `artifacts/varanegar_analysis/ui/varanegar_report_catalog_20260827.json`
- `scripts/windows/build_varanegar_report_catalog.py`

این مرحله Query source و Filter surface را از کد ثابت استخراج کرده، نه نتیجه
واقعی گزارش را. تعریف دقیق KPI Dashboard و Default فیلترهای runtime هنوز Gate
باز است.
