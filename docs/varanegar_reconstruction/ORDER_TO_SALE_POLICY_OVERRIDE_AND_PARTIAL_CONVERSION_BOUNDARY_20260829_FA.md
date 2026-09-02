# مرز Policy Override و تبدیل جزئی سفارش به فروش

تاریخ استخراج: ۲۰۲۶-۰۸-۲۹  
وضعیت: **SQL Clone فقط‌خواندنی + IL ایستای Hash-pinned؛ اجرای عملیاتی صفر**

## نتیجهٔ کوتاه

پارامترهای `chkNot*` در تبدیل سفارش به فروش چند Boolean هم‌معنی برای «رد کردن
Validation» نیستند. هریک Policy متفاوتی را کنترل می‌کند و بعضی از آن‌ها از فرم
گروهی قابل انتخاب‌اند. مهم‌ترین مورد `chkNotStock` است: مقدار ۱ اقلام دارای کسری
را از مجموعهٔ موقت تبدیل حذف می‌کند و اگر قلم دیگری باقی بماند، تبدیل را ادامه
می‌دهد. پس این گزینه در عمل **تبدیل جزئی سفارش** است، نه صرفاً چشم‌پوشی از خطا.

برای ERP وب نگین این فلگ‌ها نباید مستقیم وارد DTO عمومی شوند. Policy باید در
سرور و براساس Actor، Scope، نوع سفارش، مرکز، نسخهٔ تنظیمات و مجوز مستقل resolve
شود. تبدیل جزئی نیز باید Command جدا، نتیجهٔ Item-level و Audit تغییرناپذیر داشته
باشد.

## مسیر اثبات‌شده

دو مسیر UI متفاوت به خانوادهٔ تبدیل می‌رسند:

1. `FormSaleDataEntry.SaveCommand` هر دو فلگ قیمت را با مقدار ثابت صفر می‌فرستد
   و فقط مقدار موجودی را از فیلد `CheckNotSaleItmStock` می‌گیرد؛ سپس از
   `SaleHandler.OrderToSaleSaveCommand` عبور می‌کند.
2. `FormOrderToSale.AcceptCommandOld` و `AcceptCommandDiscountV2` مقدار موجودی،
   چهار کنترل اعتبار و سقف اعتبار را از کنترل‌های UI می‌گیرند، ولی هر دو فلگ
   قیمت را صفر می‌فرستند. مسیر قدیمی مستقیماً به `OrderHandler.CreateSaleByOrder`
   و مسیر Discount V2 به overload نسخهٔ دوم می‌رسد.

IL سه Assembly با Hash موجودی Deployment تطبیق دارد. Assemblyها فقط به‌صورت PE
و IL خوانده شدند و Load/Execute نشدند.

## معنی دقیق Policyها

| Policy | ورودی Legacy | مقدار ویژه | رفتار اثبات‌شده |
|---|---|---:|---|
| کسری موجودی | `chkNotStock` | ۱ | اقلام کسری از `#tblTempEvcItem` حذف می‌شوند؛ اگر هیچ قلمی نماند فرمان رد می‌شود، وگرنه تبدیل جزئی ادامه می‌یابد |
| قیمت قراردادی | `chkNotCPrice` | ۱ | Check قیمت قراردادی برای نوع سفارش غیر ویژه اجرا نمی‌شود |
| قیمت کاربر | `chkNotPrice` | ۱ | Check مشروط UserPrice اجرا نمی‌شود؛ Check مستقل OrderItemPrice قبل از این Branch همچنان باقی است |
| اعتبار مشتری | `chkNotBedCredit` + `chkNotAsnCredit` | هر دو ۱ | Reload تنظیمات مرکز و Validator اعتبار مشتری رد می‌شود؛ سایر ترکیب‌ها با تنظیمات DC بازنویسی می‌شوند |
| اعتبار عامل | دو فلگ Dealer | هر دو ۱ | Reload تنظیمات مرکز و Validator اعتبار عامل رد می‌شود؛ سایر ترکیب‌ها با تنظیمات DC بازنویسی می‌شوند |
| سقف مشتری | `chkNotCheckMaxLimit` | ۱ | `uspCheckCustLimit` اجرا نمی‌شود |
| تاریخ انقضا | `IgnoreValidateExpDate` | — | در Wrapper فعلی فقط declaration دارد و اثر SQL Runtime برای آن ثابت نشد |
| Rollback | `WithOutRollback` | ۱ | فقط Rollback شاخهٔ `XACT_STATE=-1` را suppress می‌کند؛ معادل خاموش‌کردن همهٔ Rollbackها نیست |

