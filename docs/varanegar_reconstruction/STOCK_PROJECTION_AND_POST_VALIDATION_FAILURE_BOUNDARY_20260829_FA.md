# مرز Projection موجودی و شکست اعتبارسنجی پس از سند — ۲۰۲۶-۰۸-۲۹

## نتیجهٔ اصلی

`inv.AfterInvVocherHdr` با وجود نام «After»، صرفاً اعلان موفقیت نیست؛ چهار
Validator را اجرا می‌کند و برای نوع ۲۰ پیش از Validation وضعیت Batch را نیز
تغییر می‌دهد. اما خطا را Throw نمی‌کند و فقط از Output parameter برمی‌گرداند.
Callerهای Confirm و Unconfirm آن پیام را به متن نتیجه اضافه می‌کنند و Guard توقف
ندارند.

در مسیر Confirm بدون Transaction محیطی، Header پیش از After Commit شده است.
در Unconfirm، After پیش از Commit اجرا می‌شود، ولی پیام خطا باز هم مانع Commit
نمی‌شود. پس «پیام خطا» در این قرارداد لزوماً کنترل Transaction نیست.

## ترتیب Confirm

ترتیب ایستای `dbo.USP_SDSNET_ConfirmVocher`:

```text
Validation پیشین → Transaction/Savepoint → تغییر Header →
Commit در حالت بدون Ambient transaction → AfterInvVocherHdr → append AfterMsg
```

هیچ شرط `AfterMsg != empty → rollback/return` میان Append پیام و ادامهٔ Cursor
نیست. این پنجره برای مسیر مستقیم بدون Ambient transaction قطعیِ ساختاری است؛
وقوع خطای واقعی ثابت نشده و `Vocher_Save` می‌تواند Transaction بیرونی داشته باشد.

Cursor مربوط به After شرط `CreateVocher15 <> 1` دارد؛ بنابراین حالت تولید سند
نوع ۱۵ از همین حلقه عبور نمی‌کند. این omission لزوماً خطا نیست، ولی باید در مقصد
سیاست صریح و تست مستقل داشته باشد.

## ترتیب Unconfirm

`dbo.USP_SDSNET_UnConfirmVocher` وضعیت و Cleanup را داخل Transaction تغییر می‌دهد،
سپس برای هر Header، After را صدا می‌زند، `AfterMsg` را append می‌کند و بعد Commit
می‌کند. چون خود After `RAISERROR`/`THROW` ندارد و Caller پیام را Guard نمی‌کند،
خطای Validation به‌تنهایی Rollback را فعال نمی‌کند.

## داخل AfterInvVocherHdr

این Procedure:

- Transaction، Savepoint، Commit، Rollback، `RAISERROR` یا `THROW` ندارد؛
- ۹ سیگنال `NOLOCK` دارد؛
- برای نوع ۲۰ ابتدا `BatchNo.IsDisabled` را متناسب با حالت تأیید تغییر می‌دهد؛
- سپس `usp_VocherValidation`، `usp_CheckOnHandQtyAndDetailQty`،
  `usp_CheckCardexQty` و `usp_CheckCardexDetailQty` را فراخوانی می‌کند؛
- بررسی‌های عمومی OnHand/Cardex را برای انواع ۱۲ و ۱۳ skip می‌کند؛
- دو بررسی Cardex را فقط وقتی سند تأییدشده است اجرا می‌کند؛
- یک Guard ویژهٔ انتقال نوع ۸۵/۶۵ نیز دارد.

در مسیر مستقیم Confirm، Update نوع ۲۰ پس از Commit Header و بدون Transaction
محلی After رخ می‌دهد. در مسیر Unconfirm یا Save بیرونی، Ambient transaction
ممکن است آن را پوشش دهد. Physical enlistment مسیر Managed از این شاهد معلوم نیست.

## قرارداد Rule Matrix کاردکس

`inv.tblCardexType` در Snapshot جاری ۵۰ Rule برای ۳۰ نوع سند دارد:

| شکل اثر | تعداد Rule |
|---|---:|
| اثر مثبت | ۲۷ |
| اثر منفی | ۲۲ |
| اثر صفر | ۱ |
| مؤثر بر OnHand | ۲۹ |
| مؤثر بر Damaged | ۱۵ |
| مؤثر بر Reserved | ۴ |

Ruleها با `VocherTypeCode + HealthCode + CardexType` جهت و Projection مقصد را
تعیین می‌کنند. این Matrix باید Crosswalk نسخه‌دار باشد و نباید به شرط‌های پراکندهٔ
UI تبدیل شود.

## Triggerهای Projection و Guard

سه Trigger منتخب فعال‌اند:

- Header projection با Cursor، `RAISERROR` و `ROLLBACK`؛
- Item projection با Cursor، `TRY/CATCH` و `ROLLBACK`؛
- Guard منفی‌شدن `StockGoods` به‌صورت set-based روی `inserted`.

Guard آخر دو قابلیت bypass دارد: `SESSION_CONTEXT` و Replication mode. وجود این
قابلیت‌ها وقوع bypass را ثابت نمی‌کند، اما مقصد باید آن‌ها را Command نگهداری
فنس‌شده، مجاز و قابل Audit بداند.

## وضعیت فعلی و نبود Incident اثبات‌شده

- `GNR.tblStockGoods`: ۶۷٬۱۶۱ ردیف؛ مجموع مؤلفه‌های منفی سالم، خراب، رزرو و
  تحویل‌نشده صفر؛
- `GNR.tblStockGoodsDetail`: صفر ردیف؛ مسیر Batch در دادهٔ جاری فعال نیست؛
- فرمول رسمی Legacy پس از حفظ ۱٬۵۹۴ تعهد فروش باز، Residual موجودی صفر دارد.

بنابراین این تحلیل Failure semantics و قابلیت خطر را ثابت می‌کند، نه رخداد جاری.

## قرارداد مقصد

- هر Validator یک precondition یا postcondition تایپ‌شده با Failure قطعی باشد؛
- Failure هیچ‌گاه فقط متن UI نباشد و باید Transaction را Abort کند؛
- تغییر Batch نوع ۲۰ با Transition پذیرفته‌شده Atomic باشد؛
- استثنای انواع ۱۲/۱۳ و generated type-15 سیاست نسخه‌دار و Golden case داشته باشد؛
- bypass فقط با Command نگهداری، Actor/Reason، Fence و Reconciliation اجباری؛
- Matrix پنجاه‌ردیفی کاردکس منبع Rule، نه Hard-code داخل Frontend؛
- Projection، Accounting و Outbox زیر یک مالک Transaction فیزیکی قابل مشاهده.

## ریسک ثبت‌شده

`R-077` با شدت Critical ثبت شد. Exit آن نیازمند Fault injection هر چهار Validator
در مسیرهای Direct، Outer save، Adapter، Dynamic writer و Unconfirm است.

## ایمنی و محدودیت

- فقط Catalog، Rule matrix و Aggregate ناشناس Clone فقط‌خواندنی خوانده شد؛
- هیچ Procedure، Trigger، Form یا Command اجرا نشد؛
- هیچ متن خطا، سند، کالا، انبار، کاربر، Host یا ردیف خام ذخیره نشد؛
- Static order، وقوع Runtime یا فراوانی Route را اثبات نمی‌کند.

## خروجی بازتولیدپذیر

- `scripts/sql/extract_varanegar_stock_projection_validation_boundary.py`
- `artifacts/varanegar_analysis/domains/stock_projection_validation_boundary_20260829.json`
