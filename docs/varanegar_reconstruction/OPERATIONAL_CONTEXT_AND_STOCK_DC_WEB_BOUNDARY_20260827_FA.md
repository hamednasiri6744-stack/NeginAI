# مرز سال عملیاتی، مرکز/انبار و تنظیم حسابداری انبار

## نتیجهٔ اصلی

سه فرم `FormAccYear`، `FormStockDC` و `FormICAstockdcinfo` یک «تنظیم شعبه» ساده
نیستند. قرارداد ایستا ۴۱ Method منتخب، ۱٬۱۰۵ Instruction، بیست Field reference،
نه Rule signal و دو Commit signal دارد. سال عملیاتی، سال مالی، DC، دفتر فروش،
انبار/Stock، نوع حمل، نوع موجودی و روش قیمت‌گذاری حسابداری مفاهیم جدا هستند.

## قواعد مشاهده‌شده

- `AccYearHandler/Validator` سال عملیاتی را مدیریت می‌کند؛ این شناسه با
  `dbo.FiscalYear` قابل جایگزینی نیست؛
- `FormStockDC` رابطهٔ DC، SaleOffice، Stock و ShipType را می‌سازد و فهرست
  `DCSaleOffice` را در مسیر Pre-command بازنویسی می‌کند؛
- StockType از پنج Flag مستقل `1,2,4,8,16` ساخته می‌شود. این شاهد در کنار
  Encoding ترتیبی `0..4` و تابع `GNR.HasStockType` یک Gap سازگاری واقعی است؛
- `FormICAstockdcinfo` برای هر StockDC یک `PriceMethod` و Guard
  `StockHasPrice` دارد و Lookup عضویت انبار را پس از Save تغییر می‌دهد.

هیچ‌یک از این Callها ترتیب Branch، مقدار واقعی Setting، موفقیت Commit یا اثر
Runtime را ثابت نمی‌کند.

## Screen candidate مقصد

برای دو فرم MainData تعداد ۶۹ Field، ۶۲ Component و ۲۳ Web-input ثبت شد؛ ۲۳
Layout binding و ۱۷ Input+Label وجود دارد. فرم تنظیم حسابداری انبار نیز ۱۴ Field،
ده Component، سه Web-input و سه Layout binding دارد، اما Label چیدمانی قابل اتکا
برای آن صفر است. در مجموع سه Screen با ۲۶ Input ساخته شد؛ ۱۷ Input Label دارد و
نه Input بدون متن استاتیک قابل اتکا است.

سه Screen در مجموع به ۹۶ Golden case مصنوعی طراحی‌شده وصل‌اند و Gap تعریف
Golden صفر شد. Owner approval، Implementation readiness و Runtime Golden
execution همچنان صفر است و Write مسدود می‌ماند. ترتیب ساخت:

1. انتخاب/نمایش Context فقط‌خواندنی و Explainable؛
2. تأیید مالک روی معنای DC=0/1، سال عملیاتی/مالی و ترکیب Office/Stock؛
3. قرارداد رسمی Encoding نوع انبار و PriceMethod؛
4. Goldenهای Auth/Scope/Overlap/Closed-year/In-use/Retry؛
5. Write فقط در Target test DB و پس از Reconciliation سال/انبار/کاردکس.

## شواهد

- `varanegar_operational_context_command_contracts_20260827.json`
- `varanegar_operational_context_main_ui_labels_20260827.json`
- `varanegar_operational_context_main_full_fields_20260827.json`
- `varanegar_operational_context_main_layout_20260827.json`
- `varanegar_stock_accounting_context_ui_labels_20260827.json`
- `varanegar_stock_accounting_context_full_fields_20260827.json`
- `varanegar_stock_accounting_context_layout_20260827.json`
- `negin_erp_operational_context_web_screen_contract_candidates_20260827.json`
- Risk `R-039`

Builderهای اختصاصی:

- `build_varanegar_operational_context_command_contracts.py`
- `build_negin_erp_operational_context_web_screen_contract_candidates.py`

تمام استخراج‌ها Static/Offline/Read-only بودند؛ Assembly اجرا نشد، UI لمس نشد،
هیچ Command/Procedure اجرا و هیچ دادهٔ تجاری خوانده یا نوشته نشد.
