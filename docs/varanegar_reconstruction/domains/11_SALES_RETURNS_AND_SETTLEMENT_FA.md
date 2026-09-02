# دامنه ۱۱: برگشت از فروش، ورود انبار و مصرف اعتبار

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- منبع: `127.0.0.1 / NeginPakhsh_WebDev`
- وضعیت دیتابیس: `READ_ONLY`
- حساب تحلیل با `UPDATE=0` و عضویت در `db_denydatawriter` کنترل شد؛ نام حساب
  یا میزبان در Artifact ذخیره نشده است.
- Extractor قابل تکرار:
  `scripts/sql/extract_varanegar_sales_return_domain.py`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/sales_returns_and_settlement_20260826.json`

این مرحله ۱۶ جدول پایه، ۱۲۳ ارتباط FK رسمی، ۱٬۷۳۵ مصرف‌کننده ماژولی و ۲۱
کاندید ارتباط ضمنی را بررسی کرده و ۱۳ قرارداد SQL منتخب را ذخیره کرده است.
هیچ ردیف مشتری/پرسنل، Comment، نام کاربر یا میزبان، Credential، شناسه سند یا
Payment خام در Artifact وجود ندارد.

## نتیجه اصلی: یک برگشت، چهار معنای جدا

```text
SLE.tblRetOrderHdr/Itm        درخواست برگشت؛ الزاماً سند قطعی نیست
            │
            ▼
SLE.tblRetSaleHdr/Itm        سند رسمی برگشت از فروش
       │              │
       │              └─ Acc.tblPayments(1006) → مصرف اعتبار روی فاکتور
       │                                      └─ Payment(97) جفت حسابداری
       ▼
INV.tblVocherHdr/Itm(type=10) ورود تجمیع‌شده کالا به انبار

