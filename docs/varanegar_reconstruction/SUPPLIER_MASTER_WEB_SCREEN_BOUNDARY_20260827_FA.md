# مرز Command و Screen اطلاعات پایهٔ تأمین‌کننده

## نتیجهٔ اصلی

تأمین‌کننده صرفاً یک Party با چند فیلد مشترک نیست. قرارداد ایستای
`FormSupplier` از ۱۹ Method منتخب و ۶۲۸ Instruction، یازده Field reference،
نه Rule signal و یک Commit signal تشکیل شده است. مسیرهای Save/Delete به پرداخت،
گروه حسابداری، Contact/DL، وضعیت، پیوست، After-save hook و کاردکس متصل‌اند.

## مرز رفتاری

- `SupplierHandler.IsUsedInPay` یک Guard صریح برای حذف/استفاده مالی است؛
- `AfterSaveSupplier` نشان می‌دهد Commit پایان همهٔ اثرهای دامنه نیست؛
- `AccountingSupplierGroup` و `ContactDLCode` روابط حسابداری/طرف‌حساب مستقل‌اند؛
- `StatusGridLookUp`، National/Economic code و Attachment size قواعد/تنظیمات
  جداگانه دارند؛
- `FormSupplierCardex` شاهد آن است که مانده و گردش تأمین‌کننده باید از قرارداد
  کاردکس رسمی تغذیه شود، نه از فیلد mutable فرم.

این شواهد Static call هستند و ترتیب Branch، مقدار مجوز/تنظیم، موفقیت Commit و
اثر Runtime را ثابت نمی‌کنند.

## Screen candidate وب

اسکن کامل Assembly تعداد ۴۱ Field حل‌شده، ۳۷ Component و دوازده Web-input
candidate داد. چهارده Layout binding برای سیزده Control ثبت شد؛ هر دوازده Input
دارای Label چیدمانی نامزد هستند و هشت Input در Methodهای منتخب Reference شده‌اند.
Declared-field catalog قبلی این فرم را صفر گزارش می‌کرد، اما Parse مستقیم TypeDef
و `InitializeComponent` فرم را حل کرد؛ این تفاوت یک محدودیت Extractor قبلی بود،
نه نبودن فیلد در Runtime package.

Screen مقصد به ۳۲ Golden case مصنوعی طراحی‌شده برای Save/Delete، مجوز، Scope،
Duplicate، In-use، Retry، Failure و Reconciliation وصل است و Gap تعریف Golden
صفر شد. با این حال Owner-approved، Implementation-ready و
Runtime-Golden-executed همگی صفرند؛ بنابراین Write همچنان مسدود است.
ترتیب کم‌ریسک:

1. List/search/detail فقط‌خواندنی با Scope؛
2. Review مالک روی Field/Label/Lookup و مرز Party/Supplier؛
3. Golden caseهای Auth/Scope/Duplicate/Retry/Delete-in-use/Payment/Cardex؛
4. Save نسخه‌دار و Idempotent در Target test DB ایزوله؛
5. Delete فیزیکی فقط پس از تصمیم Retention و Reconciliation مالی.

## شواهد

- `varanegar_supplier_master_command_contract_20260827.json`
- `varanegar_supplier_ui_label_candidates_20260827.json`
- `varanegar_supplier_full_field_metadata_20260827.json`
- `varanegar_supplier_layout_bindings_20260827.json`
- `negin_erp_supplier_master_web_screen_contract_candidate_20260827.json`
- Risk `R-038`

Builderهای اختصاصی:

- `build_varanegar_supplier_master_command_contract.py`
- `build_negin_erp_supplier_master_web_screen_contract_candidate.py`

تمام استخراج‌ها Static/Offline/Read-only بودند. Assembly اجرا نشد، UI لمس نشد،
هیچ Command یا Procedure اجرا و هیچ دادهٔ تجاری خوانده یا نوشته نشد.
