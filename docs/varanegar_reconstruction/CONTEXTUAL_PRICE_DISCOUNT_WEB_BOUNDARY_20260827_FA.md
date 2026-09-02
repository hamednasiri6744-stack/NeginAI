# مرز قیمت زمینه‌ای و Ruleهای تخفیف/جایزه

## نتیجهٔ اصلی

`FormCPrice` و `FormDiscount` دو CRUD ساده برای «قیمت» و «تخفیف» نیستند. قرارداد
ایستا ۵۶ Method منتخب، ۱۳٬۴۳۳ Instruction، ۱۱۹ Field reference، چهارده Rule
signal و دو Commit signal دارد. Scope، اولویت، Effective state، بستن Rule، شرط،
چیدمان، جایزه و بسته بخشی از قرارداد هستند.

## قیمت زمینه‌ای

قیمت قراردادی/زمینه‌ای بر اساس ترکیبی از Customer و نوع مشتری، State/County،
DC، BuyType، Currency، Batch/BatchGroup، Package/Unit و Priority انتخاب می‌شود.
Copy، Priority تغییرپذیر، Close اطلاعات و Refresh پس از Save مسیرهای جدا دارند.
بنابراین مدل مقصد باید Version و Effective window و Explain trace داشته باشد؛
یک جدول با ستون‌های nullable و «آخرین ردیف» کافی نیست.

## تخفیف و جایزه

Rule تخفیف به Customer/CustomerGroup، Goods/GoodsGroup/DynamicGroup، Order و
OrderType، Arrange، Condition DSL و GroupOperator، Prize/GoodsPackage، Prevent
Sale و Active/Future/Inactive/Close state وابسته است. Copy/Close/Delete و
Prize insert نیز باید Commandهای نسخه‌دار یا Transitionهای صریح باشند.

این شواهد ترتیب واقعی اولویت، Qualification، محاسبه، Rounding، تاریخ مؤثر یا
نتیجه Runtime را ثابت نمی‌کنند.

## Screen candidate مقصد

دو فرم دارای ۲۳۶ Field حل‌شده، ۱۱۶ Component و چهل Web-input هستند. ۴۵ Layout
binding ثبت شد؛ ۳۲ Input Label چیدمانی دارد و هشت Input فاقد متن استاتیک قابل
اتکا است. ۳۱ Input در Methodهای منتخب Reference شده‌اند.

دو Screen در مجموع به ۶۴ Golden case مصنوعی طراحی‌شده برای
Save/Copy/Priority/Close/Delete/Retry/Fault وصل‌اند و Gap تعریف Golden صفر شد.
Owner-approved، Implementation-ready و Runtime-Golden-executed هنوز صفر است؛
پس Write مسدود می‌ماند. ترتیب صحیح ساخت:

1. Read-only Rule list/detail و Explain «چرا این قیمت/تخفیف اعمال شد»؛
2. Owner review روی Scope، Priority، تاریخ، Rounding و Close/Inactive؛
3. مدل Versioned rule + relation tables + deterministic allocator؛
4. Goldenهای qualification/precedence/overlap/copy/close/delete/retry/fault؛
5. Write فقط روی Target test DB و پس از تطبیق قیمت/تخفیف/جایزه.

## شواهد

- `varanegar_pricing_rule_command_contracts_20260827.json`
- `varanegar_pricing_rule_ui_labels_20260827.json`
- `varanegar_pricing_rule_full_fields_20260827.json`
- `varanegar_pricing_rule_layout_20260827.json`
- `negin_erp_pricing_rule_web_screen_contract_candidates_20260827.json`
- Risk `R-040`

Builderهای اختصاصی:

- `build_varanegar_pricing_rule_command_contracts.py`
- `build_negin_erp_pricing_rule_web_screen_contract_candidates.py`

تمام استخراج‌ها Static/Offline/Read-only بودند؛ Assembly اجرا نشد، UI لمس نشد،
هیچ Rule/Command/Procedure اجرا و هیچ دادهٔ تجاری خوانده یا نوشته نشد.
