# Call graph فرم‌های پرتراکم وارانگار تا Business/DataAccess

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۱۲ فرم، ۸۷ Business type و ۴۳ DataAccess type؛ همه پیدا شدند**

## انتخاب

دوازده فرم با اولویت بازبینی بالا و بیشترین اتصال غیرسیستمی انتخاب شدند:
Discount، Order، RetSale، LoanOrder، SupplierInvoice، FreeInvoice، Customer،
Stock Voucher، Goods، RetOrderSale، Contract-price wizard و Supplier Return.

شش Assembly Business/DataAccess رسمی از Runtime share فقط به‌صورت PE/IL خوانده
شدند. Hash همه با Inventory قبلی برابر بود؛ Assembly Load/Execute، DB connection،
UI action و Command اجراشده صفر بود.

## پوشش

- ۱۴۰ Edge از فرم به ۸۷ Business type در سه Assembly؛
- ۴۵ Edge از Business به ۴۳ DataAccess type در سه Assembly؛
- ۱٬۰۶۸ Method body در Business و ۳۷۵ Method body در DataAccess؛
- صفر Type گمشده، صفر Parse error و صفر Source hash mismatch؛
- ۱۹ Business type دارای Persistence signal؛
- ۹ Business type دارای Transaction/Commit signal.

## Transaction ownership

هر دوازده فرم در UI یا یکی از Business typeهای فراخوانی‌شده حداقل یک
`DataContext.Commit`/Transaction signal دارند. ده فرم Commit مستقیم UI دارند؛
Contract-price wizard از `CPriceHandler` و Stock Voucher از
`VocherHdrHandler` به Commit می‌رسند.

این کشف Atomicity انتها‌به‌انتها را ثابت نمی‌کند. در Order، RetSale و
SupplierInvoice چند Handler مستقل درگیرند و بعضی مسیرها هم Commit UI و هم Commit
Business دارند. برای مقصد Transaction owner باید یک Application command باشد؛
Handlerهای زیرمجموعه نباید مستقل و نامنسجم Commit کنند.

## مرزهای دامنه‌ای مهم

- Order به EVC، Discount، Batch، Credit، Dist و Sale وابسته است؛
- RetSale علاوه بر Sale/Order به EVC، تخفیف، Batch و Dist status متصل است؛
- SupplierInvoice به Supplier balance، ICA voucher، Buy toll، قیمت خرید و Sale
  item وابسته است؛
- Stock Voucher به Batch، Goods/Barcode، StockDC، Supplier، Sale و Dist وصل است؛
- Goods فقط Master ساده نیست: Package، BatchPackage، Supplier، Accounting group،
  DC allocation و validation حذف دارد؛
- Discount اولویت/کد تولید می‌کند، Ruleها را فعال/غیرفعال می‌کند و Prevent-sale
  و Prize unit را هم درگیر می‌کند؛
- Customer به چند Route namespace، Credit/Account، DC dependency و مجوزهای
  Stock access متصل است.

پس Aggregate مقصد نباید از روی فرم نام‌گذاری شود. UI یک Orchestrator است و
مالکیت داده میان Master, Pricing, Sales, Inventory, Distribution, Treasury و
Accounting باید مطابق Blueprint جدا بماند.

## اثر روی ترتیب ساخت

1. Goods/Customer باید Import و Read-only parity داشته باشند قبل از Order؛
2. Pricing/EVC/Discount trace باید قبل از فعال شدن Save سفارش کامل شود؛
3. Order و RetSale به Golden calculation و failure-injection چندماژولی نیاز دارند؛
4. SupplierInvoice بدون Stock/ICA/Supplier balance آماده Command نیست؛
5. Stock Voucher باید Ledger-first و Rebuildable باشد و Command مستقیم جدول
   مقصد نداشته باشد.

## مرز نتیجه

Call مستقیم IL ممکن است مسیرهای ارث‌بری، Interface، Reflection، ORM یا Event را
نبیند. Transaction signal در یک Type نیز Atomicity کل زنجیره را اثبات نمی‌کند؛
این Artifact اولویت و مرز Trace را تعیین می‌کند، نه مجوز تولید.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/varanegar_high_impact_call_graph_20260827.json`
- `scripts/windows/extract_varanegar_high_impact_call_graph.py`
- `tests/test_varanegar_ui_evidence.py`