دو Gate مستقل نیز رفتار موجودی را عوض می‌کنند: انبار می‌تواند
`AllowNegativeOnHandQty` داشته باشد و نوع سفارش می‌تواند `EffectOrderOnStockGoods`
داشته باشد. همچنین چند نوع سفارش ویژه از بعضی Checkها مستثنا هستند. بنابراین
تصمیم نهایی حاصل ترکیب Caller، تنظیمات مرکز/انبار و نوع سفارش است.

## نکتهٔ اعتبار مشتری و عامل

ورودی‌های اعتبار سه‌حالته یا انتخاب جزئی Caller نیستند. اگر هر دو فلگ یک زوج ۱
نباشند، Procedure مقادیر را از تنظیمات همان DC می‌خواند و سپس Validator را طبق
آن Policy اجرا می‌کند. فقط زوج `(1,1)` کل این مسیر را رد می‌کند. در UI گروهی
برای هرکدام CheckEdit مجزا وجود دارد، اما قرارداد SQL آن‌ها زوجی است؛ پیاده‌سازی
وب نباید دو Checkbox مستقل را بدون Rule زوجی و Permission منتشر کند.

## Gate سه‌حالتهٔ فرم گروهی

`SetDefaultForCheckEdits` شش کنترل پراثر را فقط از `ServerConfigEntity` تنظیم
می‌کند. برای پنج کنترل اعتبار/سقف، نگاشت واقعی چنین است:

| مقدار تنظیم | Enabled | Checked | معنی مؤثر |
|---:|---:|---:|---|
| ۰ | ۰ | ۱ | Bypass قفل‌شده |
| ۱ | ۱ | ۰ | پیش‌فرض اجرای کنترل، ولی قابل انتخاب توسط کاربر |
| ۲ | ۰ | ۰ | اجرای اجباری و قفل‌شده |

اما `CheckSaleItmStock` Enum متفاوتی دارد:

| مقدار تنظیم | Enabled | Checked | معنی مؤثر |
|---:|---:|---:|---|
| ۰ | ۱ | ۰ | سخت‌گیرانه به‌صورت پیش‌فرض، با امکان انتخاب تبدیل جزئی |
| ۱ | ۰ | ۱ | تبدیل جزئی اجباری |
| ۲ | ۰ | ۰ | کنترل سخت‌گیرانهٔ اجباری |

این تفاوت ثابت می‌کند عدد ۰/۱/۲ یک Enum مشترک قابل‌استفاده برای همهٔ Ruleها
نیست. هر Policy باید Type و Mapping مستقل داشته باشد.

متد `ApplySetadPermission` برخلاف نامش هیچ Permission/Authorization decision
فراخوانی نمی‌کند. در IL منتخب فقط `SiteType` و `DCRef` را می‌خواند و Enabled بودن
`MenuButtonSelect` را تغییر می‌دهد. این یافته نبود Authorization در سطح Menu یا
بازشدن فرم را ثابت نمی‌کند، اما اثبات می‌کند کنترل‌های Override در این متد با
Permission فردی محافظت نشده‌اند.

## Snapshot ناشناس تنظیمات فعلی

Clone دو ردیف تنظیم برای دو DC و صفر Orphan دارد. دو Profile متمایز دیده شد:

- هر دو Profile برای موجودی مقدار ۲، یعنی کنترل سخت‌گیرانهٔ قفل‌شده دارند؛
- یک Profile هر پنج تنظیم اعتبار/سقف را ۲ دارد؛
- Profile دیگر هر پنج مقدار اعتبار/سقف را `NULL` دارد.

پنج Getter متناظر در Entity و Getter موجودی، `CLI Int32` غیرNullable برمی‌گردانند؛
اما رفتار Materializer برای تبدیل `NULL` دیتابیس به این Int32 در شواهد منتخب ثابت
نشد. در SQL نیز Reload اعتبار مشتری/عامل `ISNULL/COALESCE` ندارد؛ اگر هر دو مقدار
یک زوج `NULL` شوند، شرط `IN(1,2) OR IN(1,2)` به `UNKNOWN` می‌رسد و Branch
Validator وارد نمی‌شود. بنابراین `NULL` نباید خودکار صفر، ۲ یا «تنظیم پیش‌فرض»
تفسیر شود؛ قبل از مهاجرت باید با Owner resolve یا fail-closed شود.

