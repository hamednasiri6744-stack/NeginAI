# قرارداد Dataset و Queryهای Discount V2

## نتیجه اجرایی

موتور Discount V2 یک query واحد یا snapshot اتمیک نمی‌خواند. Type ایستای
`AdvanceDCalDiscount.QueryHelper` دقیقاً ۴۲ template فقط‌خواندنی دارد. در مسیر
منتخب سفارش، `InitialCalcData` و `ExtractCalcDataFromDB` مجموعاً ۳۵ call مستقیم
DataContext دارند و Context نیز `Transaction.No` است. بنابراین هر command مستقل
اجرا می‌شود.

Clone فعلی RCSI را روشن و Snapshot Isolation را مجاز دارد؛ این موضوع dirty read را
در حالت معمول کم می‌کند، اما چون کل محاسبه داخل یک transaction snapshot نیست، هر
statement می‌تواند snapshot زمانی متفاوت ببیند. تغییر هم‌زمان قیمت، CPrice، تخفیف،
ممنوعیت فروش، موجودی یا خود سفارش می‌تواند یک CalcData ترکیبی بسازد. این یک ریسک
ساختاری consistency است؛ وقوع اختلاف تاریخی از این شاهد نتیجه‌گیری نمی‌شود.

## نقشه‌ی ورودی‌ها

از ۴۲ template:

- ۱۷ template مرجع/Rule هستند: گروه و نوع مشتری، Discount و DiscountGoods،
  CPrice/Price، Goods و گروه/نوع/واحد ثابت، GoodsNoSale، PrizeList، GoodsPackage،
  FreeReason، Package، PaymentUsance و DisAcc.
- ۱۰ template مخصوص درخواست سفارش هستند: Customer، OrderHdr/Item/Prize، StockGoods،
  EVC header/item، SaleHdr/Item و SaleItemPaymentUsance.
- ۱۵ template برای مسیرهای فروش/برگشت/مقایسه و diagnostic هستند، از جمله
  RetOrder/RetSale، DisSale، EVC sale/ret-item، Unit و SaleHdrDetailTime.

Dependency lexical برابر ۴۴ object است: سه جدول موقت EVC و ۴۱ object پایدار.
هر ۴۱ object پایدار در catalog clone حل شد: ۴۰ جدول و یک view. مجموع row-count
پارتیشن جدول‌های ارجاع‌شده حدود ۷٬۹۱۹٬۲۷۲ است؛ این جمع scale است و activity یا
selectivity query نیست. بزرگ‌ترین منابع شامل SaleItm، DisSale، OrderItm،
SaleHdrDetail، DisSalePrizePackage، SaleHdr و OrderHdr هستند.

## ساخت Query

هر ۴۲ مقدار با الگوی دقیق `ldstr → stsfld` در `.cctor` ساخته می‌شود؛ raw SQL در
Artifact ذخیره نشده و فقط hash، طول، placeholder و dependency نگه داشته شده است.
۲۷ template دارای ۳۱ slot قالب‌بندی `String.Format` هستند. هیچ template منتخب
`EXEC` یا keyword نوشتن ندارد و `SELECT *` مستقیم نیز مشاهده نشد.

این شاهد به‌تنهایی SQL injection را ثابت نمی‌کند؛ بسیاری از ورودی‌ها عدد یا تاریخ
اعتبارسنجی‌شده‌اند. با این حال، متن‌سازی query contract ضعیف‌تری از parameter binding
است و plan reuse، type safety و audit را سخت‌تر می‌کند. مقصد باید parameterized SQL،
TVP یا stored-query contract نسخه‌دار داشته باشد.

## قرارداد هدف ERP نگین

- ابتدای قیمت‌گذاری، `PricingSnapshotId` با `AsOfVersion` واحد گرفته شود.
- تمام Rule/master و request data در یک transaction snapshot یا read model نسخه‌دار
  خوانده شوند؛ statement-level RCSI کافی تلقی نشود.
- cache فقط برای Rule/master و با کلید حداقل DC، effective date، price-list version،
  discount-rule version و invalidation event مجاز باشد.
- Order/Customer/Stock/Sale state هرگز در cache سراسری Rule ادغام نشود.
- query budget، latency، row-count و cache hit/miss telemetry ثبت شود.
- Golden test تغییر هم‌زمان Price/Discount/Stock بین دو read را inject کند و ثابت
  کند یک snapshot مخلوط تولید نمی‌شود.

## شواهد قابل بازتولید

- `artifacts/varanegar_analysis/domains/discount_v2_query_contracts_20260829.json`
- `artifacts/varanegar_analysis/domains/discount_v2_dataset_sql_20260829.json`
- `artifacts/varanegar_analysis/domains/datacontext_transaction_runtime_20260829.json`
- `artifacts/varanegar_analysis/domains/order_sale_evc_runtime_boundary_20260829.json`

اسمبلی Load/Execute نشد، Procedure یا فرم عملیاتی اجرا نشد و SQL فقط catalog،
database options و aggregateهای پارتیشن را خواند.
