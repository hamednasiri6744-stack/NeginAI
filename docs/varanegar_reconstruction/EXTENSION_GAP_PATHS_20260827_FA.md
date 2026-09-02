# حل سه Gap افزونه از طریق IL عمیق‌تر

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS — ۱۶ Type، ۵۵ Method body، صفر Parse/Hash error**

سه Capability که در مرحله Name-match نخست شیء SQL نداشتند با اسکن محدود خانواده
Typeهای مرتبط در هفت Assembly بررسی شدند. Assemblyها Load یا Execute نشدند؛
رشته‌های غیرمجاز فقط Hash/Length ماندند.

## Linear discount

مسیر استاتیک:

`LinearDiscountHandler → LinearDiscountAdapter`

شاهدهای قطعی:

- `GenerateLinearDiscountId` از متن Allowlist‌شده
  `SELECT ISNULL(MAX(ISNULL(Id, 0)),0) + 1 FROM dbo.POSLineDiscount` استفاده می‌کند؛
- `GetActiveDiscountByGoods` با `DataContext.Query` و Scopeهای کالا، DC، گروه
  مشترک و دسته/سطح/فعالیت مشتری کار می‌کند؛
- `LinearDiscountIsUsed` دارای `Transaction.Start/Commit/RollBack` و
  `ExecuteScalar` است.

پیام مقصد: الگوی `MAX(Id)+1` concurrency-safe نیست و نباید کپی شود؛ Rule ID باید
با Identity/Sequence/UUID و Unique constraint تولید شود. Transaction عمیق‌تر
پیدا شد، بنابراین «صفر بودن signal در UI/Business مستقیم» فقط محدودیت عمق شاهد
قبلی بوده است.

## POS session

مسیر استاتیک:

`POSSessionHandler.Send → POSSessionAdapter.Send → usp_ReplicateSalesReceipt`

Adapter از `ExecuteNonQuery` و `Transaction.Start/Commit/RollBack` استفاده می‌کند.
بنابراین Session فقط صفحه Query نیست: یک Command ارسال/Replication رسید فروش هم
دارد. قرارداد مقصد با `pos.replicate_session_sales_receipts` اصلاح شد و Query
خلاصه Session جدا باقی ماند.

## Dealer day path

فرم Child واقعی `FormEditDealerDayPath` پیدا شد. `SaveCommand` آن DataContext را
می‌سازد و از `DealerDayPathUIHelper`/Base Save path استفاده می‌کند. Fieldهای
قابل‌مشاهده استاتیک:

- `ActiveDate`؛
- `DealerUniqueId`؛
- `VisitTemplatePathUniqueId`؛
- Detail کالا با `ProductUniqueId` و `OrderOf`.

Search termهای اصلاح‌شده سه Procedure candidate را در Clone پیدا کردند:

- `dbo.USP_SDSNET_DealersDayPathList_SAVE`؛
- `dbo.USP_SDSNET_DealersDayPath_GetList`؛
- `dbo.USP_SDSNET_DealersDayPath_SAVE`.

این نام‌ها با IL/نام Entity هم‌راستا هستند، ولی مسیر اجرای Runtime تا Procedure
هنوز باید با Base-class/ORM mapping یا dependency مستقیم اثبات شود.

## ایمنی و محدودیت

- ۷ Assembly، ۱۶ Type، ۵۵ Method body، ۴۵۴ Call و ۱۳۰ String literal بررسی شد؛
- ۱۸ Business literal و ۱۲ UI literal مجاز، ۱۰۰ رشته فقط Fingerprint؛
- Missing file، Hash mismatch، Metadata/Method error و Validation error همگی صفر؛
- هیچ UI action، Command یا SQL module اجرا نشد.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_extension_gap_paths_20260827.json`

Extractor:
`scripts/windows/extract_varanegar_extension_gap_paths.py`
