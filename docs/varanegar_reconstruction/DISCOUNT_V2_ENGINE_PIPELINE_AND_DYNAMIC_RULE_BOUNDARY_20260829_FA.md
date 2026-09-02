# مرز موتور Discount V2 و قواعد SQL پویا — ۱۴۰۵/۰۶/۰۷

## نتیجه قطعی

موتور تخفیف جدید فقط بخشی از `VN.SDS.Sales.Business.dll` نیست. سه اسمبلی مستقل
در بسته اجرایی فعلی وجود دارند و با SHA-256 ثبت شده‌اند:

| اسمبلی | حجم | Type | Method |
|---|---:|---:|---:|
| `DiscountV2.dll` | ۱٬۱۱۹٬۷۴۴ | ۶۹۹ | ۷٬۱۰۳ |
| `DicountV2SqlServer.dll` | ۱۰٬۷۵۲ | ۷ | ۲۶ |
| `DicountV2SqlServerSDS.dll` | ۱۱٬۲۶۴ | ۷ | ۲۷ |

در مجموع ۷۱۳ Type و ۷٬۱۵۶ Method وجود دارد. ۲۲ متد مرزی و ۳٬۷۴۳ دستور IL
به‌صورت استاتیک بررسی شدند؛ هیچ اسمبلی Load یا اجرا نشد.

## مسیر واقعی محاسبه

ورودی عمومی `RuleEngine.DiscountCalculatorHandler.Calculate` مستقیماً به
`DoEvcHandler.Execute` می‌رسد. ترتیب مشاهده‌شده در موتور اصلی چنین است:

1. استخراج مرجع سفارش؛
2. اعتبارسنجی EVC؛
3. محاسبه مهلت پرداخت؛
4. به‌روزرسانی قیمت؛
5. اجرای موتور جدول قوانین؛
6. اجرای Special Value؛
7. اجرای دوباره موتور جدول قوانین در ادامه مسیر.

داخل مرحله جدول قوانین، ترتیب اصلی این است:

1. پرکردن Rule/Statuteهای قابل بررسی؛
2. حذف قوانین نامعتبر؛
3. محاسبه مقادیر اضافی و اولویت‌ها؛
4. اعمال قانون روی اقلام؛
5. اعمال قانون روی کل EVC، شامل تخفیف دوره‌ای و جایزه کارتنی؛
6. تخفیف امانی؛
7. کنترل اعتبار جایزه پیش‌فروش.

مرحله انتخاب Rule نیز فقط یک Query ساده نیست: ابتدا Discountها پر می‌شوند، با
اطلاعات EVC فیلتر می‌شوند، `EvcItemFull` ساخته می‌شود، سپس Advanced Condition
اعمال و چند دور پاک‌سازی و نهایی‌سازی انجام می‌شود.

## قرارداد Query ورودی

این نتیجه به Artifact قبلی QueryHelper متصل است. Query مربوط به
`DISCOUNT_After_65` یک Template به طول ۶٬۱۳۳ کاراکتر با سه Slot قالب‌بندی و
هشت مرجع جدولی دارد؛ از جمله `SLE.tblDiscount`، شرط‌ها، کالاهای مشمول، فهرست
جوایز و آثار فروش قبلی. خود Template خواندنی است، اما فیلد `SqlCondition` را
نیز همراه Rule وارد CalcData می‌کند.

## اجرای `SqlCondition`

هر دو Helper سرور، مقدار `TypeSpecRow.SqlCondition` را می‌خوانند، Quote را با
`String.Replace` Escape می‌کنند، متن را داخل یک متغیر `nvarchar(max)` قرار
می‌دهند و آن را با `sp_executesql` و پارامترهای `@EvcId` و `@Result` اجرا
می‌کنند. این یعنی `SqlCondition` صرفاً Metadata نمایشی نیست؛ بخشی از برنامه
اجرایی موتور است.

