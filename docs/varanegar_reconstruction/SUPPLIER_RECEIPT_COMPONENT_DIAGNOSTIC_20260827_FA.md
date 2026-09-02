# تشخیص Component فاکتور خرید و رسید انبار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ هشدار ۵ گروه Receipt-only رد شد، Residual رسمی صفر**

## اصلاح معنا

تحلیل قبلی هر فاکتور را مستقل با تمام اقلام رسیدهای مرتبط مقایسه می‌کرد و پنج
گروه کالا در دو فاکتور را `InventoryOnlyPurchaseLine` می‌دانست. این مدل برای
رابطه‌ی N:M غلط است: یک رسید نوع ۲۰ واقعاً به دو فاکتور وصل است و کالای هر
فاکتور هنگام مقایسه‌ی جداگانه روی فاکتور دیگر Receipt-only دیده می‌شود.

گراف دو بخشی ۳٬۶۸۹ Relation به ۳٬۴۲۵ Component رسید. فقط یک Component چند
فاکتور/رسید مشترک دارد؛ حداکثر دو فاکتور و هفت رسید در Component مشاهده شد.

| سنجش | نتیجه |
|---|---:|
| Receipt-only با مدل غلط per-invoice | ۵ |
| توضیح‌شده توسط فاکتور دیگر همان Component | ۵/۵ |
| Component receipt-only | ۰ |
| Component invoice-only | ۰ |
| Component quantity mismatch | ۰ |
| Component exact `(component, goods)` | ۳۰٬۰۹۶ |

`ICA.usp_ApplySupInvoice` نیز همین معنا را تأیید می‌کند: لیست کامل Invoiceها و
لیست کامل Voucherها را جداگانه بر اساس `GoodsRef` جمع و سپس مقایسه می‌کند؛
اعتبارسنجی per-invoice یا Crosswalk ردیفی ندارد.

## مرجوعی‌های دارای Source hint

هفت گروه کالای مرجوعی که در `SupInvoiceRef` مستقیم پیدا نمی‌شوند، در سه Header
هستند؛ پنج گروه از مسیر `IsNew` و هر هفت کالا در یک فاکتور قدیمی‌تر همان
Supplier/DC/AccYear دیده می‌شوند. بااین‌حال هیچ‌کدام در Component رسیدِ فاکتور
انتخاب‌شده نیستند. پس فاکتور قدیمی فقط Candidate است، نه Crosswalk رسمی.

خروج انبار نوع ۵۵ برای هر هفت گروه دقیق است و IL فرم نیز Item grid را از
`InvVocherRef` پر می‌کند؛ `SupInvoiceRef` فقط Hint اختیاری Source/Price است.
State صحیح `OPTIONAL_SOURCE_ITEM_ABSENT_NOT_AN_INVENTORY_ERROR` است. هر هفت
Price و TotalAmount غیرصفر دارند؛ این Provenance مالی حفظ و از فاکتور قدیمی‌تر
Reprice نمی‌شود.

## شکاف Validator مرجوعی

در ۱۵۶ گروه سندی `(Return,Goods)` مرجوعیِ دارای Source، هفت گروه در قلم فاکتور
منبع وجود ندارند. خود Validator اما همه Headerهایی را که یک `SupInvoiceRef`
مشترک دارند با هم جمع می‌زند؛ Grain آن ۱۱۵ گروه `(SupInvoiceRef,Goods)` است، نه
فقط Header جاری. در گروه‌های تجمیعی Match‌شده، Over-return تعداد/جایزه و اختلاف
مبلغ در حالت برگشت کامل فعلاً صفر است. این صفر بودن Snapshot، Guard اجرایی را
اثبات نمی‌کند.

خوانش فقط‌خواندنی هفت Module SQL نشان داد:

- `SupInvoiceRef` در BeforeSave و Validatorهای قدیمی Header اجباری نیست؛
- `SLE.usp_CheckRetSupInvoice` با `INNER JOIN` فقط Goodsهای Match‌شده را کنترل
  می‌کند و Check مستقلی برای Return Goods غایب از فاکتور منبع ندارد؛
- همان Procedure، ID سند جاری را فقط برای یافتن `SupInvoiceRef` می‌گیرد و اقلام
  تمام مرجوعی‌های دارای همان Source invoice را تجمیع می‌کند؛ این کنترل تجمعی
  باید از کنترل Aggregate جاری و Check صریح Unmatched جدا بماند؛
- سمت Source در متن Procedure بدون `GROUP BY` خوانده می‌شود، اما Unique index
  رسمی `(HdrRef,GoodsRef)` و Duplicate جاری صفر است؛ بنابراین در Schema مستقر
  هر کالا در فاکتور منبع یکتا است. مقصد باید همین Invariant را حفظ یا Source را
  پیش از مقایسه صریحاً تجمیع کند؛
- مسیر SQL جدید `dbo.usp_sdsnet_RetSupInvoice_Save` در INSERT پس از نوشتن
  ردیف‌ها Validator را صدا می‌زند، اما Return code را نمی‌گیرد و پس از آن
  `RAISERROR` نمی‌کند؛ سپس می‌تواند Commit کند؛
