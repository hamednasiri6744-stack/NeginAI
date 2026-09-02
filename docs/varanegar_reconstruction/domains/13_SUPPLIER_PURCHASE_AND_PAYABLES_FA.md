# دامنه ۱۳: خرید از تأمین‌کننده، مرجوعی خرید و بدهی تأمین‌کننده

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- منبع: `127.0.0.1 / NeginPakhsh_WebDev`
- وضعیت دیتابیس: `READ_ONLY`
- حساب تحلیل با `UPDATE=0` و عضویت در `db_denydatawriter` کنترل شد.
- Extractor قابل تکرار:
  `scripts/sql/extract_varanegar_supplier_purchase_domain.py`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/supplier_purchase_and_payables_20260826.json`

این مرحله ۲۰ جدول پایه، ۸۱ FK رسمی، ۱٬۴۳۷ مصرف‌کننده ماژولی، ۲۵ ارتباط
ضمنی و ۱۱ قرارداد SQL منتخب را بررسی کرده است. ردیف هویتی/تماس/مالیاتی
تأمین‌کننده، Comment، User/Host، Credential، شناسه ابزار پرداخت و ردیف خام
Settlement در Artifact ذخیره نشده است.

## نتیجه اصلی: خرید یک Workflow سه‌مرحله‌ای است

```text
رسید انبار نوع 20، Confirmed
        │
        ├─ ICA.tblSupInvInvoiceRelation [1..7]
        │          │
        │          └─ ICA.TblSupInvoiceHdr / Itm / Tolls
        │                         │
        │                         └─ Status 0: مرتبط/اعمال نشده
        │                            Status 1: مرتبط/اعمال شده
        │
        └─ ICA.usp_ApplySupInvoice
                   ├─ Inv.tblVocherItmPrice
                   ├─ Buy-price history
                   └─ inventory cost correction

مرجوعی خرید
  └─ ICA.tblRetSupInvoiceHdr.InvVocherRef
       └─ خروج قطعی انبار نوع 55

کاردکس تأمین‌کننده
  └─ Acc.Usp_GetSupplierRemAmount (چندمنبعی)
