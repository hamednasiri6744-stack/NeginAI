# مرز Authorization و Resource Scope تبدیل سفارش به فروش

تاریخ استخراج: ۲۰۲۶-۰۸-۲۹  
وضعیت: **SQL Clone فقط‌خواندنی + IL ایستای Hash-pinned؛ اجرای عملیاتی صفر**

## نتیجهٔ کوتاه

در مسیر منتخب تبدیل سفارش به فروش، مجوز مستقل Action با معنای
`ConvertOrderToSale` اثبات نشد. Type دقیق `FormOrderToSale` هیچ Member call نام‌دار
Permission/Access ندارد و هفت متد منتخب UI/Business/Adapter تبدیل نیز چنین Gateای
ندارند. این نتیجه نبود مجوز در Menu، BaseForm یا لایهٔ بیرونی را ثابت نمی‌کند،
اما نشان می‌دهد دسترسی به صفحه یا Helper عمومی حقوق سفارش را نمی‌توان مجوز
Server-side فرمان وب دانست.

سرور یک Scope محدود ناحیهٔ فروش دارد، ولی فقط وقتی کلید سراسری `AreaAccess=1`
باشد. در Clone فعلی این کلید فعال نیست و GeneralConfig نیز `AreaAccess=false`
است. پس وجود دو ردیف Projection دسترسی ناحیه، به‌تنهایی Gate جاری ایجاد نمی‌کند.

## حقوق نوع سفارش

`usp_sdsnet_Order_OrderTypePermission` Actor، ActionType و OrderType را می‌گیرد و
سه منبع را بررسی می‌کند:

- Admin؛
- Right مستقیم کاربر؛
- Right گروه کاربر.

Actionهای مستندشده در Procedure عبارت‌اند از View، New، Edit، Delete، Cancel،
Confirm و Unconfirm. Action مستقلی برای Convert/CreateSale وجود ندارد.

اسکن کل `VN.SDS.Sales.UI.dll` ده Callsite این Helper را پیدا کرد که همگی در
`FormOrderList` یا `FormLoanOrderList` و برای View/Edit/Delete/Cancel/Confirm-
Unconfirm هستند. `FormOrderToSale` Callsite ندارد. Adapter نیز Actor را از
`UserSessionInfo` می‌گیرد و Procedure حقوق نوع سفارش را صدا می‌زند، اما این مسیر
به فرمان تبدیل متصل نشده است.

## Scope ناحیهٔ فروش در Wrapper

Wrapper پیش از فراخوانی Core، Procedure
`usp_sdsnet_CreateSaleByOrder_CheckAreaAccess` را صدا می‌زند. Gate فقط در صورت
وجود تنظیم سراسری `tblServerConfig: AreaAccess=1` فعال می‌شود. وقتی فعال باشد،
ناحیهٔ مشتری باید در `vwSaleUserAccess` همان User باشد؛ مشتری بدون SaleArea نیز
صریحاً مجاز عبور می‌کند.

این Scope فقط رابطهٔ User/Customer/SaleArea را می‌سنجد و به‌تنهایی موارد زیر را
اثبات نمی‌کند:

- مجوز Action تبدیل؛
- Scope مرکز، دفتر فروش، انبار یا عامل؛
- مجوز تبدیل جزئی موجودی؛
- مجوز Override اعتبار/سقف؛
- مجوز تغییر تاریخ عملیات.

Core پارامتر `UserRef` دارد و آن را در ساخت فروش/اثرهای بعدی مصرف می‌کند، اما
Dependency یا Branch نام‌دار Permission/Right/Access در Core منتخب ندارد. پذیرش
Actor به‌عنوان پارامتر، Authorization نیست و ERP وب نباید Actor را از Payload
Client بپذیرد.

## Snapshot ناشناس فعلی

- کلید فعال `tblServerConfig.AreaAccess=1`: صفر؛
- GeneralConfig: یک ردیف و صفر مقدار AreaAccess=true؛
- Projection دسترسی ناحیه فروش: دو ردیف؛
- Right مستقیم نوع سفارش: ۱۹۰ ردیف؛
- Right گروهی نوع سفارش: ۱۲۰ ردیف.

هیچ User ID، Group ID یا نگاشت هویتی ذخیره نشد. این شمارش‌ها فقط وجود دادهٔ
پیکربندی را نشان می‌دهند و Effective permission هیچ Identity را ثابت نمی‌کنند.

## قرارداد مقصد

Actionهای مستقل حداقل چنین باشند:

| Action | Scope لازم |
|---|---|
| `ConvertOrderToSale` | DC، SaleOffice، OrderType، Customer/SaleArea و Order |
| `ConvertOrderToSalePartially` | Scope بالا + StockDC + مجوز ویژه |
| `OverrideCustomerOrDealerCredit` | Scope بالا + Reason + PolicyVersion |
| `SetSaleOperationDate` | DC، AccYear، Sale system + Reason |

- Actor فقط از Principal احراز‌شدهٔ سرور استخراج شود؛ `UserRef` Payload ممنوع.
- هر Command پیش از خواندن/نوشتن مالی، Action و Resource scope را Server-side و
  deny-first ارزیابی کند.
- خاموش‌بودن AreaAccess نباید به «همهٔ Scopeها مجازند» ترجمه شود؛ Scope مقصد یک
  قرارداد مستقل و اجباری است.
- مشتری بدون SaleArea به حالت `UNSCOPED_CUSTOMER` برود و Policy صریح داشته باشد؛
  عبور ضمنی Legacy کپی نشود.
- Decision شامل Actor، Action، Resource set، Policy version، Rule evidence و
  نتیجهٔ allow/deny در Audit تغییرناپذیر ثبت شود.

Golden caseها باید direct/group/admin، بدون Right، cross-DC، cross-office،
cross-area، مشتری بدون ناحیه، نوع سفارش غیرمجاز، تبدیل جزئی و Override را پوشش
دهند. آزمون منفی مستقیم API باید ثابت کند دسترسی به صفحه جای مجوز فرمان نیست.

## سطح اطمینان و محدودیت

- نبود Call نام‌دار در Type دقیق فرم و متدهای منتخب: **تأییدشده**.
- Scope شرطی AreaAccess و مدل حقوق نوع سفارش: **تأییدشده** از SQL/IL.
- نبود Authorization در BaseForm/Menu/Endpoint/Proxy بیرونی: **اثبات‌نشده**.
- تنظیم Clone، وضعیت Production یا Effective right کاربران: **اثبات‌نشده**.
- هیچ دسترسی غیرمجاز واقعی یا exploit جاری ادعا نشده است؛ این یک مرز طراحی
  Server-side برای مهاجرت است.

## ایمنی و بازتولید

- Clone `READ_ONLY` و Login فاقد Write بود؛
- هیچ Procedure، فرم یا Command اجرا نشد؛
- سه Assembly فقط با PE/IL خوانده شدند و Load/Execute نشدند؛
- هیچ Identity، متن SQL خام، پیام یا مقدار حساس در Artifact ذخیره نشد.

خروجی‌ها:

- `scripts/sql/extract_varanegar_order_sale_authorization_sql.py`
- `scripts/sql/extract_varanegar_order_sale_authorization_runtime.py`
- `artifacts/varanegar_analysis/domains/order_sale_authorization_sql_20260829.json`
- `artifacts/varanegar_analysis/domains/order_sale_authorization_runtime_20260829.json`
- `tests/test_varanegar_order_sale_authorization_boundary.py`