SLE.tblRetSale*_RD           Staging برگشت در پایان توزیع
NGT.CustomerCallReturns      ثبت موبایل؛ تا Crosswalk رسمی، سند ERP نیست
```

این موجودیت‌ها نباید در نسخه وب در یک جدول یا یک Status ادغام شوند. تأیید
عملیاتی برگشت، ورود کالا، ایجاد اعتبار و مصرف اعتبار چهار Transition مستقل‌اند.

## Masterهای معنایی

کدهای ظاهراً مشابه از Lookupهای متفاوت می‌آیند و قابل یکی‌کردن نیستند:

| CodeType | معنا | کدهای فعلی |
|---:|---|---|
| ۱۰ | سلامت سند برگشت | ۱ سالم، ۲ ضایعاتی، ۳ توزیع‌نشده |
| ۱۷ | نوع سند برگشت | ۱ جزئی، ۲ کلی، ۳ بدون مبنا، ۵ با مبنا و آزاد، ۶ عطف به فاکتور، ۷ عطف به درخواست |
| ۱۰۰۳ | نوع درخواست برگشت | ۱ عطف به فاکتور، ۲ بدون مبنا، ۳ با مبنا و آزاد |
| ۱۰۰۴ | سلامت درخواست | ۱ سالم، ۲ ضایعاتی |

`SLE.tblRetCause` دارای ۱۵ علت فعال است و همه برای Follow-up، سند برگشت و NGT
قابل نمایش‌اند. از آن‌ها فقط ۹ علت در Headerهای فعلی مصرف شده‌اند. دو علت غالب:

- «کسری کالا»: ۹٬۳۵۲ سند، ۹٬۳۳۹ فعال؛
- «عدم هماهنگی با مشتری»: ۳٬۷۹۱ سند، ۳٬۶۵۰ فعال.

در مدل مقصد Code به‌تنهایی کلید نیست؛ کلید باید `(lookup_set, code)` باشد.

## سند رسمی برگشت

`SLE.tblRetSaleHdr` تعداد ۱۴٬۰۹۱ سند از `۱۴۰۳/۰۱/۱۸` تا `۱۴۰۵/۰۵/۳۱` دارد:

| شاخص | مقدار |
|---|---:|
| فعال | ۱۳٬۹۱۳ |
| ابطال‌شده | ۱۷۸ |
| UUID پر و یکتا | ۱۴٬۰۹۱ |
| با سند فروش مبنا (`TSaleRef`) | ۹۶۸ |
| با Sale پیشنهادی برای تسویه | ۸٬۵۱۹ |
| متصل به توزیع | ۱۱٬۱۷۱ |
| متصل به درخواست برگشت | ۳ |
| متصل به FRU/NGT در Header اصلی | ۰ |

همه ردیف‌ها `IsNew=1` دارند؛ مسیر Legacy در این Snapshot مصرف نشده است. کلید
تجاری زیر و UUID هر دو بدون تکرارند و شماره صفر نیز وجود ندارد:

```text
(AccYear, DCRef, DCSaleOfficeRef, RetSaleNo)
```

هیچ Source Sale، Settlement Sale، RetOrder یا Dist یتیم پیدا نشد و Customer
سند با Source/Settlement Sale در همه لینک‌ها سازگار است. در ۸۶۴ سند Source و
Settlement یک Sale هستند و در ۹ سند هر دو پر ولی متفاوت‌اند؛ پس این دو فیلد
دو مفهوم مستقل دارند.

پرتکرارترین Workflow فعال، نوع ۳ سالم و بدون مبنا با ۱۲٬۵۱۲ سند است. سپس
۶۴۳ برگشت کلی سالم، ۴۷۱ برگشت بدون مبنای ضایعاتی و ۲۸۶ برگشت جزئی سالم قرار
دارند. در پنجره `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` تعداد ۱٬۲۱۰ سند برای ۷۲۰ مشتری و
۱۷۹ عامل ثبت شده که ۱٬۲۰۸ فعال و دو مورد ابطال‌شده‌اند.

## اقلام و اتصال به فاکتور مبنا

`SLE.tblRetSaleItm` تعداد ۴۱٬۹۳۱ ردیف با UUID یکتا، مقدار مثبت و ۲٬۷۱۱ کالای
متمایز دارد. هیچ Header، کالا یا واحد یتیم نیست. هر Header بین ۱ تا ۸۰ ردیف
و به‌طور متوسط ۲٫۹۷۶ ردیف دارد؛ `(HdrRef, RowOrder)` یکتا است.

فیلد `tblRetSaleItm.SaleRef` در **تمام ۴۱٬۹۳۱ ردیف خالی** است. بنابراین اتصال
ردیفی به فاکتور مبنا با ID مستقیم انجام نمی‌شود. View رسمی `FRU.RetSaleItmModel`
و داده فعلی قرارداد زیر را تأیید می‌کنند:

```text
header.TSaleRef
+ item.GoodsRef
+ item.PrizeType
+ COALESCE(item.FreeReasonId, 0)
```

برای ۶٬۰۲۵ قلم متعلق به Headerهای دارای مبنا، این کلید در هر ۶٬۰۲۵ مورد دقیقاً
یک کاندید SaleItem و صفر مورد مبهم/گمشده دارد. تطبیق تجمعی مقدار نیز ۵٬۹۰۱ گروه
برگشت کامل، ۱۲۴ گروه برگشت جزئی و **صفر بیش‌برگشت** نشان می‌دهد؛ بیشترین نسبت
برگشت به فروش ۱ است.

علت Item در ۴۱٬۹۲۷ ردیف با Header برابر و در ۴ ردیف متفاوت است. علت ردیف باید
قابل نگهداری باشد و با مقدار Header بازنویسی اجباری نشود.

## مبلغ: اصلاح یک هشدار کاذب مهم

مقایسهٔ قبلی `Header.TotalAmount` با `Σ Item.Amount` غلط بود، چون `Amount`
مبلغ **ناخالص** قلم است. قرارداد رسمی وارانگار در سه لایه هم‌راستا است:

```text
Item.AmountNut = Item.Amount - Item.Discount + Item.AddAmount
Header.TotalAmount = Σ Item.AmountNut
Item.Discount = Dis1 + Dis2 + Dis3 + OtherDiscount
Item.AddAmount = Add1 + Add2 + OtherAddition
```

- `SLE.usp_CheckRetSaleAmountDiscount` همین فرمول و جمع Header را کنترل می‌کند؛
- `RetSaleItemEntity` مقدار `AmountNutFinal` را با تفریق/جمع بالا بازحساب می‌کند؛
- `FormRetSaleDataEntry.FillSumOfDisAddS` جمع `AmountNutFinal` را در
  `Header.TotalAmount` می‌گذارد؛
- `dbo.usp_RecalcRetSale` نیز Header را از `SUM(AmountNut)` بازسازی می‌کند.

نتیجهٔ تطبیق کل ۱۴٬۰۹۱ سند:

| سنجش | اختلاف |
|---|---:|
| Header با جمع ناخالص `Amount` ـ صرفاً مقایسهٔ نامعتبر | ۷۳۱ |
| از ۷۳۱ مورد بالا، فعال | ۶۹۶ |
| Header با جمع خالص ذخیره‌شده `AmountNut` | **۰** |
| Header با خالص محاسبه‌شده `Amount-Discount+AddAmount` | **۰** |
| فرمول خالص قلم | **۰** |
| Rollup تخفیف و اضافه | **۰** |

اختلاف تجمعی ناخالص با خالص رسمی `۲۰٬۷۲۶٬۲۴۵٬۸۵۸` است و یک تعدیل توضیح‌پذیر
کسب‌وکاری است، نه فساد داده. Tax و Charge طبق Validator رسمی جزو فرمول
`AmountNut` نیستند و جدا نگهداری می‌شوند.

نتیجه برای Migration: مؤلفه‌های ناخالص، تخفیف و اضافه و مبلغ خالص باید با
Provenance حفظ شوند؛ Quarantine فقط وقتی فعال می‌شود که Invariant رسمی خالص
نقض شود. صرف اختلاف `Amount` و `TotalAmount` هرگز خطا نیست. قرارداد بازتولیدپذیر
در `varanegar_sales_return_amount_diagnostic_contract_20260827.json` ثبت شد.

## ورود انبار: Projection تجمیع‌شده کالا

برای تمام ۱۳٬۹۱۳ برگشت فعال دقیقاً یک Voucher نوع ۱۰ وجود دارد؛ همه تأییدشده
و AccYear، StockDC و Health آن‌ها با Header برگشت سازگار است. سند بدون Voucher،
Voucher چندگانه یا Voucher یتیم صفر است.

Procedure رسمی `dbo.USP_SDSNET_GenerateRetSaleVocher` اقلام را بر اساس کالا
جمع می‌کند، ID و RowOrder جدید می‌سازد و GoodsType=4 را حذف می‌کند. بنابراین
ID یا RowOrder سند انبار Crosswalk ردیف برگشت نیست.

تطبیق صحیح در سطح `(RetSale, Goods)` انجام شد:

| نتیجه | گروه کالا |
|---|---:|
| دقیق | ۳۹٬۶۰۹ |
| فقط در برگشت | ۰ |
| فقط در Voucher | ۰ |
| اختلاف مقدار | ۰ |

در داده فعلی هیچ قلم فعال GoodsType=4 وجود ندارد. این صفر به معنای حذف قاعده
نیست؛ مقصد باید استثنای کالای غیرانبارشونده را مطابق Procedure نگه دارد.

## اعتبار برگشت و تسویه فاکتور

همه ۱۴٬۵۸۶ Payment متصل به برگشت از نوع `1006` هستند و به ۱۳٬۲۲۳ سند فعال
متصل می‌شوند. هیچ Payment به برگشت ابطال‌شده/یتیم یا Customer متفاوت وصل نیست.
برای تک‌تک این ۱۴٬۵۸۶ ردیف دقیقاً یک Counter-entry نوع `97` با همان مبلغ و
Customer وجود دارد و `PaymentRef` آن را به Payment نوع 1006 متصل می‌کند.

```text
RetSale credit
  └─ Payment 1006: اعمال اعتبار روی Sale
       └─ Payment 97: جفت خنثی‌کننده/انتقال حساب با PaymentRef
