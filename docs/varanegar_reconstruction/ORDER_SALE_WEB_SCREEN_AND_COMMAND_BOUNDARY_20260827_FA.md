# مرز Screen وب و Command درخواست تا فروش و برگشت

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **شاهد استاتیک/کاتالوگ PASS؛ پیاده‌سازی و Runtime parity هنوز صفر**

## هدف و مرز ایمنی

سه فرم مرکزی زیر بدون Load/Execute کردن Assembly و بدون هیچ UI Action یا Command
کسب‌وکاری بررسی شدند:

- `FormOrderDataEntry`؛ عنوان استاتیک محتمل «درخواست مشتري»؛
- `FormSaleDataEntry`؛ عنوان «حواله/فاکتور فروش جدید»؛
- `FormRetSaleDataEntry`؛ عنوان «برگشت فاکتور».

عنوان‌ها از آخرین `Control.set_Text` فارسیِ بدون Target-field در
`InitializeComponent` به‌صورت Heuristic آمده‌اند و Runtime title قطعی نیستند.
اتصال SQL فقط به Clone `READ_ONLY` با `can_update=0` و `db_denydatawriter` بود؛
Procedure/Trigger اجرا نشد و Definition یا مقدار ردیف تجاری ذخیره نشد.

## مرز Save، Validate و Permission

از شش مرز مشترک `CreateNewDataObject / ValidateCurrentData / ValidateData /
SaveCommand / UIOnPostCommandExecute / ApplyUserPermission` و مرز Editability
درخواست، ۱۸ Method با ۱٬۷۵۴ Instruction انتخاب شد. ۲۹ Field، ۲۵ فراخوانی
Business یکتا، ده Getter تنظیم و سیزده Rule signal ثبت شد. UI هیچ SQL مستقیم
ندارد؛ دو Save دارای `DataContext.Commit` در UI هستند:

- درخواست: `TypeSpecRow.SaveCommand`، شماره‌گذاری، اعتبار درخواست، Batch،
  AfterSave و در صورت Setting تبدیل مستقیم به فروش؛ Commit در UI؛
- تبدیل درخواست به فروش: `SaleHandler.OrderToSaleSaveCommand`؛ Commit در Handler،
  نه UI؛
- برگشت: `RetSaleHandler.SaveCommand/SaveCommandFromPeygiri/AfterSaveRetSale`؛
  Commit هم در UI و هم در شاخهٔ پیگیری Handler دیده می‌شود.

وجود Commit در چند Layer به معنی Transaction اتمیک انتها‌به‌انتها نیست. مالک
Transaction مقصد باید دقیقاً یکی باشد و UI فقط Command نسخه‌دار/Idempotent بفرستد.
`ApplyUserPermission` در فرم درخواست و برگشت Override شده، ولی در فرم فروش Override
محلی ندارد؛ این فقط شاهد احتمال Permission ارثی است، نه نبود مجوز.

سیگنال‌های قاعده شامل اعتبار مشتری/فروشنده/سرپرست، موجودی، رزرو، قیمت عادی و
قراردادی، ردیف تکراری، Batch/Serial، منع فروش کالا/مشتری، مهلت پرداخت، تبدیل
مستقیم، EVC/Prize، Confirm/Cancel و قواعد منبع/مانده/مجوز برگشت است. ترتیب Branch،
مقدار Effective Setting و پیام دقیق هنوز اثبات نشده‌اند.

## قرارداد Field و Layout برای وب

Prefix-filter قبلی فقط ۴۳ Field این سه فرم را می‌دید. Parse کامل Type metadata
هر ۴۲۳ Field را با Failure صفر حل کرد:

- ۳۴۲ UI-component candidate؛
- ۱۴۰ Web-input candidate؛
- ۱۸۴ جزء Layout، ۹۸ Editor، ۳۹ Lookup، سیزده Command و سه Boolean؛
- ۸۱ State/Infrastructure یا Type حل‌نشده از نظر نقش UI، نه Type CLR؛
- Runtime binding، Requiredness، Default، Mask، Visibility و Authorization صفر.

از فراخوانی دقیق `LayoutItem.set_Control(input)` تعداد ۱۴۰ Pair بدون Shape failure
به دست آمد. ۱۲۲ Pair مربوط به Web input و ۱۱۳ مورد دارای Label استاتیک‌اند؛ هیچ
Control با چند Layout binding دیده نشد. این Pairing از حدس نام قوی‌تر است، ولی
Dynamic relayout/visibility و متن Resource-backed را ثابت نمی‌کند. ۲۷ Input در
Screen contract هنوز Label استاتیک قابل استفاده ندارند.

سه Screen contract نامزد وب، ۱۴۰ Input، سیزده Command control، سیزده Rule signal
و Commandهای تثبیت‌شدهٔ قبلی `order.save`، `order.convert_to_sale` و
`sales_return.save` را به ۴۸ Golden case مصنوعی (۱۶ مورد برای هر Command) متصل
می‌کند. هر ۴۸ مورد فقط طراحی Test هستند؛ Runtime اجرا، Owner approval و
Implementation-ready هر سه صفر است.

## گراف Business و DataAccess

از ۳۰ Edge مستقیم Form/Method به Business، گراف محدود دو لایه به موارد زیر رسید:

- ۵۳ Method node در Business و ۸۶ Dependency edge؛
- ۲۸ Method node در DataAccess؛
- دو Business method و دو DataAccess method دارای Transaction/Persistence signal؛
- هفت SQL object anchor بدون Hash mismatch یا Member حل‌نشده.

