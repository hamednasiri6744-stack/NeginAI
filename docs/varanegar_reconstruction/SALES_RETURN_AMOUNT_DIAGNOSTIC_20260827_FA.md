# قرارداد تشخیص مبلغ برگشت فاکتور وارانگار

## نتیجه

ادعای قبلی دربارهٔ «۶۹۶ برگشت فعال با مغایرت مبلغ» رد شد. آن سنجش، مبلغ
خالص Header را با مبلغ ناخالص Item مقایسه کرده بود. در تمام ۱۴٬۰۹۱ برگشت
فاکتور موجود، اختلاف با قرارداد رسمی مبلغ خالص **صفر** است.

این نتیجه از اجرای هیچ فرم یا Procedure به دست نیامده است: Catalog و تعریف
SQL و Aggregateهای بی‌نام از Clone فقط‌خواندنی خوانده شدند و DLLهای Deployشده
فقط با Parser متادیتا/IL بررسی شدند؛ هیچ Assembly بارگذاری یا اجرا نشد.

## قرارداد رسمی مبلغ

```text
Item.Discount  = Dis1 + Dis2 + Dis3 + OtherDiscount
Item.AddAmount = Add1 + Add2 + OtherAddition
Item.AmountNut = Item.Amount - Item.Discount + Item.AddAmount
Header.TotalAmount = Σ Item.AmountNut
```

Tax و Charge فیلدهای مستقل‌اند. خود `SLE.usp_CheckRetSaleAmountDiscount` در
فرمول `AmountNut` آن‌ها را اضافه نمی‌کند. تغییر این رفتار در ERP مقصد بدون
شاهد مستقل، شکست Parity است.

## زنجیرهٔ شواهد

| لایه | شاهد | نتیجه |
|---|---|---|
| Entity | `RetSaleItemEntity.set_Amount/set_Discount` | `AmountNutFinal` با تفریق و جمع Decimal بازحساب می‌شود |
| UI | `FormRetSaleDataEntry.FillSumOfDisAddS` و Lambda نهایی آن | `Header.TotalAmount` از جمع `AmountNutFinal` می‌آید |
| Business/DataAccess | `RetSaleHandler.CheckRetSaleAmountDiscount` → `RetSaleAdapter` | مرز Validator مبلغ/تخفیف وجود دارد |
| SQL Save | `dbo.usp_Sdsnet_RetSale_Save` | Validator رسمی را در مسیر Save فراخوانی می‌کند |
| SQL RD | `SLE.usp_RD_InsertRetSale` | بعد از تبدیل RD، Validator رسمی را فراخوانی می‌کند |
| SQL Validator | `SLE.usp_CheckRetSaleAmountDiscount` | Rollup اجزا، فرمول قلم و جمع خالص Header را کنترل می‌کند |
| SQL Repair | `dbo.usp_RecalcRetSale` | `TotalAmount` را از `SUM(AmountNut)` بازسازی می‌کند |

وجود این مسیرها به معنی اجرای آن‌ها در این تحلیل نیست؛ فقط تعریف و شکل تماس
آن‌ها بررسی شده است.

## نتیجهٔ تطبیق داده

| کنترل | نتیجه |
|---|---:|
| کل Headerها | ۱۴٬۰۹۱ |
| اختلاف مقایسهٔ نامعتبر با Gross | ۷۳۱ |
| اختلاف Gross در Header فعال | ۶۹۶ |
| اختلاف Header با `SUM(AmountNut)` | ۰ |
| اختلاف Header با `SUM(Amount-Discount+AddAmount)` | ۰ |
| اختلاف فرمول ذخیره‌شدهٔ قلم | ۰ |
| اختلاف Rollup تخفیف | ۰ |
| اختلاف Rollup اضافه | ۰ |
| بیشترین Residual رسمی | ۰ |
| جمع ناخالص منهای خالص رسمی | ۲۰٬۷۲۶٬۲۴۵٬۸۵۸ |

در سه ماه ۱۴۰۵/۰۳/۰۱ تا ۱۴۰۵/۰۵/۳۱ نیز Residual رسمی در تمام ماه‌ها و هر دو
وضعیت فعال/باطل صفر است. اختلاف Gross در این پنجره صرفاً میزان تعدیل‌های
تجاری را نشان می‌دهد.

## ترتیب تشخیص Incident

1. معلوم کن عدد گزارش‌شده Gross، Net، Tax، Charge، تخفیف، اضافه، اعتبار تسویه
   یا مقدار انبار است؛ این‌ها یک مفهوم نیستند.
2. برای هر قلم، Rollup تخفیف و اضافه و سپس
   `Amount - Discount + AddAmount` را محاسبه کن.
3. `Header.TotalAmount` را فقط با `SUM(Item.AmountNut)` بسنج؛ مقایسه با
   `SUM(Item.Amount)` برای تشخیص فساد داده ممنوع است.
4. وضعیت ابطال، نوع برگشت، مبنای فروش/درخواست، تاریخ عملیات و Scope را جداگانه
   کنترل کن.
5. بعد از صحت مبلغ، Voucher انبار نوع ۱۰ و جفت اعتبار 1006/97 را مستقل تطبیق بده.
6. قبل از پیشنهاد اصلاح، خطای دقیق Validator و نتیجهٔ Transaction را ثبت کن.

## قرارداد مقصد

- Gross و تمام مؤلفه‌های تخفیف/اضافه باید به‌صورت Money value object و با
  Provenance نگهداری شوند.
- Net یک مقدار مشتق‌شده با Policy نام‌دار است و در مرز Command دوباره اعتبارسنجی
  می‌شود.
- Quarantine فقط برای نقض فرمول رسمی، Rollup اجزا یا جمع Header فعال می‌شود.
- Dashboard باید Bridge شفاف `Gross → Discount → Addition → Net` نشان دهد.
- Alert/Telemetry نباید شناسه مشتری یا سند را در Artifact تحلیلی عمومی ذخیره کند.
- Drift نسخه DLL، تعریف Validator و رفتار گردکردن باید در Baseline انتشار ثبت شود.

## حدود شواهد

- Clone وضعیت فعلی و Aggregate سه‌ماهه را ثابت می‌کند، نه تمام Editهای میانی گذشته.
- IL شکل شاخهٔ قابل‌دستیابی را ثابت می‌کند، نه مسیر دقیق یک کاربر مشخص.
- Getterهای مالی گردکردن را نشان می‌دهند، اما همه نسخه‌ها و تنظیمات موتور تخفیف
  به‌صورت Runtime اجرا نشده‌اند.
- رفتار حسابداری جداگانهٔ Tax/Charge باید در دامنه مربوط خودش دنبال شود.

## منبع بازتولید

- Extractor: `scripts/sql/extract_varanegar_sales_return_amount_diagnostic_contract.py`
- Artifact: `artifacts/varanegar_analysis/ui/varanegar_sales_return_amount_diagnostic_contract_20260827.json`
- دامنهٔ مادر: `domains/11_SALES_RETURNS_AND_SETTLEMENT_FA.md`
