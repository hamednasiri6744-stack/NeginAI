# مرز Command و Screen اطلاعات پایهٔ مشتری و کالا

## نتیجهٔ اصلی

فرم‌های مشتری و کالا دو جدول ساده نیستند. قرارداد ایستا از ۲۱ Method منتخب و
۲٬۱۱۹ Instruction، ۲۹ Field مورد استفاده، ده Rule signal و چهار Commit signal
تشکیل شده است. Save/Delete مقصد هنوز Owner-approved، Implementation-ready یا
Runtime-parity-ready نیست.

## مشتری

`FormCustomers` دارای Scope مجوز کاربر و ستاد، وضعیت، مشتری والد، DL code،
حساب/اعتبار، Main/Sub type و رفتار Post-save است. تنظیم
`AutoupdatDLCodeToCustCode` نشان می‌دهد کد حساب تفصیلی و کد مشتری همیشه مستقل
نیستند. Save و Delete هر دو Commit دارند؛ Merge/Unmerge و اثر استفاده‌شدن مشتری
باید جداگانه بسته شوند.

Metadata کامل فرم مشتری ۲۶۳ Field، ۲۳۸ Component، ۶۹ Web-input و ۱۱ کنترل
فرمانی دارد. ۶۶ Layout binding یافت شد ولی فقط ۲۱ Web-input Label چیدمانی ثابت
دارند؛ پس نام‌گذاری و گروه‌بندی صفحه هنوز به Review مالک نیاز دارد.

## کالا

`FormGoods` علاوه بر مشخصات پایه، Barcode، Supplier، Package، BatchPackage،
Main/Sub group crosswalk و تخصیص مرکز را مدیریت می‌کند. حذف کالا به تنظیم
`AllowDeleteGoodsAfterReplicate` وابسته است و `RemoveAllInfoFromGoods` نشان می‌دهد
Delete یک حذف سادهٔ Header نیست.

Metadata کامل کالا ۱۷۸ Field، ۱۴۲ Component، ۶۱ Web-input و پنج کنترل فرمانی
دارد. ۵۶ Layout binding و ۴۷ Input+Label ثبت شد. Barcode/Supplier/Package/Batch
باید Child relation یا Aggregate مستقل باقی بمانند، نه ستون‌های تخت فرم.

## Screen candidate مقصد

دو Screen در مجموع ۱۳۰ Input، ۱۶ Command control و ۶۸ Input+Layout-label دارند؛
۶۲ Input هیچ متن استاتیک قابل اتکایی ندارند. فقط پنج Input در Methodهای منتخب
مستقیماً Reference شده‌اند؛ این به‌معنی بی‌استفاده‌بودن بقیه نیست، بلکه Gap
Binding ایستا است.

برای چهار Command نامزدِ ذخیره/حذف مشتری و کالا ۶۴ Golden case مصنوعی تعریف
شد: برای هر Command یازده حالت مشترک و پنج حالت دامنه‌ای. این سناریوها Auth،
Scope، Idempotency، Version conflict، Context، خرابی قبل/بعد Commit، اختلاف
Reconciliation، Duplicate key، Child relation، Delete-in-use و Replication
guard را پوشش می‌دهند. هر دو Screen اکنون به ۳۲ Case وصل‌اند و Gap «تعریف‌نشدن
Golden» صفر است؛ بااین‌حال اجرای Runtime، تأیید مالک و آمادگی پیاده‌سازی همچنان
صفر است. شروع کم‌ریسک مقصد:

1. Search/list/detail فقط‌خواندنی با Scope؛
2. Owner review فیلد/Label/Tab/Lookup؛
3. Review مالک روی ۶۴ Golden case طراحی‌شده؛
4. سپس Commandهای نسخه‌دار و Idempotent Save؛
5. Delete/Merge فقط پس از Dependency و Reconciliation.

## شواهد

- `varanegar_customer_goods_command_contracts_20260827.json`
- `varanegar_customer_ui_label_candidates_20260827.json`
- `varanegar_customer_full_field_metadata_20260827.json`
- `varanegar_customer_layout_bindings_20260827.json`
- `varanegar_goods_ui_label_candidates_20260827.json`
- `varanegar_goods_full_field_metadata_20260827.json`
- `varanegar_goods_layout_bindings_20260827.json`
- `negin_erp_customer_goods_web_screen_contract_candidates_20260827.json`
- `negin_erp_customer_goods_master_golden_cases_20260827.json`

تمام استخراج‌ها Static/Offline/Read-only بودند؛ هیچ فرم یا Command اجرا و هیچ
دادهٔ عملیاتی خوانده/نوشته نشد.