دو مرز خاص قابل مشاهده‌اند: `SaleHandler.OrderToSaleSaveCommand` و
`RetSaleHandler.SaveCommandFromPeygiri` خودشان Commit دارند؛
`EVCAdapter.CreateEVCSqlTempTable` Transaction مستقل و `ExecuteNonQuery` دارد؛
`OrderAdapter.CreateSaleByOrder` نیز Commit ثبت کرده است. این پراکندگی باید با
Fault injection و اثبات مالکیت Transaction بسته شود.

## هفت Procedure و اثرهای قابل حل

هفت Anchor به هفت Stored procedure یکتا در Clone رسیدند: ۹۵ Parameter و ۱۱۴
Dependency. ردپای Lexical آن‌ها ۱۳۳ Select، ۵۲ Execute، هشت Insert، هفت Update،
سه Delete، هفت Transaction token و دو Dynamic-SQL token دارد. فقط دو Procedure
Mutation token دارند:

- `SLE.usp_CreateSaleByOrder` → `SLE.tblSaleHdr`, `SLE.tblSaleItm`؛
- `sle.usp_sdsnet_CreateSaleByOrder` → هشت Target قابل حل شامل Order header/item
  detail، Sale header/item detail، Batch، Payment، ReservedPrize و Timing.

سه Procedure کنترل اعتبار/حد مشتری و دو Procedure کنترل برگشت Mutation حل‌شده
ندارند. Metadata نتیجهٔ اول هر هفت Procedure با `SYNTAX` توصیف نشد؛ بنابراین
Result shape/parity صفر و یک Gap صریح است، نه نشانهٔ بدون خروجی بودن.

## Targetهای Mutation و Trigger cascade

نه جدول حل‌شده دارای ۲۶۵ ستون، هشت ستون PK، ۱۱۵ مشاهده FK، ۷۳ Trigger فعال و
۲٬۰۸۸ مشاهدهٔ Referencing module هستند. گراف Transitive سه‌لایهٔ ۷۳ Trigger در
سقف ۵۰۰ Node متوقف شد:

- ۱٬۰۱۳ Edge، ۳۸۴ Trigger، ۹۰ Table و ۲۶ Module دیگر؛
- ۳۱۵ Mutation token و ۳۵ Write target حل‌شده؛
- ۱۴۲ Module دارای Transaction signal؛
- ۲۰۷ Dependency حل‌نشده و ۱۸۴ Node در Frontier گسترش‌نیافته؛
- بیشترین Reach یک Root برابر ۱۷۵ Node و ۲۱ Write target است.

این گراف «اجرای حتمی همه اثرها» نیست و به‌دلیل سقف ۵۰۰ Node عمداً ناقص است؛ اما
ثابت می‌کند Order-to-sale را نمی‌توان با CRUD هدر/ردیف جایگزین کرد. Risk بحرانی
`R-033` برای همین Failure mode ثبت شد. قبل از فعال شدن Commandهای فروش، هر ۷۳
Trigger و Frontier ناقص باید `retain/replace/retire`، Owner و آزمون Reconciliation
داشته باشد.

## نتیجه برای ERP شخصی نگین

1. UI وب از Screen contract شروع می‌شود، ولی Requiredness/Binding و Lookupها باید
   با Owner و Runtime Golden بسته شوند.
2. `order.save`، `order.convert_to_sale` و `sales_return.save` سه Command مستقل‌اند؛
   UI یا API حق نوشتن مستقیم جدول ندارد.
3. قیمت، اعتبار، موجودی، رزرو، جایزه، Batch/Serial و تبدیل/برگشت باید Invariant یا
   سرویس دامنهٔ صریح باشند، نه Event handler پنهان در فرم.
4. یک Transaction owner محلی، Outbox، `command_id + payload fingerprint`،
   `expected_version`، Audit و Reconciliation شرط فعال‌سازی‌اند.
5. تا زمانی که ۴۸ Golden case روی Target isolated harness اجرا نشده و Trigger
   disposition کامل نیست، این سه Screen فقط نامزد Review هستند.

## Artifactها و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_order_sale_entry_command_contracts_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_order_sale_ui_label_candidates_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_order_sale_full_field_metadata_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_order_sale_layout_bindings_20260827.json`
- `artifacts/varanegar_analysis/ui/negin_erp_order_sale_web_screen_contract_candidates_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_order_sale_command_dependency_graph_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_order_sale_sql_semantics_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_order_sale_mutation_source_model_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_order_sale_trigger_transitive_graph_20260827.json`
- `scripts/windows/build_varanegar_order_sale_entry_command_contracts.py`
- `scripts/windows/extract_varanegar_order_sale_ui_label_candidates.py`
- `scripts/windows/extract_varanegar_order_sale_full_field_metadata.py`
- `scripts/windows/extract_varanegar_order_sale_layout_bindings.py`
- `scripts/windows/build_negin_erp_order_sale_web_screen_contract_candidates.py`
- `scripts/windows/extract_varanegar_order_sale_command_dependency_graph.py`
- `scripts/sql/extract_varanegar_order_sale_sql_semantics.py`
- `scripts/sql/extract_varanegar_order_sale_mutation_source_model.py`
- `scripts/sql/extract_varanegar_treasury_trigger_transitive_graph.py` با Artifact identity فروش.

فرمان‌های دقیق همه ورودی/خروجی‌ها در Scriptها ثبت شده‌اند؛ بازتولید باید فقط روی
Share Hash-verified و Clone فقط‌خواندنی انجام شود. اجرای Runtime business command
یا Procedure برای این بازتولید ممنوع است.
