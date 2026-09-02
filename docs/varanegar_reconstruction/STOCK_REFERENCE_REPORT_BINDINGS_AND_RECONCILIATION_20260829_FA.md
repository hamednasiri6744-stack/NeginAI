# Binding گزارش‌های مرجع موجودی و طرح Reconciliation — ۲۰۲۶-۰۸-۲۹

## نتیجه

سطح `RPT-15` از ۴۱ نام کاندید به ده Binding دقیق تبدیل شد. هر ده مسیر
`FormReportResultList → StockGoodsHandler → StockGoodsAdapter → SQL` با IL ایستا
و Catalog فقط‌خواندنی به یک Procedure یکتا رسید و مجموعه پارامترهای IL و Catalog
برای هر ده مورد، بدون حساسیت به حروف، برابر است.

## نگاشت دقیق

| نقش گزارش | Procedure |
|---|---|
| تاریخچه Batch | `dbo.usp_sdsn_GetBatchHistory` |
| کاردکس Batch | `inv.Usp_SDSN_GetBatchCardexItem` |
| کاردکس موجودی | `inv.usp_sdsn_GetCardexReport` |
| فاکتور آزاد/باز | `SLE.usp_sdsn_GetFreeInvoiceList` |
| تشخیص اصلاح موجودی آسیب‌دیده | `dbo.Usp_CheckModifyStockGoods` |
| سفارش خرید انتقال‌نیافته | `inv.Usp_sdsn_ListOfPOrderWithOutTransfer` |
| خروجی‌های تأییدنشده/تعهد مرکب | `SLE.usp_sdsn_CollectionStockGoodsReport` |
| سفارش باز | `SLE.usp_sdsn_GetOpenOrderList` |
| فروش باز | `SLE.usp_sdsn_GetOpenSaleList` |
| علت رزرو کالا | `inv.Usp_sdsn_ListOfReservedGoods` |

Catalog برای این ده Procedure، ۵۲ پارامتر و ۴۴ dependency اعلام‌شده ثبت کرد.
تعریف‌ها فقط در حافظه برای Hash و پروفایل لغوی خوانده شدند و متن خام SQL، مقدار
تجاری یا شناسه ردیف Persist نشد.

## مرز Source of Truth

این ده خروجی یک Truth واحد موجودی نیستند؛ همگی Procedure گزارش/Projection مشتق‌اند.
Reconciliation باید حداقل پنج دانه را جدا نگه دارد: وضعیت و ردیف سند انبار، Cardex،
Projection جاری StockGoods، تعهد سفارش/فروش باز و Projection رزرو. مقایسه مستقیم
StockGoods با یکی از گزارش‌های تعهد، بدون همسان‌سازی Watermark و Scope، Bug را ثابت
نمی‌کند.

## Playbook اختلاف موجودی

1. Method، Procedure hash، ورودی‌ها و Watermark را Pin کن.
2. Permission فرمان مشاهده را جدا از DC/Stock/Goods scope کنترل کن.
3. `AccYear`، Business date و در Cardex بازه `Date1/Date2` را همسان کن.
4. On-hand، Reserved، OpenOrder و OpenSale را به‌عنوان کمیت‌های مستقل تفکیک کن.
5. Policy حذف/لغو/تأییدنشده را از همان Procedure مشخص کن.
6. Grain رخداد Voucher/Cardex را پیش از مقایسه با Projection جاری بررسی کن.
7. Snapshot timing و Commitهای هم‌زمان را کنترل کن.
8. فقط Residual دارای شاهد را Bug بنام؛ بقیه رفتار Projection یا بدهی داده است.

## UAT لازم برای Result parity

اجرای این طرح مجاز نشده و انجام نشده است. در UAT ایزوله باید Snapshot ثابت و
ناشناس ساخت، برای هر ده نقش یک Case کنترل‌شده انتخاب کرد و Row count، Hash مجموعه
کلید، جمع مقدار، علامت، Null، rounding و bucket وضعیت را با ورودی و Scope یکسان
مقایسه کرد. فقط Aggregate delta و Hash نگهداری شود و تأیید مالک عملیاتی شرط parity
باشد.

## سطح اطمینان و ریسک

- Query identity و declared parameter binding: **تأییدشده**.
- نقش گزارش و مشتق‌بودن Projection: **استنباط قوی**.
- Scope مؤثر Runtime، فرمول نهایی و Result parity: **اثبات‌نشده**.
- ریسک تازه ساخته نشد؛ یافته به `R-002/R-008/R-021/R-023/R-031/R-034` متصل شد.
- هیچ Procedure گزارش اجرا نشد؛ Clone با `READ_ONLY`، `can_update=0` و deny-write
  کنترل شد؛ Assembly فقط با PE/CLR metadata و IL ایستا خوانده شد.
