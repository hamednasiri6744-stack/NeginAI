# نوع CLR فیلدهای فرم‌های ورود داده

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ هر ۸۱۳ Signature حل شد، Runtime behavior صفر**

Signature متادیتای هر ۸۱۳ Field candidate Decode و Tokenهای TypeDef/TypeRef بدون
Load کردن Assembly حل شد:

- ۸۰۵ TypeDef/TypeRef، پنج Primitive و سه Generic definition؛ Failure صفر؛
- ۵۳ CLR type یکتا؛
- پرتکرارها: ۱۷۱ `System.Windows.Forms.Label`، ۶۹ DevExpress TextEdit، ۴۹ VNGrid،
  ۴۶ Panel، ۳۹ Button، ۳۸ CheckEdit، ۳۱ ButtonEdit، ۳۰ GroupBox و ۳۰ SimpleButton؛
- ۵۹۲ Prefix-kind با نوع حل‌شده هم‌خوان و ۲۲۱ مورد mismatch/unclassified است.

Mismatchها نشان می‌دهد Prefix نام Legacy برای طراحی نوع ورودی قابل‌اعتماد کامل
نیست؛ مثلاً بعضی نام‌های Date/Check/Lookup در واقع TextEdit، BindingSource یا
GridView هستند. برای ERP مقصد باید CLR type + usage + قرارداد کسب‌وکار کنار هم
استفاده شود، نه فقط نام Field.

نوع CLR ثابت می‌کند Field با چه Typeای اعلام شده، نه اینکه در Runtime visible/
enabled باشد یا به کدام Column وصل، required یا مجاز باشد. این موارد همچنان بازند.

Artifact: `artifacts/varanegar_analysis/ui/varanegar_data_entry_field_types_20260827.json`

Extractor: `scripts/windows/extract_varanegar_data_entry_field_types.py`