نسخه SDS پیش از اجرا چهار Replace مرتب دارد:

1. `EvcItemFull → #EvcItemFull`
2. `sle.tblEvc → #tblTempEvc`
3. `sle.tblEvcItem → #tblTempEvcItemStatutes`
4. `sle.tblEvcItemStatutes → #EvcItemFull`

ترتیب مهم است: Replace عمومی شماره ۲ پیشوند نام‌های ۳ و ۴ را هم عوض می‌کند؛ پس
برای متن lowercase دقیق، Replaceهای تخصصی بعدی دیگر match نمی‌شوند. Corpus فعلی
هیچ نام پایه `sle.tblEvc*` ندارد: ۷۹۳ Rule از قبل `#tblTempEvc` و ۵۲ Rule
`EvcItemFull` دارند. بنابراین در داده فعلی عملاً Rewrite اول مصرف می‌شود و مشکل
ترتیب به‌عنوان compatibility trap برای Rule آینده ثبت می‌شود، نه رخداد جاری.

Binding مسیر منتخب نیز حل شد: هر دو متد `InitialCalcData` و
`ExtractCalcDataFromDB` ابتدا `DicountV2SqlServerSDS.AdvanceConditionSqlHelper`
را می‌سازند و بلافاصله آن را به Constructor `CalcData` می‌دهند. در این دو مسیر
هیچ Constructor از Helper غیر-SDS دیده نشد. بنابراین Rewrite Temp فقط قابلیت
موجود در DLL نیست؛ پیاده‌سازی تزریق‌شدهٔ مسیر order-to-sale منتخب است.

مرز Performance نیز استاتیک ثابت شد: `FillSimpleEvcSharpSummary` یک بار
`ValidateAdvanceCondition` را صدا می‌زند، اما Helper نوع SDS داخل فهرست Ruleهای
کاندید `GetEnumerator/MoveNext` دارد و در هر دور یک `DataContext.GetValue` شامل
`sp_executesql` اجرا می‌کند. در شاخه Result=true نیز یک `AllRawEntity` و یک
`Execute` برای Include staging دارد. بنابراین تعداد Query پویا به تعداد Ruleهای
کاندید وابسته است؛ ۸۴۵ Rule کل یا ۵۷ Rule effective امروز به‌تنهایی تعداد Query
یک سفارش را ثابت نمی‌کند و Runtime telemetry لازم است.

این Loop در مسیر منتخب صرفاً reachable و خاموش نیست: Constructor یک‌پارامتری
`CalcData(advanceConditionHelper)` مقدار `BackOfficeType=1` را ثابت می‌گذارد؛
همان مسیر EVC این Constructor را صدا می‌زند و Gate در
`FillSimpleEvcSharpSummary` دقیقاً مقدار ۱ را برای رفتن به
`ValidateAdvanceCondition` می‌پذیرد. پس با وجود Rule کاندید دارای شرط، validation
پویا در مسیر منتخب فعال است.

Constructor خود Helper نوع SDS نیز `context` را در Base interface ذخیره می‌کند.
`ValidateAdvanceCondition` اگر این context موجود باشد همان را انتخاب می‌کند و
فقط برای fallback یک `DataContext(1)`/context پیش‌فرض می‌سازد. در مسیر منتخب،
EVC همان DataContext بدون Transaction را به Helper داده است؛ بنابراین Queryهای
per-candidate روی یک Context/Connection ولی بدون transaction snapshot واحد اجرا
می‌شوند. RCSI فقط هر statement را جداگانه پایدار می‌کند.

## Snapshot امن دیتابیس

سه ستون هم‌نام در Catalog پیدا شد، ولی فقط منبع اصلی موتور فعلاً داده دارد:

| منبع | کل ردیف | شرط غیرخالی | فعال و غیرخالی |
|---|---:|---:|---:|
| `SLE.tblDiscount` | ۵٬۰۹۸ | ۸۴۵ | ۶۲۶ |
| `NGT.Discounts` | ۰ | ۰ | ۰ |
| `SLE.tblSaleVocherDiscount` | ۰ | ۰ | ۰ |

