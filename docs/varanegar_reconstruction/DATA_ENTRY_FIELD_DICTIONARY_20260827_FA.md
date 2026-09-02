# واژه‌نامه استاتیک فیلدهای فرم‌های ورود داده

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای ۱۴۱ فرم منتخب؛ Field candidate است نه Binding نهایی**

از IL Redacted موجود، نام کنترل‌های متعلق به خود فرم، نوع تقریبی بر اساس Prefix،
مصرف در Methodهای Validation/Write/Selector و Labelهای UI قبلاً Allowlist‌شده
استخراج شد.

## پوشش

- ۱۴۱ فرم Data-entry/Master-detail منتخب؛
- ۹۳ فرم دارای Field candidate و ۴۸ فرم بدون نام کنترل قابل‌اعتماد در این روش؛
- ۵۸۱ Field candidate و ۳۵۰ نام یکتا؛
- ۱۱۸ Text، ۲۹ Numeric، ۱۸ Date، ۱۹ Choice، ۳۹ Boolean، ۷ Lookup، ۱۰۷ Grid،
  ۸۷ Command، ۱۵۰ Container و ۷ Media؛
- ۷۴ Field با Write/Submit signal، ۵۱ Validation، ۴۹ Selector و ۱۳ Permission؛
- ۱٬۵۹۴ Label امن در ۱۳۹ فرم، عمداً بدون Pairing ساختگی با Field.

Required/Nullable، Data binding، Visibility و Enabled state مؤثر هیچ Fieldی هنوز
اثبات نشده است. Prefix نام کنترل نیز Runtime type proof نیست. برای ERP مقصد، این
Artifact مبنای سؤال و طراحی فرم است، نه مجوز ساخت مستقیم Schema/UI.

Artifact: `artifacts/varanegar_analysis/ui/varanegar_data_entry_field_dictionary_20260827.json`

Builder: `scripts/windows/build_varanegar_data_entry_field_dictionary.py`