- مسیر UPDATE همین Save جدید Validator را اصلاً صدا نمی‌زند؛
- Transaction و Catch/Rollback در Save وجود دارد، اما پیام/Return فعلی به
  Exception تبدیل نشده تا آن Rollback را فعال کند؛
- شرط بررسی Toll نیز `RetSupInvoiceItmRef` را با ID Header مقایسه می‌کند؛ این
  یک شکاف Static قطعی در سطح فیلتر است، نه اثبات وقوع خرابی Toll در دادهٔ جاری.

بنابراین Risk `R-046` باز است: مقصد نباید این Validator را به‌عنوان Guard
Blocking کپی یا قابل‌اعتماد فرض کند. کنترل مقصد باید Union کامل Goodsهای Source
و Return را پیش از Write، یکسان برای INSERT/UPDATE، بررسی کند و خطا را اتمیک و
Blocking برگرداند.

### Permission، تاریخ قطعی و Scope کنترل اجباری

مسیر SDSNET برای INSERT/UPDATE/DELETE به‌ترتیب Access nodeهای
`826001/826002/826003` را از Authorizer عمومی می‌پرسد، اما `AccYear` و `DCRef`
ورودی را به Authorizer نمی‌فرستد. این شاهدِ Permission عملیاتی Legacy است، نه
مجوز Scope مقصد؛ مقصد باید دسترسی Command را با DC/سال مؤثر ترکیب کند.

BeforeSave تاریخ قطعی خرید را با `SysRef=5` و `AccYear` می‌خواند و DC را در آن
Lookup وارد نمی‌کند. همچنین کنترل Goods اجباری به‌جای Temp/current aggregate کل
`ICA.tblRetSupInvoiceItm` را بدون `HdrRef` می‌خواند؛ بنابراین یک ردیف خراب فرضی
می‌تواند همه Saveها را متوقف کند. Snapshot فعلی صفر Goods تهی/صفر دارد، پس این
Blast radius فعلاً رخ نداده، ولی مقصد باید Validation را فقط روی Aggregate جاری
اجرا کند.

### تفاوت مسیر Desktop

IL مرتب ۱۲۴ Instruction از `FormRetSupInvoiceDataEntry.SaveCommand`، با Hash
دقیق Assembly نسبت به Inventory، مسیر دیگری را ثابت کرد:

1. `TypeSpecRow.SaveCommand`؛
2. بررسی اعتبار اولیه؛
3. `RetSupInvoiceHdrHandler.CheckRetSupInvoice`؛
4. `String.IsNullOrWhiteSpace` روی پیام؛
5. برای پیام غیرخالی: ساخت `ValidationFailure`، Dispose و خروج قبل از Commit؛
6. برای پیام خالی: `DataContext.Commit`.

پس Desktop خروجی Validator را Blocking می‌کند و نباید با مسیر SDSNET یکی گرفته
شود. بااین‌حال هر دو مسیر از همان Validator دارای `INNER JOIN` استفاده می‌کنند؛
بنابراین هفت Goods بدون Match حتی در Desktop هم به Check تعداد وارد نمی‌شوند.

سه Method دیگر علت را روشن می‌کنند: `FillRetSupInvoiceItmGrid` با
`InvVocherRef` اقلام را می‌خواند؛ تغییر سند انبار انتخاب Source invoice را پاک
می‌کند؛ تغییر Source invoice فقط اقلام آن را می‌خواند، برای Goods Match‌شده Price
را کپی و برای Unmatched در Grid صفر می‌گذارد. دادهٔ جاریِ هفت مورد Price غیرصفر
دارد، پس منشأ دقیق قیمت تاریخی از Snapshot/IL ثابت نیست و نباید از فاکتور قبلی
حدس زده شود.

هر پنج گروه مسیر جدید و هر دو گروه Legacy Price غیرصفر دارند. Event
`GridList_ValidatingEditor` ستون‌های `Price` و `Amount` را فقط از نظر Numeric
بودن می‌سنجد؛ بنابراین فرم امکان نگهداری/ویرایش مقدار را دارد، ولی Snapshot
Actor و منشأ محاسبهٔ این هفت قیمت را ثابت نمی‌کند. نتیجه فقط حفظ Provenance است،
نه برچسب «قیمت دستی».

Catalog سه Writer رسمی را نیز جدا کرد: مسیر Legacy/Desktop پارامتر `Price` را
می‌پذیرد و ذخیره می‌کند؛ Save مسیر SDSNET قیمت و مبلغ را از Temp payload کپی
می‌کند؛ و `dbo.usp_Convert_RetSupInvoice2`، `UnitPrice` ورودی Import را در Price
می‌گذارد و Amount را از `Qty×UnitPrice` می‌سازد. Header جاری Marker معتبرِ مسیر
ایجاد ندارد، پس هیچ‌یک علت تاریخی قطعی هفت مورد نیست و برچسب Import/Manual ممنوع
می‌ماند.

Binding نیز Name-candidate نیست و تا SQL دقیق اثبات شد:

`FormRetSupInvoiceDataEntry.SaveCommand → RetSupInvoiceHdrHandler.CheckRetSupInvoice`
`→ RetSupInvoiceHdrAdapter.CheckRetSupInvoice → SLE.usp_CheckRetSupInvoice`.

Method لایه Business شش Instruction و Adapter هفده Instruction دارد؛ Adapter
نام دقیق Procedure را به `DataContext.Execute` می‌دهد و پیام `EM` را برمی‌گرداند.

### شاهد عملیاتی سه ماه اخیر

در پنجرهٔ `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` هر ۵۰ Header مرجوعی خرید از مسیر
`IsNew=1` آمده‌اند و در مجموع ۳۹۳ قلم دارند؛ Header مسیر Legacy در این پنجره
صفر است. فقط یک Header `SupInvoiceRef` دارد و در همین نمونه پنج گروه کالا در
قلم فاکتور منبع پیدا نمی‌شوند. بنابراین ضعف `INNER JOIN` و نابرابری مسیر
INSERT/UPDATE فقط یک مسئلهٔ تاریخی نیست و روی مسیر جاریِ عملیاتی نیز مصداق
داده‌ای دارد. در مقابل، تعداد Explicit TollRef قدیمی در این پنجره صفر است؛
پس ۲۰ مورد TollRef قابل‌بازیابیِ موجود به دادهٔ Legacy محدودند و نباید به مسیر
جدید نسبت تاریخی داده شوند.

## TollRef قدیمی، نه Toll گم‌شده

در ۴٬۶۰۱ ردیف Item×Toll، تعداد ۲۰ ردیف از یک Header دارای
`RetSupInvoiceTollsRef` هستند که ID آن دیگر در جدول Toll Header وجود ندارد و
Validator فعلی هر ۲۰ را به‌علت Scope اشتباه از دست می‌دهد. اما این ۲۰ ردیف
«عامل مالی گم‌شده» نیستند:

- هر ۲۰ با `(ReturnHeader, TollRef)` دقیقاً یک Toll جاری پیدا می‌کنند؛
- Ambiguous و Unresolved هر دو صفرند؛
- View رسمی `ICA.TblRetSupInvoiceItmTolls` عمداً Ref ذخیره‌شده را کنار می‌گذارد
  و با Header+TollRef Join می‌کند؛ هر ۲۰ ردیف در آن قابل مشاهده‌اند؛
- FK رسمی فقط از ItemXToll به Item وجود دارد و `RetSupInvoiceTollsRef` FK ندارد.

در SQL مسیر SDSNET یک Defect مستقل هم هست: شاخه UPDATE برای درج Allocation جدید
`SI.HdrRef=@HdrId` را به‌کار می‌برد، درحالی‌که `@HdrId` فقط در INSERT مقدار
می‌گیرد، و Refهای موجود را نیز Retarget نمی‌کند. این مسیر می‌تواند Ref قدیمی
بسازد، اما علت تاریخی ۲۰ مورد فعلی اثبات‌شده نیست: Header مبتلا `IsNew=0` است
و در گروه مسیر SDSNET جدید قرار ندارد. پس این کد فقط Root-cause candidate برای
رخدادهای مشابه آینده است، نه انتساب علت به دادهٔ جاری.

State مهاجرتی این موارد
`STALE_EXPLICIT_TOLL_REF_RESOLVED_BY_HEADER_TOLL_CODE` است: Ref خام برای
Provenance حفظ، Effective mapping از قاعدهٔ سازگاری رسمی گرفته و فقط Match
غایب/چندگانه قرنطینه می‌شود. حذف Toll یا ساخت Allocation مصنوعی ممنوع است.

## قرارداد مقصد

- Relation Header-level N:M عیناً حفظ شود؛ Unique اجباری روی یکی از دو Ref ممنوع؛
- Reconciliation در سطح Connected component و Goods انجام شود؛
- فقط Residual پس از فرمول کامل Component قرنطینه شود؛
- برای پنج مورد قبلی Item مالی مصنوعی نساز و Receipt item را حذف نکن؛
- Price application فقط با Command نسخه‌دار، اتمیک و Idempotent انجام شود؛
- نبود Line allocation رسمی با Allocation حدسی جایگزین نشود.
- Validation مرجوعی باید پیش از Persistence و روی Union دو مجموعه Goods اجرا شود؛
- نتیجهٔ Validator باید Exception/Domain error مسدودکننده باشد، نه پیام نادیده‌گرفته‌شده.

## ایمنی و محدودیت

Clone `READ_ONLY` و حساب `UPDATE=0` بود. ID و Quantity فقط در حافظه برای ساخت
Component پردازش و هیچ مقدار خامی ذخیره نشد. Procedure/Form اجرا و داده‌ای
تغییر داده نشد. Snapshot نیت کسب‌وکاری ایجاد رسید مشترک را ثابت نمی‌کند. هیچ
Save یا Validator اجرا نشد؛ نتیجهٔ Non-blocking از Control flow متن Procedure
استنتاج مستقیم شده و رفتار UI/Client تاریخی جداگانه اثبات نشده است.

## بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_supplier_receipt_component_diagnostic_contract.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_supplier_receipt_component_diagnostic_contract_20260827.json
```