۸۴۵ نمونه فقط ۴۴ Hash متمایز دارند؛ یعنی اکثر شرط‌ها از تعداد کمی الگوی
تکرارشونده ساخته شده‌اند. طول شرط‌ها ۲۰ تا ۱٬۵۰۳ کاراکتر و میانگین آن‌ها
۵۷۸٫۸ است. ۸۴۴ شرط الگوی `SELECT`، ۸۴۳ شرط `@EvcId`، ۸۴۴ شرط `@Result` و
۷۹۳ شرط ارجاع Temp EVC دارند.

اسکن واژگانی فعلی هیچ `INSERT/UPDATE/DELETE/MERGE`، DDL/Permission،
`xp_cmdshell`، `OPENROWSET`، `OPENQUERY` یا `WAITFOR` پیدا نکرد. این شاهد خوبی
برای Snapshot فعلی است، اما مجوز اجرای SQL دلخواه در معماری مقصد نیست: موتور
عمداً متن Rule را اجرا می‌کند و تغییر آینده یا دسترسی ویرایش Rule می‌تواند مرز
اعتماد را عوض کند.

متن خام شرط‌ها و شناسه Ruleها در Artifact ذخیره نشده‌اند؛ فقط شمارش، طول،
Fingerprint مجموعه و شکل واژگانی نگهداری شده است. اتصال با حساب
`Negin_Report_ReadOnly` به Clone `READ_ONLY` و دارای deny-write انجام شد.

## خانواده‌های ساختاری و استفاده سه‌ماهه

۴۴ Hash به پروفایل ساختاری بدون Literal تبدیل شدند. Vocabulary جمعی آن‌ها چهار
شیء پایدار (`GNR.tblCust`، `SLE.tblDiscount`، `SLE.tblDisSale` و
`SLE.tblOrderHdr`)، یک Temp اصلی (`#tblTempEvc`) و ۲۳ نام ستون معتبر Catalog را
پوشش می‌دهد. ستون‌ها ابعادی مانند مشتری/عامل، نوع تخفیف، سفارش، پرداخت، برند،
سازنده، مسیر، انبار و مقدار کل را نشان می‌دهند. این Inventory معنای رسمی هر Rule
را ثابت نمی‌کند، ولی دامنه DSL مقصد را از حدس عمومی به Vocabulary واقعی نزدیک
می‌کند.

استخراج مستقل `FROM/JOIN` شش Object shape را نشان داد و ابهام دو خانوادهٔ فعال
تاریخی را کمتر کرد: هر دو روی `EvcItemFull` Query می‌زنند؛ خانوادهٔ ۴۴۸ اثری فقط
ستون `ID` و خانوادهٔ ۲۳ اثری `ID` و `BrandName` را لمس می‌کند. هر دو
`@EvcId/@Result`، یک `EXISTS` و یک Subquery دارند. مقدار مقایسه و معنای رسمی Rule
عمداً استخراج نشده، پس فقط می‌توان گفت خانواده دوم brand-sensitive است، نه این‌که
کدام برند یا تصمیم کسب‌وکاری را هدف می‌گیرد.

پروفایل Aggregate دو خوشه معماری روشن می‌کند:

- ۷۹۳ Rule در ۹ خانواده هم‌زمان `#tblTempEvc`، `tblDiscount`، `tblDisSale` و
  `tblOrderHdr` را می‌خوانند. ۴۱ Rule این خوشه امروز date-effective است، ولی در
  پنجره منتخب اثر retained در `tblDisSale` ندارد. پارامترها و ستون‌های غالب
  `CustRef/DisRef/DiscountTypeRef/EvcType/HdrRef/RefId/Path` هستند؛ این شواهد با
  خانواده «سابقه مصرف/محدودیت اجرای Rule» سازگار است، اما برچسب رسمی هنوز لازم است.
