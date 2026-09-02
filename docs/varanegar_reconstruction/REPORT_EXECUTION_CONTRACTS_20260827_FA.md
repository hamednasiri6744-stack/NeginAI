# قرارداد Report، Preview، Export و Print

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۲۰ Surface؛ سه خروجی سندی Stateful، سه Export فایل و دو فرم Command-like**

## اصل مهم

در وارانگار «گزارش» همیشه Read-only نیست. سه فرم چاپ فاکتور/مرجوعی/Batch پس از
چاپ موفق Hook ثبت تکمیل چاپ دارند. دو فرم Statement نیز با وجود ظاهر گزارشی،
`SaveCommand` و Validator دارند و Aggregate عملیاتی‌اند.

ERP مقصد باید پنج Capability مستقل داشته باشد:

```text
report.read
report.preview
report.export_file
document.print
document.mark_print_completed
```

Preview نباید Business state را تغییر دهد. فقط تأیید تکمیل واقعی خروجی/چاپ، با
Command اتمیک و Idempotent، مجاز است Print-completed event را ثبت کند.

## دسته‌بندی ۲۰ Surface

- سه `transactional_document_output`:
  - `FormPrintBatch`؛
  - `FormReportFactor`؛
  - `FormReportRetSale`.
- سه `read_report_with_file_export`:
  - Production detail؛
  - Stock report result list؛
  - Healthy voucher cardex.
- چهار Render/preview shell شامل Cardex مشتری، ارزی، تأمین‌کننده و PrintInvoice؛
- هشت Selector/Dashboard/report shell؛
- دو `report_like_command_form`: Statement list و Statement data entry.

۱۶ Surface Filter contract دارند؛ Scope گزارش باید در Query اعمال شود، نه فقط
Control سمت Client.

## چاپ سند فروش/مرجوعی/توزیع

IL این نشانه‌ها را هم‌زمان نشان می‌دهد:

- `frmPreviewPrint` و Flag `Preview`؛
- رویداد `PrintButtonClick` و `PrintedCompleted`؛
- `SetPrintCompleatedDrFact`، `SetPrintCompleatedReportJoze` یا
  `SetLoginDrFactForVocherOrFactor`.

پس قرارداد مقصد:

1. Preview فقط Render و بدون State change؛
2. Print/Download یک Output job با `output_id` و Template version؛
3. Mark-completed فقط پس از Success signal خروجی؛
4. Retry همان `command_id + document + template/version` رویداد دوم نسازد؛
5. Actor، Scope، Filter hash، نسخه سند و زمان Completion Audit شوند؛
6. Print permission از Read/Preview جدا باشد.

`FormPrintBatch` علاوه بر Dist status، AccYear، DC، SaleOffice، OprDate، ExitNo،
StockDC و نوع گزارش را بررسی می‌کند و خروجی‌های جزء، تیم پخش، فرم خروج، فهرست
خروج و درخواست برگشت را جدا می‌سازد.

## Export فایل

Exportهای Stock/Cardex با `ExportToXls`/Save dialog فایل بیرونی می‌سازند ولی
شاهد Write به ERP برایشان دیده نشد. بااین‌حال Export یک Data exfiltration event
است و باید Permission، Scope، Row limit، Watermark/metadata و Audit جدا داشته
باشد. فایل تولیدی نباید جای Snapshot/version منبع را بگیرد.

## Cardex و Dashboard

- Cardex مشتری معمولی، Cardex ارزی و Centralized مسیرهای Query متفاوت دارند؛
- Supplier cardex به خرید و مرجوعی خرید Drill-down می‌کند؛
- Stock report router شامل Cardex، Batch history، damaged inventory، سفارش/فروش
  باز، خروج تأییدنشده، رزرو و free invoice است؛
- Dashboard پنج Intent دارد: نقطه سفارش، مبلغ چک به وضعیت، فروش بازه‌ای، فروش
  مقابل برگشت ماهانه و Top dealer.

هر Drill-down باید Scope و Permission مقصد را دوباره ارزیابی کند؛ دسترسی به Chart
به‌تنهایی مجوز بازکردن سند زیرین نیست.

## Statement: اصلاح Classification

`FormStatement` و `FormStatementDataEntry` را نباید به Report API منتقل کرد.
آن‌ها StatementNo، AccYear/DC، تاریخ، نوع، مشتری/ویزیتور، ارز/نرخ و Validation
دارند و Data entry ذخیره می‌کند. در مقصد این دامنه Aggregate/Command مستقل با
مجوز `statement.create_or_update` است.

## مرز ایمنی

این تحلیل کاملاً Offline از IL Redacted بود. هیچ Report اجرا/Render نشد، هیچ
چاپ یا فایل Export ساخته نشد، Print-completed ثبت نشد و هیچ مقدار Report/Business
در Artifact ذخیره نشد.

## Artifact و کد

- `scripts/windows/build_varanegar_report_execution_contracts.py`
- `artifacts/varanegar_analysis/ui/varanegar_report_execution_contracts_20260827.json`
- `tests/test_varanegar_ui_evidence.py`
