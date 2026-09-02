# مرز Batch، Stock و Export گزارش جزئیات تولید (`RPT-14`)

این فرم Query مستقیم در UI ندارد. زنجیرهٔ ایستا از چهار Assembly هش‌پین‌شده اثبات شد:
`GetBatchWithStock/GetBatchWithoutStock` از `GetAllView` استفاده می‌کنند؛
`BatchNumberAdapter` از generic base مشتق است؛ `BatchNumberViewEntity` از
`BatchNumberEntity` ارث می‌برد و override آن نام
`usp_sdsnet_BatchNo_GetList` را برمی‌گرداند؛ generic base آن را به `EXEC` و
`DataContext.AllFast` می‌رساند. هیچ Assembly Load/Execute نشده است.

Catalog فقط‌خواندنی `dbo.usp_sdsnet_BatchNo_GetList` را با ۱۸ پارامتر و ۱۸
dependency تأیید کرد. دو mode «دارای موجودی» و «بدون موجودی» با FetchReason تفکیک
می‌شوند، ولی مقدار mapping آن ذخیره یا حدس زده نشده است. مقدار ناشناخته باید رد شود
و نباید به «همه سری‌ساخت‌ها» widen شود.

grain مقصد `goods + stock DC + batch` است. on-hand، damaged، reserved و available
نباید یکی فرض شوند؛ Formula نهایی نیازمند Golden value مالک است. تاریخ تولید و
انقضا نیز business dateهای مستقل‌اند و null آنها با created/migration date پر نمی‌شود.

مسیر Excel مستقیماً فایل Xls می‌سازد و صرفاً external file event است؛ receipt باید
filter hash، row count و content hash داشته باشد و mutation ERP صفر بماند. شش Golden
Case برای دو mode، تفکیک damaged، تاریخ null، منع Scope و export تکراری ثبت شد.
Result parity صفر و Risk count برابر ۸۴ باقی ماند.