- ۵۲ Rule در ۳۵ خانواده روی `EvcItemFull` هستند؛ ۱۶ Rule امروز date-effective
  است و هر سه Rule دارای اثر/تمام ۴۷۱ اثر سه‌ماهه در همین خوشه‌اند. این خوشه
  Predicate سبد/اقلام جاری است.
- یک Rule مستقل `GNR.tblCust` را می‌خواند و در پنجره اثر retained ندارد.

پس DSL مقصد حداقل باید دو Context صریح و جدا داشته باشد:
`CurrentBasketPredicate` و `HistoricalRuleUsagePredicate`. دسترسی تاریخی نباید
به‌صورت SQL آزاد داخل Predicate سبد پنهان شود؛ Query budget، snapshot و محدودیت
زمانی هر Context باید جدا تعریف شود.

در بازه تجاری `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱`:

| شاهد | مقدار |
|---|---:|
| کل اثرهای `tblDisSale` | ۳۰۰٬۳۶۱ |
| کل Rule مصرف‌شده | ۷۰۴ |
| خانواده Advanced دارای اثر | ۲ از ۴۴ |
| Rule Advanced دارای اثر | ۳ از ۸۴۵ |
| اثر Advanced | ۴۷۱ ردیف روی ۳۸ فروش |
| سهم Advanced از اثرها | ۰٫۱۵۶۸٪ |
| Discount / Addition در اثر Advanced | ۴۷۱ / ۰ |

از ۶۲۶ Rule دارای Flag فعال، فقط ۵۷ Rule در تاریخ فعلی داخل بازه Start/End هستند
و این ۵۷ Rule به ۱۶ خانواده تعلق دارند. همچنین ۲۶۷ Rule از ۳۶ خانواده از نظر
تاریخی با بازه سه‌ماهه هم‌پوشانی تاریخ دارند؛ ولی چون `IsActive` فعلی وضعیت گذشته
را بازسازی نمی‌کند، این هم‌پوشانی اثبات فعال‌بودن تاریخی نیست.

یکی از سه Rule مصرف‌شده در Snapshot فعلی active نیست. این تناقض نیست: Flag فعلی
پس از بازه تاریخی مشاهده شده و نباید برای تفسیر نتیجه گذشته استفاده شود.

Log وضعیت این مورد را دقیق‌تر کرد. `tblDiscount_DeactivationLog` در کل ۱٬۳۱۳
ردیف برای ۱٬۳۱۳ Rule دارد؛ تمام رخدادها `IsActiveChangedTo=0` هستند و هیچ رخداد
فعال‌سازی ندارد. در Advanced ruleها، ۲۱۸ غیرفعال‌سازی پیش از پنجره، دو مورد داخل
پنجره و صفر مورد پس از آن ثبت شده است. یک Rule که امروز فعال است نیز Log
غیرفعال‌سازی قدیمی دارد؛ پس فعال‌سازی مجدد در این Log کامل ثبت نمی‌شود و تاریخچه
کامل state machine از آن قابل بازسازی نیست.

با این Caveat، سه Rule دارای اثر روشن‌تر شدند: دو Rule خانواده `ID` امروز نیز
فعال‌اند و ۴۴۸ اثر دارند؛ Rule خانواده `ID/BrandName` داخل همان پنجره غیرفعال
شده و پیش از آن ۲۳ اثر retained ساخته است. بنابراین inactive فعلی آن، اثر تاریخی
را بی‌اعتبار نمی‌کند.

این اعداد دامنه اولویت Golden Case را بسیار کوچک‌تر می‌کنند: دو خانواده دارای
اثر باید در موج اول با خروجی تاریخی Reconcile شوند؛ ۴۲ خانواده دیگر همچنان برای
قابلیت و مهاجرت نگه داشته می‌شوند، اما نبود اثر retained به معنی قابل‌حذف‌بودن یا
عدم اجرا/رد آن‌ها نیست.

