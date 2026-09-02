# دامنه ۲۱: مرز تاریخ قطعی پیش از صدور سند حسابداری

تاریخ استخراج: ۲۰۲۶-۰۸-۲۸  
وضعیت: **رد پیش از Mutation تأیید شد؛ پوشش همهٔ انبارهای خرید FAIL؛ استثنای حقوق بدون نمونهٔ تاریخی است**

## نتیجهٔ کوتاه

`dbo.usp_DoExternalVoucher` برای هر ترکیب نوع سند انتخابی و DC انتخابی، قبل از
ساخت `PreVoucher` تاریخ قطعی سیستم منبع را کنترل می‌کند. شکست این کنترل Result
کسب‌وکار برمی‌گرداند و پیش از اولین Write پایدار `RETURN` می‌کند؛ بنابراین این
شاخه در مسیر مستقر Mutation جزئی ندارد.

اما Finality خرید کامل نیست. SQL مقدار زیر را محاسبه می‌کند:

```text
MIN(ICA.DefeniteDate)
از ردیف‌های موجود ICAOprDate
که StockDC آن‌ها متعلق به DC انتخابی است
```

Anti-join یا شمارش «همهٔ StockDCهای لازم ردیف دارند» وجود ندارد. اگر از ده
انبار، هشت انبار ردیف تاریخ قطعی داشته باشند، `MIN` فقط همان هشت مورد را می‌بیند
و دو ردیف مفقود از تصمیم حذف می‌شوند. این با `R-050` بحرانی ردیابی شده است.

## الگوریتم مستقر

1. سال مالی، User موجود، نوع‌های سند، DCها و `ToDate` اعتبارسنجی می‌شوند.
2. `ToDate` باید داخل بازهٔ سال مالی باشد.
3. Cross product تمام `ExternalVoucherType × DC`های انتخابی ساخته می‌شود.
4. برای سیستم خرید (`VNSystemId=1`) کمینهٔ `ICA.tblICAOprDate.DefeniteDate` روی
   ردیف‌های موجود StockDC همان DC/سال خوانده می‌شود.
5. برای بقیه، کمینهٔ `GNR.tblOprDate.LastDate` با کلید
   `OperationId + DC + AccYear` خوانده می‌شود.
6. `OperationId=5` صریحاً از شرط رد مستثناست.
7. تاریخ تهی برای سیستم غیرمستثنا به رشتهٔ تهی تبدیل و قبل از `ToDate` محسوب
   می‌شود؛ نبود کامل ردیف Fail-closed است.
8. اگر خطا وجود داشته باشد، Result برگردانده و `RETURN` می‌شود؛ فراخوانی
   `usp_DoPreVoucher` و Insertهای Header/Line/Relation بعد از این نقطه‌اند.

کلیدهای موجود خودشان Duplicate ندارند: Duplicate گروه
`GNR(DCRef,SysRef,AccYear)` و `ICA(StockDCRef,AccYear)` هر دو صفرند. مسئله
Duplicate نیست؛ مسئلهٔ **completeness** مجموعهٔ ICA است.

## پوشش Clone

| سال | DC فعال | Scope دارای StockDC | Scope کامل | Scope جزئی | Scope بدون ردیف | StockDC مفقود |
|---:|---:|---:|---:|---:|---:|---:|
| ۱۴۰۳ | ۲ | ۱ | ۰ | ۱ | ۱ | ۶ |
| ۱۴۰۴ | ۲ | ۱ | ۰ | ۱ | ۱ | ۲ |
| ۱۴۰۵ | ۲ | ۱ | ۰ | ۱ | ۱ | ۲ |

در ۱۴۰۵، Scope دارای انبار ده StockDC و فقط هشت ردیف ICA دارد. هر ده StockDC
`InActiveAccYear` تهی دارند؛ پس در Clone شاهدی برای کنارگذاشتن آن دو مورد به‌عنوان
انبار غیرفعال وجود ندارد. Scope فعال دیگر StockDC ندارد و چون هیچ تاریخ خریدی
تولید نمی‌شود، به‌شکل Fail-closed رد خواهد شد.

## پوشش سیستم‌ها و تاریخچه