```

ایجاد/تأیید رسید انبار، اتصال فاکتور خرید و اعمال قیمت تمام‌شده سه مفهوم مستقل
هستند. مقصد نباید آن‌ها را در یک Boolean به نام «تأیید خرید» ادغام کند.

## جمعیت فاکتورهای خرید

`ICA.TblSupInvoiceHdr` تعداد ۳٬۴۲۶ فاکتور برای ۶۳ تأمین‌کننده دارد:

| Status | معنی عملی | فاکتور | ConfirmDate | بازه VchDate |
|---:|---|---:|---:|---|
| ۰ | مرتبط/اعمال نشده | ۱۴۱ | ۰ | ۱۴۰۵/۰۵/۰۱..۱۴۰۵/۰۵/۲۶ |
| ۱ | مرتبط/اعمال شده | ۳٬۲۸۵ | ۳٬۲۸۵ | ۱۴۰۳/۰۱/۱۹..۱۴۰۵/۰۴/۳۱ |

- Supplier، DC و Currency یتیم: صفر؛
- CurrencyRef همه پر و ExchangeRate همه برابر ۱؛
- `TSupInvoiceRef` در Snapshot فعلی مصرف نشده؛
- ۳٬۳۹۳ فاکتور `IsNew=1` و ۳۳ فاکتور اعمال‌شده Legacy هستند؛
- `TasviehDate` در همه فاکتورها خالی است و منبع قابل‌اعتماد تسویه نیست.

۱۴۱ فاکتور Status=0 نیز همگی به رسیدهای انبار Confirmed وصل‌اند. بنابراین
Status=0 به‌معنی «کالا دریافت نشده» نیست؛ فقط هنوز Apply/Link مالی خرید کامل
نشده است.

## اقلام و قرارداد مبلغ

۳۰٬۰۹۶ Item برای ۳٬۲۲۴ کالا وجود دارد:

- Qty همه مثبت و PrizeQty در همه صفر؛
- Header، Goods و Unit یتیم: صفر؛
- UUID/ردیف هویتی خام در Artifact نگهداری نشده؛
- فرمول ساده `Amount = Qty × Price` برای ۳۰٬۰۶۲ ردیف درست و برای ۳۴ ردیف
  متفاوت است.

۳۴ اختلاف اخیر خطای قطعی نیست. قرارداد رسمی
`ICA.usp_ValidateSupInvoiceAmount` برای کالاهای نوع ۲/۳ استثنا دارد و برای
سایر کالاها قیمت واحد را با `Qty-PrizeQty`، ExchangeRate، تقسیم بر ۱۰ و
Floor/Round کنترل می‌کند. با همان فرمول رسمی هر ۳۰٬۰۹۶ ردیف معتبر است.

پس Rule مقصد باید نسخه‌گذاری‌شده و مبتنی بر `GoodsType` باشد؛ اعتبارسنجی ساده
ضرب تعداد در قیمت، خریدهای معتبر قدیمی را رد می‌کند.

## رابطه فاکتور خرید با رسید انبار

`ICA.tblSupInvInvoiceRelation` تعداد ۳٬۶۸۹ رابطه دارد:

- هر ۳٬۴۲۶ فاکتور حداقل یک Relation دارد؛
- ۳٬۲۱۷ فاکتور دقیقاً یک رسید و ۲۰۹ فاکتور چند رسید دارند؛
- بیشینه هفت رسید برای یک فاکتور است؛
- ۳٬۶۸۸ رسید متمایز مصرف شده؛ ۳٬۶۸۷ رسید به یک فاکتور و یک رسید به دو
  فاکتور وصل است؛
- همه Voucherها نوع ۲۰ و Confirmed هستند؛
- Invoice/Voucher یتیم، Supplier mismatch و AccYear mismatch صفر؛
- `Voucher.DCRef` برای ۱٬۰۷۳ رابطه خالی و برای ۲٬۶۱۶ رابطه پر و منطبق است.

نسبت ۱:N و مورد N:1 واقعی است؛ بنابراین Uniqueکردن اجباری Relation روی یکی
از دو Ref، داده معتبر را از بین می‌برد. مورد یک رسید/دو فاکتور باید در Golden
Dataset حفظ شود.

### تطبیق مقدار کالا

مقایسه‌ی قدیمی per-invoice پنج Receipt-only group در دو فاکتور می‌ساخت، اما
این هشدار کاذب بود: یک رسید به دو فاکتور وصل است و اقلام فاکتور دیگر در مقایسه
جداگانه اضافه دیده می‌شد. با ساخت ۳٬۴۲۵ Connected component از ۳٬۶۸۹ Relation،
هر پنج مورد توضیح داده شد و ۳۰٬۰۹۶ گروه `(component, goods)` دقیق با Receipt-only،
Invoice-only و اختلاف مقدار صفر به‌دست آمد.

`ICA.usp_ApplySupInvoice` نیز کل Invoice list و Voucher list ورودی را بر اساس
Goods جمع می‌کند، نه هر Relation را مستقل. بنابراین پنج مورد Quarantine نیستند؛
Relation N:M حفظ و فقط Residual سطح Component بازبینی می‌شود. قرارداد کامل:
`SUPPLIER_RECEIPT_COMPONENT_DIAGNOSTIC_20260827_FA.md`.

جدول‌های Legacy `dbo.POrder` و `dbo.POrderLine` هر دو خالی‌اند و هیچ رسید نوع
۲۰ `PurchaseOrderRef` ندارد. در این Clone، مسیر فعال از سفارش خرید Legacy
عبور نمی‌کند؛ ولی صفر بودن داده مجوز حذف Capability تاریخی نیست.

## عوارض، اضافات/کسورات و قیمت تمام‌شده

فاکتور خرید ۷٬۵۱۶ Toll و ۶۲٬۶۷۰ تخصیص Toll به ۲۶٬۶۹۶ Item دارد:

- Toll یا Item یتیم: صفر؛
- Allocation میان دو Invoice متفاوت: صفر؛
- `HeaderToll.UserPrice` با جمع علامت‌دار Allocationها برای هر ۷٬۵۱۶ Toll
  دقیقاً برابر است؛
- EffectiveAddition، EffectiveDiscount، OtherAddition و OtherDiscount برای
  هر ۲۶٬۶۹۶ Item دارای Toll با جمع رسمی Allocationها دقیقاً تطبیق دارند؛
- اختلاف در هر دو سطح صفر است.

منطق طبقه‌بندی رسمی:

```text
AffectionOnStockReceipt=1, IsAdding=1  -> EffectiveAddition
AffectionOnStockReceipt=1, IsAdding=0  -> EffectiveDiscount
AffectionOnStockReceipt=0, IsAdding=1  -> OtherAddition
AffectionOnStockReceipt=0, IsAdding=0  -> OtherDiscount
```

`ICA.usp_ApplySupInvoice` مبلغ `FinalEffectiveAmount` را روی
`Inv.tblVocherItmPrice` توزیع می‌کند، قیمت خرید را به‌روز می‌کند، قیمت مؤثر
واحد کمتر از یک را رد می‌کند و اختلاف گردکردن را اصلاح می‌کند. این عملیات
باید Command اتمیک، Idempotent و Auditدار باشد؛ محاسبه در UI یا Update مستقیم
قیمت انبار مجاز نیست.

## مرجوعی خرید

۴۶۷ Header و ۳٬۵۱۸ Item مرجوعی برای ۵۱ تأمین‌کننده وجود دارد:

- Supplier و Currency همه پر؛
- ۳۷۴ Header جدید و ۹۳ Legacy؛
- همه ۴۶۷ Header مستقیماً `InvVocherRef` معتبر دارند؛
- همه Voucherها نوع ۵۵، Confirmed، هم‌سال و DC منطبق‌اند؛
- هر ۳٬۵۱۸ Item Qty مثبت دارد و Header/Goods یتیم صفر است؛
- `TotalAmount = EffectiveAmount + OtherAddition - OtherDiscount` برای همه
  Itemها دقیق است؛
- مجموع `TotalAmount` و `FinalEffectiveAmount` برای هر ۴۶۷ Header برابر است؛
- مجموع مالی مرجوعی‌ها ۲۹۴٬۵۰۹٬۰۷۹٬۳۷۰ واحد پولی است.

مقدار `(Return,Goods)` برای هر ۳٬۵۱۸ گروه با Voucher خروج نوع ۵۵ دقیقاً برابر
است؛ اختلاف، Return-only و Voucher-only صفر.

فقط ۲۷ مرجوعی `SupInvoiceRef` دارند. در آن‌ها ۱۵۶ گروه کالا وجود دارد: ۱۴۹
گروه در فاکتور منبع و در محدوده Qty منبع است، هفت گروه در فاکتور منبع پیدا
نمی‌شود و هیچ گروه تطبیق‌شده‌ای بیش از Qty منبع نیست.

نتیجه: `SupInvoiceRef` منشأ اختیاری است، نه شرط ایجاد مرجوعی. حقیقت عملیاتی
مرجوعی، `InvVocherRef` نوع ۵۵ است. تشخیص تازه هر هفت گروه بدون Source match را
با خروج نوع ۵۵ دقیق یافت و IL فرم نیز بارگذاری Item از سند انبار را ثابت کرد؛
Invoice فقط Hint قیمت/منشأ است. State آن‌ها
`OPTIONAL_SOURCE_ITEM_ABSENT_NOT_AN_INVENTORY_ERROR` است؛ Price/Amount تاریخی
حفظ و Reassign/Reprice حدسی از فاکتور قبلی ممنوع است.

## تسویه و کاردکس تأمین‌کننده

`Acc.tblSupSettlement` فقط دو ردیف برای یک تأمین‌کننده و دو فاکتور دارد:

- هر دو مبلغ مثبت، Invoice/Supplier معتبر و Customer mismatch صفر؛
- یک ردیف نوع ۳ «چک سایرین» و یک ردیف نوع ۴ «برداشت»؛
- یکی با received-cheque و دیگری با withdrawal؛
- هر دو `DocPayId` دارند؛
- هیچ Cash یا payable-cheque مستقیمی در این دو ردیف نیست؛
- هر دو فاکتور فقط بخشی تسویه شده‌اند؛ ۳٬۴۲۴ فاکتور هیچ Allocation مستقیم
  ندارند و هیچ فاکتور fully/over-settled نیست.

هشت نوع فعال و Manual در Master تعریف شده است: نقد، چک پرداخت، چک سایرین،
برداشت، برگشت فاکتور خرید، سند عمومی تأمین‌کننده، فاکتور فروش و اعلامیه
حسابداری. همه `PlusMinus=1` دارند؛ جهت بدهکار/بستانکار از Source contract نیز
می‌آید و نباید فقط از این ستون حدس زده شود.

این اعداد به‌معنی «فقط دو پرداخت به تأمین‌کننده» نیست. Procedure رسمی
`Acc.Usp_GetSupplierRemAmount` مانده را از مجموعه بزرگی از منابع می‌سازد:

- مانده اول دوره؛
- فاکتور خرید و مرجوعی خرید؛
- وجه نقد، چک پرداختنی، چک دریافتی واگذارشده و برداشت؛
- فروش/سفارش‌های دارای تأمین‌کننده؛
- سند عمومی و سند دستی حسابداری؛
- Allocationهای `tblSupSettlement` و برگشت ابزارها.

پس `tblSupSettlement` فقط Allocation Bridge است. بازسازی حساب پرداختنی با جمع
دو ردیف این جدول، مانده تأمین‌کننده را غلط می‌کند. مقصد باید Supplier Cardex
Append-only و Projection قابل بازسازی داشته باشد.

## سه ماه اخیر Clone

در پنجره `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱`:

| رخداد | تعداد |
|---|---:|
| فاکتور خرید | ۴۶۴ |
| Item خرید | ۴٬۲۵۵ |
| تأمین‌کننده فعال | ۳۶ |
| مرجوعی خرید | ۵۰ |
| Item مرجوعی | ۳۹۳ |
| Relation فاکتور/رسید | ۵۰۱ |
| Allocation مستقیم تسویه | ۲ |

این پنجره نشان می‌دهد دامنه خرید و مرجوعی فعال است؛ کم‌بودن Settlement مستقیم
به‌علت چندمنبعی‌بودن کاردکس است، نه نبود پرداخت.

هر ۵۰ مرجوعی این پنجره `IsNew=1` هستند؛ Header مسیر Legacy صفر است. فقط یک
Header به Source invoice وصل است و پنج گروه کالای همان Header در قلم Source
پیدا نمی‌شوند، درحالی‌که Explicit TollRef قدیمی در سه ماه اخیر صفر است. پس
Guard مقصد باید شکاف Validator مسیر SDSNET جدید را مسئلهٔ جاری بداند، اما ۲۰
TollRef قابل‌بازیابی را به‌عنوان وضعیت مهاجرتی Legacy نگه دارد.

## قرارداد اولیه مدل مقصد

حداقل موجودیت‌ها و قواعد:

- `SupplierPurchaseInvoice` با State مستقل `Draft/Unapplied/Applied`؛
- `SupplierPurchaseInvoiceLine` با Amount contract نسخه‌گذاری‌شده؛
- `PurchaseReceiptLink` با cardinality چندبه‌چند کنترل‌شده؛
- `PurchaseToll` و `PurchaseLineTollAllocation`؛
- `InventoryCostApplication` با Command اتمیک و Idempotency Key؛
- `InventoryItemCostLayer` یا Crosswalk به قیمت Item انبار؛
- `SupplierPurchaseReturn` و Line؛
- `SupplierReturnInventoryExitLink` اجباری و SourceInvoiceLink اختیاری؛
- `SupplierLedgerEntry` چندمنبعی و Append-only؛
- `SupplierInvoiceAllocation` برای تخصیص ابزار بدهکار به Invoice؛
- `SupplierBalanceProjection` قابل بازسازی؛
- `SourceCrosswalk` برای Header/Item/Voucher/Toll/Settlement Legacy.

اعمال فاکتور خرید باید Linkها و Qty را کنترل کند، Tollها را تطبیق دهد، قیمت
مؤثر را محاسبه کند، Cost layer را در یک Transaction بنویسد و Retry تکراری را
با Idempotency مهار کند. UI فقط فرمان می‌دهد و نتیجه Projection را می‌خواند.

## Golden Caseهای لازم

1. یک فاکتور روی یک رسید Confirmed و سپس Apply هزینه.
2. یک فاکتور روی چند رسید و حفظ ترتیب/جمع Qty.
3. یک رسید متصل به دو فاکتور با Review صریح.
4. فاکتور Status=0 که رسید Confirmed دارد.
5. پنج False positive مقایسهٔ per-invoice که در Component N:M دقیق‌اند.
6. هر چهار نوع اثر Toll و تطبیق Header/Item.
7. ۳۴ Item که ضرب ساده را رد ولی فرمول رسمی قبول می‌کند.
8. Retry Apply بدون Cost layer یا BuyPrice تکراری.
9. مرجوعی مستقل بدون SupInvoiceRef ولی با خروج نوع ۵۵.
10. مرجوعی متصل به SourceInvoice با Qty در محدوده.
11. هفت Goods بدون Source match ولی دقیق با خروج نوع ۵۵؛ حفظ Price provenance.
12. تسویه جزئی با دو ابزار مختلف و یک Projection مانده.
13. محاسبه مانده از Invoice + Return + Instrument + Manual Voucher.
14. Reverse ابزار پرداخت و بازسازی مانده بدون Update تاریخی.

## ابهام‌های باز

1. نیت/علت کسب‌وکاری یک Receipt مشترک میان دو Supplier Invoice، با وجود Reconciliation دقیق.
2. منشأ تاریخی Price/Amount غیرصفر هفت Goods بدون Item در Source Invoice.
3. مسیر واقعی صدور سفارش خرید در نسخه جاری، چون POrder Legacy خالی است.
4. تفاوت دقیق گزارش `SupplierCredit_GetList` با Cardex جامع در نسخه‌های دارای
   `InEffectiveOnSupplier` غیرصفر؛ مقدار فعلی همه صفر است.
5. قرارداد Reverse/Unapply قیمت تمام‌شده و محدودیت حذف پس از مصرف موجودی.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_supplier_purchase_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\supplier_purchase_and_payables_20260826.json
```
