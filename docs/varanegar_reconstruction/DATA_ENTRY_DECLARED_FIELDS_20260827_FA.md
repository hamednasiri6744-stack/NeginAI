# Field metadata اعلام‌شده فرم‌های ورود داده

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای ۱۴۱ Type؛ Runtime binding هنوز اثبات نشده**

FieldList متادیتای Typeهای ۱۴۱ فرم مستقیماً از DLLهای Hash‌شده خوانده و با
واژه‌نامه Usage مرحله قبل تطبیق داده شد؛ Assemblyها Load/Execute نشدند.

## نتیجه

- هر ۱۴۱ Type حل شد؛ Hash mismatch و Metadata failure صفر؛
- ۹۵ فرم Field candidate اعلام‌شده دارند و ۴۶ فرم بدون Control field محلی‌اند؛
- ۸۱۳ Field candidate و ۴۹۰ نام یکتا؛
- ۵۸۱ مورد با Method usage قبلی غنی شد و ۲۳۲ مورد فقط در Metadata اعلام شده بود؛
- ۱۸۹ Label field، ۱۲۸ Text، ۳۰ Numeric، ۲۰ Date، ۲۰ Choice، ۴۵ Boolean،
  ۷ Lookup، ۱۱۹ Grid، ۸۸ Command، ۱۶۰ Container و ۷ Media.

۴۶ فرم بدون Field محلی می‌توانند Base/inherited/dynamic باشند؛ «فرم بدون فیلد»
نتیجه‌گیری نمی‌شود. Signature متادیتا در این مرحله Decode نشده و Runtime type،
Label pairing، Binding، Requiredness، Visibility و Enabled state همگی باز هستند.

Artifact: `artifacts/varanegar_analysis/ui/varanegar_data_entry_declared_fields_20260827.json`

Extractor: `scripts/windows/extract_varanegar_data_entry_declared_fields.py`