| سیستم معنایی | Operation | نوع تنظیم‌شده | Header نگه‌داری‌شده | Header مسیر جدید | Header سه‌ماهه |
|---|---:|---:|---:|---:|---:|
| حسابداری انبار/خرید | ۱ | ۱۷ | ۱٬۵۴۰ | ۰ | ۰ |
| حسابداری مشتریان | ۲ | ۱۴ | ۲۹۵ | ۰ | ۰ |
| فروش | ۱ | ۲ | ۱۰۹٬۵۶۱ | ۱۷۵ | ۹۷ |
| خزانه | ۲ | ۳۰ | ۸۶٬۱۲۲ | ۲۰۷ | ۱۰۷ |
| حقوق | ۵ | ۲ | ۰ | ۰ | ۰ |

۳۸۲ Header مسیر جدید فقط فروش و خزانه‌اند و با تاریخ‌های فعلی Clone هیچ‌کدام
Finality failure ندارند. نبود Header جدید خرید یعنی اثر Runtime شکاف خرید در
تاریخچهٔ نگه‌داری‌شده اثبات نشده است. دو نوع حقوق تنظیم شده‌اند، اما صفر نمونهٔ
تاریخی دارند؛ استثنای `OperationId=5` ممکن است کاملاً عمدی باشد، ولی باید مالک
آن را تأیید و با Golden case تثبیت کند.

## قرارداد مقصد

1. Finality decision برای هر `type × DC` صریح و Explainable باشد.
2. ابتدا مجموعهٔ StockDCهای applicable با Policy version تعیین شود؛ سپس نبود
   حتی یک Operation row باید Fail-closed باشد.
3. `MIN(date)` فقط بعد از اثبات cardinality کامل محاسبه شود.
4. استثنای حقوق یک Policy versioned و Owner-approved باشد، نه عدد جادویی ۵.
5. تصمیم باید شناسهٔ Command، Policy version، مجموعهٔ Scope و نتیجهٔ هر عضو را
   Audit کند؛ تاریخ‌های حساس خام وارد Log عمومی نشوند.
6. هیچ Write پایداری قبل از PASS همهٔ سیستم‌ها انجام نشود.
7. Retry همان Finality snapshot معتبر را بازگرداند یا با تغییر نسخه، Conflict
   صریح بدهد.

## Golden و Fault tests

- ده StockDC که یکی Operation row ندارد باید صدور را رد کند.
- تاریخ‌های مختلط با یک تاریخ عقب باید رد شوند.
- DC بدون StockDC باید Result مشخص `NO_APPLICABLE_STOCK_DC` یا Policy مصوب داشته
  باشد، نه رفتار مبهم.
- انتخاب چند DC و چند نوع باید همهٔ ترکیب‌ها را ارزیابی کند؛ یک PASS نباید Error
  ترکیب دیگر را بپوشاند.
- دو نوع حقوق باید سناریوی Exempt و Non-exempt تأییدشدهٔ مالک داشته باشند.
- Finality failure باید Snapshot تمام جدول‌های Stage/Header/Line/Relation را
  بدون تغییر بگذارد.

## ماتریس Verification

| نیاز | شاهد | نتیجه | محدودیت |
|---|---|---|---|
| کنترل پیش از Write | ترتیب SQL تا `usp_DoPreVoucher` | PASS | Caller پس از PASS هنوز تراکنش بیرونی می‌خواهد |
| نبود کامل تاریخ غیرمستثنا | `ISNULL(date,'') < ToDate` | PASS | رفتار پیام Runtime اجرا نشد |
| یکتایی کلید تاریخ عملیات | Catalog + Aggregate | PASS | completeness جداست |
| پوشش همه StockDCهای خرید | ۱۰ StockDC در برابر ۸ Row سال ۱۴۰۵ | FAIL | Header جدید خرید نگه‌داری نشده |
| استثنای حقوق دارای Parity | ۲ نوع، صفر Header | FAIL شواهد | Intent ممکن است معتبر باشد |
| مسیر جدید فروش/خزانه با وضعیت فعلی | ۳۸۲ Scope، صفر Failure | PASS Snapshot | وقوع تاریخی هر Gate را ثابت نمی‌کند |

## شواهد و ایمنی

- Artifact:
  `artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json`
- Extractor:
  `scripts/sql/extract_varanegar_voucher_creation_atomicity_policy.py`
- Test:
  `tests/test_varanegar_voucher_creation_atomicity_policy.py`
- Risk: `R-050` در `negin_erp_risk_register_20260827.json`.

اتصال فقط به Clone محلی `READ_ONLY` با `can_update=0` و
`db_denydatawriter=1` بود. هیچ Procedure یا View عملیاتی اجرا نشد، هیچ Assembly
Load نشد و هیچ شناسه/ردیف عملیاتی در Artifact ذخیره نشد.