## قرارداد مقصد

- `ConvertOrderToSale` عمومی هیچ `chkNot*` یا `WithOutRollback` از Client نپذیرد.
- سرور یک `PolicyDecision` نسخه‌دار شامل Stock، ContractPrice، UserPrice،
  CustomerCredit، DealerCredit و MaximumLimit تولید کند.
- Decision شامل Actor، Permission، DC/StockDC، OrderType، OperationDate،
  PolicyVersion، Reason و Evidence hash باشد.
- هر Rule یک Enum مستقل داشته باشد و `NULL`/مقدار ناشناخته پیش از Dispatch رد یا
  با نسخهٔ Policy و تأیید Owner resolve شود؛ هیچ Default ضمنی مجاز نیست.
- `ConvertOrderToSalePartiallyForStockShortage` Command مستقل و دارای مجوز ویژه
  باشد؛ نتیجه برای هر Item یکی از `CONVERTED`، `REJECTED_SHORTAGE` یا
  `REJECTED_OTHER_POLICY` را ثبت کند.
- اگر همهٔ اقلام رد شدند، Outcome کل Command `REJECTED` باشد و هیچ Sale ناقص
  ساخته نشود.
- Override اعتبار یا سقف فقط با Permission مستقل، Reason اجباری و Audit
  تغییرناپذیر انجام شود؛ Policy عادی از تنظیمات Server-side resolve شود.
- Parameterهای declared-only مانند `IgnoreValidateExpDate` تا یافتن Caller و
  اثر واقعی به API مقصد منتقل نشوند.
- Golden caseها باید ترکیب نوع سفارش، تنظیمات انبار، قیمت، اعتبار مشتری/عامل،
  سقف و حالت یک/همهٔ اقلام کسری را پوشش دهند.
- آماده‌سازی EVC در Discount V2 و تبدیل اصلی در Legacy دو Context/Connection با
  مرز تراکنشی جدا دارند؛ Policy/EVC/Conversion در مقصد باید یک Unit of Work
  تزریق‌شده داشته باشند یا مرحلهٔ جدا Receipt/Compensation صریح بگیرد.

## سطح اطمینان و محدودیت

- معنی Branchها و مسیرهای UI ذکرشده: **تأییدشده** از SQL/IL Hash-pinned.
- مقدار واقعی انتخاب‌شده در هر اجرای تاریخی: **اثبات‌نشده**؛ Event/Receipt کامل
  برای Policy decision وجود ندارد.
- دسترسی مؤثر کاربران به کنترل‌های فرم و فراوانی استفاده از Overrideها در سه ماه
  گذشته: در این مرحله **اندازه‌گیری نشده**.
- نبود استفادهٔ SQL از `IgnoreValidateExpDate` فقط دربارهٔ Definition فعلی Wrapper
  است و نبود Caller بازتابی یا Assembly دیگر را ثابت نمی‌کند.

## ایمنی و بازتولید

- Clone محلی `READ_ONLY` و Login عضو `db_denydatawriter` بود؛
- هیچ Stored Procedure عملیاتی، فرم، Trigger یا Report اجرا نشد؛
- هیچ Assembly بارگذاری یا اجرا نشد؛
- SQL خام، String literal، دادهٔ کسب‌وکاری، شناسه یا پیام در Artifact ذخیره نشد.

خروجی‌ها:

- `scripts/sql/extract_varanegar_order_sale_policy_flag_sql.py`
- `scripts/sql/extract_varanegar_order_sale_policy_flag_runtime.py`
- `scripts/sql/extract_varanegar_order_sale_policy_gate_runtime.py`
- `scripts/sql/extract_varanegar_order_sale_policy_config_snapshot.py`
- `artifacts/varanegar_analysis/domains/order_sale_policy_flag_sql_20260829.json`
- `artifacts/varanegar_analysis/domains/order_sale_policy_flag_runtime_20260829.json`
- `artifacts/varanegar_analysis/domains/order_sale_policy_gate_runtime_20260829.json`
- `artifacts/varanegar_analysis/domains/order_sale_policy_config_snapshot_20260829.json`
- `tests/test_varanegar_order_sale_policy_flag_boundary.py`