## مسیر ساخت، اعتبارسنجی و ذخیره شرط

تحلیل ایستای پنج DLL هش‌پین‌شده، ۳۲ متد و ۲٬۱۸۳ Instruction نشان داد که
`btnCondition_Click` پنجره اختصاصی `FormDiscountCondition` را باز می‌کند و پس
از تأیید، `FilterCondition` آن را در `DiscountEntity.SqlCondition` می‌نویسد.
`CopyNew_Click` دومین Setter منتخب است و شرط Rule مبنا را برای نسخه کپی‌شده
منتقل می‌کند.

در خود پنجره، `FilterControl` با
`CriteriaToWhereClauseHelper.GetDataSetWhere` به عبارت Where تبدیل می‌شود. دکمه
تأیید ابتدا زمینه موقت EVC را می‌سازد و سپس از
`ValidateUserBuiltCondition` به `ExecuteBuiltCondition` می‌رسد. Adapter برای این
اعتبارسنجی چهار `DataContext.Execute` با چهار Literal دارای شکل
`sp_executesql` دارد. پس Validation قدیمی فقط Parse یا Allowlist نیست؛ شرط
ساخته‌شده را در زمینه آزمایشی اجرا می‌کند. این روش سازگاری اجرایی را می‌سنجد،
اما مرز امنیتی DSL محسوب نمی‌شود.

Save فرم، Validation و `SaveCommandcustomize` را فراخوانی و سپس Commit می‌کند؛
Business save نیز دو بار به مسیر عمومی `TypeSpecRow.SaveCommand` واگذار می‌کند.
در متدهای اختصاصی تخفیف هیچ Reference نام‌دار Permission/Authorization دیده
نشد. بررسی BaseForm ثابت کرد `FormDiscount` از `FormBaseWithListDataEntry` ارث
می‌برد. Init عمومی `InternalApplyUserPermission` را فراخوانی می‌کند؛ این مسیر با
`UserSessionInfo.HasPersmission` وضعیت Enabled دکمه‌های Toolbar را تعیین می‌کند.
Click handlerهای New/Edit/Delete/Save نیز فقط `Visible && Enabled` را بررسی و
سپس Command داخلی را Dispatch می‌کنند. خود چهار Internal command هیچ Permission
recheck ندارند. پس مرز اثبات‌شده UI-command gate است، نه Service authorization.
خود `HasPersmission/HasPermission` نیز Cache نشست `UserPermissionS` را با
`ClassName+AccessNodeKey` یا `AccessNodeId` جست‌وجو و Flag آماده `HasAccess` را
برمی‌گردانند؛ در دو Lookup هیچ Database round trip نیست. نحوه تبدیل Admin bypass
و Deny precedence به `HasAccess` داخل این متدهای منتخب اثبات نشد.
کلیدهای Safe داخل Base منتخب `New/Edit/Delete/Print` هستند؛ سه کلید Mutating با
Childهای Route تطبیق مستقیم دارند، ولی `View` در این متد مصرف نمی‌شود. بنابراین
مصرف واقعی Child تنظیم‌شدهٔ View هنوز از این مسیر اثبات نشده است.
کلید مستقل `Save` نیز وجود ندارد؛ Save از ورود مجاز به State جدید/ویرایش و وضعیت
دکمه تبعیت می‌کند، ولی Command داخلی مجوز را دوباره بررسی نمی‌کند.

استخراج Aggregate مجوز از Clone این بخش را جلوتر برد. Route دقیق فرم به
`AccessNodeId=404` و کلید `DiscountRules` می‌رسد و چهار Child قابل‌نمایش
`View/New/Edit/Delete` دارد. Snapshot شامل ۱۴۱ کاربر فعال و هفت Admin bypass
است؛ Root و هر چهار Child پانزده Effective allow، Root نیز ۱۲۶ Neutral/no-allow
و هر پنج Node صفر Explicit deny دارند. هیچ هویت، نام گروه یا Assignment فردی
ذخیره نشد؛ بنابراین مساوی‌بودن Countها اثبات نمی‌کند همان Principalها همه چهار
مجوز را دارند.

