# مرز سند انبار و توزیع تا خروج کالا

## نتیجهٔ اصلی

در وارانگار، «سند انبار» و «توزیع/خروج» دو فرم CRUD مستقل نیستند. ذخیرهٔ
سند انبار یک Draft ساختاریافته است و تأیید، عدم‌تأیید و ساخت سند برگشتی
Transitionهای جدا هستند. توزیع نیز تا ایجاد/ادغام/حذف خروج، چند Aggregate و
Ledger را درگیر می‌کند. بنابراین ERP نگین باید این عملیات را Commandهای مستقل،
نسخه‌دار، Idempotent و قابل Reconciliation پیاده کند.

## سند انبار: مرز UI و Business

از `FormVocherDataEntry` نه Method مهم با ۱٬۱۲۲ Instruction و ۲۰ Field مورد
استفاده استخراج شد. شواهد ایستا هشت قاعده را نشان می‌دهند:

- کنترل Batch/Serial و تکرار کالا یا بچ؛
- کنترل مقدار مثبت و کالای فعال؛
- Scope سال مالی و انبار؛
- کنترل Cardex/OnHand؛
- Transition تأیید/عدم‌تأیید؛
- Transition ساخت سند برگشتی.

`VocherHdrHandler` دارای سیگنال `DataContext.Commit` است و مسیرهای
`Confirm`، `UnConfirm`، `GenerateRetVocher` و Validationهای Cardex/OnHand را
به DataAccess می‌سپارد. با این حال `TypeSpecRow.SaveCommand` در IL یک Dispatch
جنریک است؛ Implementation واقعی انتخاب‌شده و ترتیب Branchها در Runtime هنوز
اثبات نشده است.

سه Command مقصد فعلاً Candidate هستند:

1. `stock_voucher.save`
2. `stock_voucher.confirm_or_unconfirm`
3. `stock_voucher.generate_return`

این قرارداد Owner-approved یا Runtime-parity-ready نیست.

## توزیع تا خروج: SQL واقعی Clone

چهار Command و پنج SQL anchor بررسی فقط‌خواندنی شد:

- `distribution.create_or_update`
- `distribution.issue_exit`
- `distribution.merge_or_adjust_exit`
- `distribution.remove_exit`

پنج Procedure دارای ۴۹ Parameter و ۶۵ Dependency هستند. همه Mutation token
دارند؛ دو مورد Transaction token و چهار مورد TRY/CATCH دارند. ۱۶ جدول مقصد
پایدار از کاتالوگ حل شد. هیچ پارامتر صریح Idempotency در مسیر Legacy دیده نشد.

مدل Catalog این ۱۶ جدول، ۳۱۶ ستون، ۱۰۵ مشاهدهٔ FK و ۸۷ Trigger فعال را ثبت
می‌کند. گراف Trigger سه‌لایه در سقف ایمنی ۵۰۰ Node متوقف شد و شامل ۱٬۲۱۵ Edge،
۳۶۹ Trigger، ۸۳ Table و ۳۸ Write target حل‌شده است. ۲۳۲ Dependency حل‌نشده و
۱۴۲ Node در Frontier باقی مانده‌اند؛ بنابراین این اعداد حد پایین Blast radius
هستند، نه پوشش کامل.

## اثر مستقیم روی طراحی ERP نگین

- Draft سند، Posting/Confirm، Unconfirm و Return endpoint و مجوز جدا دارند.
- توزیع و خروج نباید با چند Update مستقیم جدول جایگزین شوند؛ Application
  command باید مالک Atomicity، ExpectedVersion، CommandId و Outbox باشد.
- Cardex/OnHand و رابطهٔ سند مبدأ/برگشتی باید بعد از هر Command با Golden
  reconciliation کنترل شود.
- حذف خروج یک Delete ساده نیست؛ سابقهٔ توزیع، سند انبار و روابط فروش باید حفظ
  یا به رویداد جبرانی تبدیل شوند.
- نتیجه‌شکل Procedureها به‌علت metadata failure هنوز قرارداد API نیست و باید
  جداگانه با Snapshot فقط‌خواندنی و دادهٔ غیرحساس بسته شود.

## Screen candidate وب

سند انبار همراه دو فرم فاکتور/برگشت خرید در استخراج کامل UI شامل ۲۸۸ Field،
۲۱۳ Component و ۹۴ Web-input candidate است. ۶۷ اتصال دقیق Layout ثبت شد؛ ۵۹
ورودی Label چیدمانی استاتیک دارند و ۳۵ ورودی فاقد آن‌اند. سه Screen به ۷۷
Golden case مصنوعی موجود متصل شدند، ولی Owner-approved، Implementation-ready و
Runtime-executed هر سه صفر است.

## شواهد ماشین‌خوان

- `varanegar_stock_voucher_command_contract_20260827.json`
- `varanegar_distribution_sql_anchor_contracts_20260827.json`
- `varanegar_distribution_sql_semantics_20260827.json`
- `varanegar_distribution_mutation_source_model_20260827.json`
- `varanegar_distribution_trigger_transitive_graph_20260827.json`
- `negin_erp_stock_supplier_web_screen_contract_candidates_20260827.json`

هیچ Command برنامه، Procedure یا Trigger اجرا نشده، هیچ Row عملیاتی ذخیره نشده
و اتصال Clone با `READ_ONLY`، `can_update=0` و `db_denydatawriter` باقی مانده است.