```

پوشش اعتبار برگشت‌های فعال نسبت به TotalAmount رسمی Header:

| وضعیت | برگشت |
|---|---:|
| بدون Payment / اعتبار مصرف‌نشده | ۶۹۰ |
| مصرف جزئی | ۸۱۳ |
| مصرف کامل | ۱۲٬۴۹۶ |
| بیش‌مصرف | ۰ |

حداکثر یک برگشت در ۱۲ Allocation مصرف شده است. ۱۳٬۶۱۸ Payment دارای SaleRef
هستند. فقط ۸٬۴۴۴ Allocation با `Header.SaleSettlementRef` برابر و ۵٬۱۷۸ مورد
متفاوت‌اند؛ ۵٬۳۹۸ Header اصلاً SaleSettlementRef ندارند. بنابراین
`SaleSettlementRef` تنها Hint/انتخاب اولیه است و فهرست نهایی تخصیص‌ها نیست.
منبع حقیقت مصرف اعتبار، Ledger و قرارداد `Acc.GetRetSalePayAmount` است.

جدول `dbo.tblPayWithPaymentRelation` در Snapshot فعلی خالی است؛ جفت جاری
1006/97 از `Acc.tblPayments.PaymentRef` به‌طور کامل قابل اثبات است. جدول خالی
برای مسیرهای دیگر/Legacy باید در Schema مقصد حفظ یا صریحاً بازنشسته شود.

## درخواست برگشت

`SLE.tblRetOrderHdr` فقط ۵ Header و ۲۲ Item دارد. چهار درخواست Cancel و هیچ‌کدام
Confirm نشده‌اند؛ یک درخواست Cancel نشده ولی Confirm نیز نشده است. سه سند
برگشت به سه درخواست وصل‌اند و هر سه سند برگشت ابطال‌شده‌اند. بنابراین داده فعلی
هیچ نمونهٔ فعال و کامل از تبدیل Request به Return ارائه نمی‌کند.

بااین‌حال `SLE.usp_AfterSaveRetSale` و
`SLE.usp_sdsnet_CreateRetSaleFromRetOrder` قرارداد عملی را مشخص می‌کنند: مقدار
تجمعی برگشت فعال نباید از مقدار درخواست در کلید کالا/جایزه/علت رایگان بیشتر شود.
برای Golden Case این مسیر باید با داده کنترل‌شده بازسازی شود.

## Staging توزیع و NGT

`SLE.tblRetSaleHdr_RD` اکنون ۳۸ Header و ۶۰ Item برای یک Distribution و تاریخ
`۱۴۰۵/۰۵/۳۱` دارد. همه `RDStatus=7`، سالم، نوع ۳، CancelFlag=0 و بدون Source
Sale/Request هستند. هیچ‌یک هنوز با کلید تجاری به Main Return متصل نیست.

`SLE.usp_RD_InsertRetSale` Statusهای ۵، ۶، ۷، ۱۱ و ۱۲ را به Header/Item اصلی
با ID جدید تبدیل و سپس `usp_AfterSaveRetSale` را اجرا می‌کند. Procedure
`usp_FinalizeRetDist` پس از کنترل و تبدیل، RDها را حذف می‌کند. پس ۳۸ ردیف فعلی
**کار در جریان پایان توزیع** هستند و نباید در گزارش سند رسمی دوباره شمرده شوند.

در NGT فقط دو Header، دو Line و دو QuantityDetail فعال وجود دارد. هیچ‌کدام
RetOrder یا RetSale جاری ندارند؛ اما تحلیل عمیق‌تر نشان داد یک Line نتیجه‌ی دقیق
UUID/Ref در `TourHistory` دارد و Write-back آن انجام شده، در حالی که هدف جاری
اکنون غایب است. Line دیگر هیچ نتیجه‌ی تاریخی ندارد. پس اولی
`HISTORICAL_RESULT_CURRENT_TARGET_MISSING` و دومی `PENDING_OR_UNATTEMPTED` است؛
هیچ‌کدام سند رسمی جاری یا مجوز بازسازی خودکار نیستند.

همچنین FK رسمی `SLE.*.CustomerCallReturnId` به مدل عددی `FRU` اشاره می‌کند، نه
UUID مدل NGT. مسیر `NGT_DoReplicateTour` نیز Commit نتیجه را پیش از Write-back
Crosswalk NGT انجام می‌دهد و یک Failure window دوطرفه دارد. قرارداد کامل در
`NGT_RETURN_CROSSWALK_DIAGNOSTIC_20260827_FA.md` ثبت شده است.

## قرارداد اولیه مدل مقصد

حداقل موجودیت‌ها و مرزها:

- `ReturnRequest` و `ReturnRequestLine` با State مستقل؛
- `SalesReturn` و `SalesReturnLine` با Source Sale اختیاری؛
- `SalesReturnSourceLineMatch` با کلید مرکب و Evidence؛
- `ReturnReason`، `ReturnType` و `GoodsHealth` به‌صورت Master نسخه‌دار؛
- `ReturnInventoryEntry` به‌عنوان Projection تجمیع‌شده `(return, goods)`؛
- `ReturnCredit` و `ReturnCreditAllocation` برای مصرف چندفاکتوری؛
- `AccountEntryPair` برای جفت 1006/97؛
- `DistributionReturnStaging` با Finalize idempotent؛
- `MobileReturnDraft` و Crosswalk صریح به Request/Return؛
- `AmountReconciliationIssue` برای اختلاف Header و Item؛
- نگهداری `source_id` و `source_uuid` برای هر Record مهاجرت‌شده.

نوشتن مستقیم به OpenInvoice، Voucher یا Payment از UI ممنوع است. Command رسمی
برگشت باید در یک Transaction کنترل‌های مقدار، انبار، اعتبار، تأیید و Audit را
اجرا کند و Projectionها را از Eventهای رسمی بسازد.

## Golden Caseهای لازم

1. برگشت جزئی عطف به فاکتور با کلید مرکب Item و مقدار کمتر از فروش.
2. برگشت کامل که Type آن طبق Procedure به حالت کلی تبدیل می‌شود.
3. برگشت بدون مبنا با سلامت سالم و ضایعاتی.
4. برگشت دارای جایزه/FreeReason و جلوگیری از تطبیق با ردیف عادی.
5. ساخت Voucher نوع ۱۰ با دو Item یک کالا و یک ردیف تجمیعی.
6. GoodsType=4 بدون ورود انبار.
7. اعتبار برگشت که روی چند فاکتور تا سقف TotalAmount مصرف می‌شود.
8. ایجاد دقیق جفت Payment 1006/97 و Retry بدون Duplicate.
9. برگشت ابطال‌شده بدون Voucher/Payment فعال.
10. اختلاف Header.TotalAmount و جمع Item که وارد Quarantine می‌شود.
11. تبدیل RetOrder بدون بیش‌برگشت تجمعی.
12. Finalize RD که Main Return را می‌سازد و Staging را پاک می‌کند.
13. NGT Draft بدون Crosswalk که سند مالی/انبار رسمی محسوب نمی‌شود.

## ابهام‌های باز

1. علت تاریخی ۷۳۱ اختلاف TotalAmount Header با جمع Item و اینکه کدام نسخه‌های
   اپلیکیشن آن را ایجاد کرده‌اند.
2. معنای دقیق UI برای RDStatusهای ۵، ۶، ۷، ۱۱ و ۱۲؛ Procedure Eligibility را
   ثابت می‌کند ولی عنوان Master مستقیمی پیدا نشد.
3. چرخه واقعی درخواست برگشت، چون نمونه فعال Confirm‌شده در Clone وجود ندارد.
4. علت باقی‌ماندن ۶۹۰ اعتبار کاملاً مصرف‌نشده و ۸۱۳ اعتبار جزئی.
5. علت تاریخی غیبت هدف جاری برای Line دارای `TourHistory` و وضعیت قطعی Line
   بدون نتیجه؛ Snapshot فعلی فقط دو State متفاوت را ثابت می‌کند.
6. قواعد برگشت چک دریافتی و اثر آن روی قابلیت مصرف اعتبار؛ دامنه بعدی باید
   چرخه چک دریافتی را مستقل ببندد.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_sales_return_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\sales_returns_and_settlement_20260826.json
```
