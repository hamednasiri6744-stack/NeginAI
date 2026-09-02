# مرز فاکتور خرید، برگشت خرید و Trigger محافظ رابطه

## نتیجهٔ اصلی

ذخیره/حذف فاکتور خرید و برگشت خرید در وارانگار یک CRUD ساده نیست. دو فرم
`FormSupInvoiceDataEntry` و `FormRetSupInvoiceDataEntry` با یک DataContext مشترک
ثبت می‌شوند، کنترل‌های مبلغ/تعداد/باقی‌مانده/تأمین‌کننده و Toll/XToll دارند و
رابطهٔ فاکتور خرید با سند انبار یک Guard تریگری ویژه دارد.

## شواهد UI و Business

۱۹ Method منتخب با ۱٬۱۵۵ Instruction و ۱۵ Field مورد استفاده ثبت شد. سه Method
دارای سیگنال `DataContext.Commit` هستند. قواعد ایستای دیده‌شده:

- فعال‌بودن تأمین‌کننده؛
- تکراری‌نبودن شماره فاکتور یا کالا؛
- مقدار، باقیمانده، قیمت و مبلغ مؤثر؛
- سازگاری فاکتور مبدأ و سند انبار در برگشت؛
- محاسبه و پاکسازی Toll/XToll؛
- کنترل Delete و Permission.

دو Command مقصد فعلاً Candidate و تأییدنشده‌اند:

- `supplier_invoice.save_or_delete`
- `supplier_invoice_return.save_or_delete`

## یافتهٔ پرخطر Trigger Guard

در IL لایه DataAccess هفت SQL literal امن ثبت شد. دو Literal دقیقاً
`ENABLE TRIGGER` و `DISABLE TRIGGER` را برای
`tr_VN_PreventDeletetblSupInvInvoiceRelation` نشان می‌دهند و Delete روی
`ICA.tblSupInvInvoiceRelation` دیده می‌شود. این متن‌ها فقط شاهد هستند و هرگز
اجرا نشدند.

کاتالوگ Clone نشان داد جدول رابطه پنج ستون، یک PK، یک FK و چهار Trigger فعال
دارد. گراف سه‌لایهٔ همان چهار Trigger بدون Truncation به ۲۱۵ Node/۳۴۳ Edge،
۱۴۳ Trigger node، ۴۶ Table و ۲۹ Write target رسید؛ ۴۱ Dependency هنوز حل‌نشده
است. بنابراین خاموش/روشن‌کردن یک Trigger محلی می‌تواند در مرز Legacy به
رفتار گسترده‌تری وصل باشد و نباید در مقصد کپی شود.

## قرارداد مقصد

- رابطه فاکتور خرید↔سند انبار باید Aggregate invariant و Constraint صریح باشد؛
- Save، Delete و Return Commandهای Idempotent و نسخه‌دار جدا می‌خواهند؛
- مقصد نباید برای عبور از Guard، Trigger را Disable کند؛ عملیات جبرانی باید
  مجوز، دلیل، Audit و Reconciliation داشته باشد؛
- Supplier balance، stock voucher، invoice relation و Toll effects باید در
  Golden caseهای موفق/Retry/Fault/Delete/Return با هم آشتی داده شوند؛
- `TypeSpecRow` جنریک و Branch واقعی Runtime هنوز Gap است، پس قرارداد Command
  برای پیاده‌سازی آماده یا Owner-approved نیست.

## Screen candidate وب

سه فرم هم‌خانوادهٔ سند انبار/فاکتور خرید/برگشت خرید در مجموع ۹۴ ورودی نامزد،
۵۹ ورودی دارای Label چیدمانی و ۳۵ ورودی بدون Label چیدمانی دارند. ۷۷ Golden
case مصنوعی به Save/Confirm/Returnهای دارای قرارداد وصل شده‌اند. Deleteهای خرید
فعلاً فقط Secondary candidate هستند و تا تکمیل Golden contract غیرفعال می‌مانند.

## شواهد ماشین‌خوان

- `varanegar_supplier_invoice_command_contract_20260827.json`
- `varanegar_supplier_invoice_sql_anchor_contracts_20260827.json`
- `varanegar_supplier_invoice_relation_source_model_20260827.json`
- `varanegar_supplier_invoice_relation_trigger_transitive_graph_20260827.json`
- `varanegar_stock_supplier_ui_label_candidates_20260827.json`
- `varanegar_stock_supplier_full_field_metadata_20260827.json`
- `varanegar_stock_supplier_layout_bindings_20260827.json`
- `negin_erp_stock_supplier_web_screen_contract_candidates_20260827.json`

هیچ فرم، Command، SQL statement، Trigger یا Business row اجرا/تغییر داده نشد؛
تمام خواندن کاتالوگ از Clone فقط‌خواندنی انجام شد.