در این Subtree فرمان جدا برای `Review` یا `Publish` وجود ندارد. همراه با مسیر
Save/Commit، ساخت و انتشار Rule در مدل قدیم از نظر Workflow تفکیک نشده‌اند.
این یافته وجود Check منو را ثابت نمی‌کند؛ فقط قرارداد پیکربندی و Aggregate حق‌ها
را نشان می‌دهد. ERP مقصد باید مجوز را در API هر Transition دوباره enforce کند.

برای مقصد، Draft/Review/Publish/Deactivate/Rollback باید مجوزهای API مستقل،
Audit غیرقابل‌تغییر و انتشار چهارچشمی داشته باشند. اعتبارسنجی نیز باید کامپایل
AST نوع‌دار و برآورد هزینه باشد و هیچ SQL نویسنده را اجرا نکند.

## اثر روی طراحی ERP شخصی

در ERP مقصد اجرای مستقیم `SqlCondition` ممنوع می‌ماند. جایگزین لازم است:

- AST/DSL نوع‌دار با Field و Operatorهای Allowlist؛
- Rule version غیرقابل‌تغییر، Publisher، Approver و Hash؛
- Compiler محدود که Query پارامتری می‌سازد و هیچ SQL خام نمی‌پذیرد؛
- Snapshot واحد برای Price، Stock، Order و Rule در کل محاسبه؛
- `RuleEvaluationTrace` برای دلیل پذیرش/رد هر Rule؛
- Golden Case از هر ۴۴ الگوی متمایز و آثار واقعی منتخب؛
- تست منفی برای متن مخرب، Field ناشناخته، حلقه/هزینه نامحدود و Rule بدون نسخه؛
- انتشار چهارچشمی و Rollback با انتخاب نسخه قبلی، نه ویرایش تاریخچه.

## چیزی که هنوز قطعی نیست

- کدام‌یک از ۴۴ الگو از نظر کسب‌وکار باید به چه Predicate نوع‌داری تبدیل شود؛
- مجوز مؤثر منو/BaseForm و نقش‌های واقعی نویسنده/ناشر `SqlCondition`؛
- شاخه اجراشده و خروجی هر Rule برای یک سفارش خاص؛
- هم‌ارزی عددی موتور قدیم و مقصد بدون Golden Case اجرایی در محیط ایزوله؛
- معنای رسمی بعضی خانواده‌های `DisType`، Prize و Tie-breakها.

بنابراین شناخت ساختاری موتور و مرز امنیتی آن اکنون بسیار قوی‌تر است، ولی
«پاریتی کامل محاسبات» تا استخراج الگوهای نوع‌دار و Golden Case اثبات نشده است.

## شواهد قابل تکرار

- `artifacts/varanegar_analysis/domains/discount_v2_engine_runtime_20260829.json`
- `artifacts/varanegar_analysis/domains/discount_v2_dynamic_rule_sql_20260829.json`
- `artifacts/varanegar_analysis/domains/discount_v2_condition_families_20260829.json`
- `artifacts/varanegar_analysis/domains/discount_rule_authoring_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/discount_rule_authorization_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/discount_v2_query_contracts_20260829.json`
- `scripts/windows/extract_varanegar_discount_v2_engine_runtime.py`
- `scripts/sql/extract_varanegar_discount_v2_dynamic_rule_sql.py`
- `scripts/sql/extract_varanegar_discount_v2_condition_families.py`
- `scripts/windows/extract_varanegar_discount_rule_authoring_boundary.py`
- `scripts/sql/extract_varanegar_discount_rule_authorization_boundary.py`
