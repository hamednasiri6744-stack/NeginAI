# دامنه ۱۵: قرارداد رسمی کاردکس و مانده تأمین‌کننده

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی؛ Parity عددی موردی هنوز لازم است**

## منبع شاهد

- Procedure رسمی: `Acc.Usp_GetSupplierRemAmount`
- طول تعریف: ۶۵۳ خط؛ Dynamic SQL با `sp_executesql`
- SHA-256 تعریف:
  `c42fa7d5873dbbda69c6ff3675a22ff6c972c82a3cda7ec7b674357e4fd1a3db`
- Extractor: `scripts/sql/extract_varanegar_supplier_cardex_contract.py`
- Artifact: `artifacts/varanegar_analysis/domains/supplier_cardex_contract_20260826.json`

داده خام تأمین‌کننده، مشتری، سند، چک، حساب، Comment، User/Host و Credential
ذخیره نشده است. Artifact تعریف Procedure، ماتریس بازبینی‌شده شاخه‌ها و جمعیت
کلی منبع‌ها را نگه می‌دارد.

## نتیجه اصلی

مانده تأمین‌کننده حاصل یک جدول نیست:

```text
SupplierBalance(scope)
  = Σ BedAmount(branch 0..26, scope)
  - Σ BesAmount(branch 0..26, scope)
```

`scope` هم‌زمان شامل سال مالی، From/ToDate، DC، SaleOffice، SL، نوع Reason،
IsSettlement، وضعیت سند/چک، Feature Flag و Crosswalkهای Contact/DL/Customer است.
حذف هرکدام از این Gateها می‌تواند عدد را عوض کند.

Procedure ۲۸ Union leg با ۲۷ TitleId از صفر تا ۲۶ دارد؛ TitleId=26 دو بار برای
دو سمت ManualVoucher استفاده شده است.

## ماتریس شاخه‌ها

| ID | عنوان | منبع اصلی | اثر |
|---:|---|---|---|
| ۰ | مانده اول دوره | Supplier | PlusMinus: بدهکار/بستانکار |
| ۱ | فروش | Sale | بدهکار |
| ۲ | فروش مستقیم | POrder/Line | بدهکار |
| ۳ | برگشت فروش مستقیم | POrderRetLine | بستانکار |
| ۴ | تسویه فروش مستقیم | PPayment | بستانکار |
| ۵ | برگشت از فروش | RetSale | بستانکار |
| ۶ | سایر اسناد پرداختی | tblPayments | گروه ۵ بدهکار، سایر بستانکار |
| ۷ | حواله بانکی تخصیص‌یافته | BankOrder/Payments | جهت تابع PayTypeGroup |
| ۸ | چک تسویه فاکتور | PayCheque state view | جهت از State projection |
| ۹ | مانده چک دریافتی | Cheque/Payments | ۴/۵/۹ بدهکار، سایر بستانکار |
| ۱۰ | مانده حواله بانکی | BankOrder/Payments | بستانکار |
| ۱۱ | مانده نقد دریافتی | RCash/Receipt/Payments | بستانکار |
| ۱۲ | پرداخت نقد | Pay/PCash | بدهکار |
| ۱۳ | پرداخت برداشت | Pay/PWithdraw | بدهکار |
| ۱۴ | پرداخت چک | Pay/PCheque/History | ۳/۵ بدهکار، ۲ بستانکار |
| ۱۵ | پرداخت چک سایرین | RCheque assignment | بدهکار |
| ۱۶ | برگشت چک سایرین | RCheque return after 7 | بستانکار |
| ۱۷ | پرداخت گروهی | PayGroup | بدهکار |
| ۱۸ | سند حسابداری | Voucher/VoucherItem | Debit/Bed، Credit/Bes |
| ۱۹ | خرید | SupplierInvoice/Item | بستانکار |
| ۲۰ | برگشت خرید | RetSupplierInvoice/Item | بدهکار |
| ۲۱ | دریافت حواله متفرقه | RCashDraft/Receipt | بستانکار |
| ۲۲ | دریافت چک متفرقه | SupplierCheque state | ۴/۵ بدهکار، سایر بستانکار |
| ۲۳ | دریافت نقد متفرقه | RCash/Receipt | بستانکار |
| ۲۴ | سند تنخواه | Fund/FundItem | بدهکار |
| ۲۵ | اعلامیه بدهکار | Statement | بدهکار |
| ۲۶ | اعلامیه حسابداری | ManualVoucher | هر دو branch فعلی بدهکار |

ماتریس کامل شامل Date/State/Gate هر شاخه در Artifact ثبت شده است.

## Gateهای غیرقابل حذف

### Crosswalk طرف حساب

Procedure ابتدا Supplier را به Contact، DL و در صورت وجود Customer متناظر وصل
می‌کند. بعضی شاخه‌ها با `SupplierRef`، بعضی با `ContactId`، بعضی با `DLCode` و
بعضی با `CustRef` کار می‌کنند. یک Join واحد روی SupplierId جایگزین درست نیست.

### تاریخ و سال مالی

همه شاخه‌ها یک Date rule ندارند:

- فروش/برگشت با AccYear؛
- BankOrder/Receipt با From..ToDate؛
- Payهای غیرتسویه‌ای تا ToDate؛
- Payهای تسویه‌ای، بسته به داشتن Customer متناظر، تا AccYear یا فقط همان سال؛
- Purchase/Return/Fund/Statement با `Date<=ToDate`؛
- Opening balance بدون تاریخ سند.

### وضعیت و قابلیت

- Sale و RetSale ابطال‌شده حذف می‌شوند؛
- نمایش RetSale می‌تواند به Confirmed inventory voucher وابسته باشد؛
- Receipt باید Status تأییدشده یا شماره رسمی داشته باشد؛
- چک دریافتی و پرداختنی با **وضعیت جاری/رخداد** جهت عوض می‌کنند؛
- چک پرداختنی Certified از branch 14 حذف است؛
- سند دستی حسابداری به Feature Flag و VoucherType غیرخارجی وابسته است؛
- همه شاخه‌ها SL/DC/SaleOffice gateهای خاص خود را دارند.

## جمعیت منبع Snapshot

| منبع | جمعیت |
|---|---:|
| Supplier | ۷۵ |
| Sale / RetSale | ۲۷۵٬۹۹۵ / ۱۴٬۰۹۱ |
| tblPayments | ۴۹۳٬۴۹۴ |
| Receipt / RCash / BankDraft | ۶۸٬۶۲۶ / ۱۱٬۰۹۶ / ۱۴۶٬۵۷۶ |
| Pay / PCash / PWithdraw / PCheque | ۳۰٬۳۲۲ / ۱٬۶۸۴ / ۲۹٬۰۸۳ / ۴٬۶۷۲ |
| Voucher / VoucherItem | ۲۰۵٬۹۴۴ / ۱٬۳۸۵٬۶۹۴ |
| SupplierInvoice / Item | ۳٬۴۲۶ / ۳۰٬۰۹۶ |
| SupplierReturn / Item | ۴۶۷ / ۳٬۵۱۸ |
| Statement | ۱٬۳۸۴ |

مسیرهای `POrder/PPayment`، `PayGroup`، `Fund/FundItem` و `ManualVoucher` در
Snapshot صفرند. صفر بودن داده فقط وضعیت فعلی است؛ Branch رسمی و Golden Case
آن‌ها باید حفظ شود.

## یافته نیازمند تأیید

دو Union leg آخر، یکی با `ManualVoucher.DebitContactId` و دیگری با
`CreditContactId`، هر دو:

- `TitleId=26`؛
- عنوان «اعلامیه حسابداری»؛
- `Amount -> BedAmount`.

ممکن است این جهت به معنای خاص دامنه یا یک رفتار تاریخی باشد. چون هیچ داده
فعلی ManualVoucher وجود ندارد، از Snapshot امکان داوری عددی نیست. مقصد فعلاً
باید این قرارداد را به‌عنوان `source_behavior_unconfirmed` نگه دارد و بدون
تأیید حسابداری آن را به Credit/Bes تغییر ندهد.

## مدل مقصد

- `SupplierLedgerEntry` Append-only با `source_type/source_id/title_id`؛
- `SupplierPartyCrosswalk` برای Supplier/Contact/DL/Customer؛
- `LedgerDirectionRuleVersion` برای جهت هر Branch و State؛
- `LedgerScope` برای AccYear/Date/DC/SaleOffice/SL/flags؛
- `SupplierBalanceProjection` با فرمول Bed-Bes؛
- `SourceStateSnapshot` برای وضعیت چک/سند در زمان Projection؛
- `ProjectionBuildRun` با Procedure hash و ورژن Rule؛
- `ReconciliationDifference` برای اختلاف منبع/مقصد بدون اصلاح خودکار.

هر Entry باید Idempotency Key از `(source_type, source_id, event/version)` داشته
باشد. تغییر وضعیت چک باید Entry معکوس/جدید بسازد؛ Update تاریخی جهت قبلی ممنوع.

## برنامه Parity

1. انتخاب Golden Supplier برای هر شاخه فعال و هر نوع Crosswalk.
2. اجرای کنترل‌شده Procedure رسمی با AccYear/DC/SaleOffice/SL مشخص.
3. خروجی فقط در سطح جمع مانده و جمع شاخه، بدون داده هویتی خام.
4. اجرای Projection مقصد با همان Scope و Procedure hash.
5. الزام برابری `ΣBed-ΣBes` و نیز برابری هر TitleId.
6. Quarantine اختلاف با Source contribution count؛ بدون Auto-adjustment.
7. ساخت داده کنترل‌شده برای چهار مسیر خالی و دو branch TitleId=26.

## ابهام‌های باز

1. جهت مورد انتظار CreditContact در ManualVoucher/TitleId=26.
2. Exact semantics سه Feature Flag داخلی Procedure.
3. تفاوت Contact/DL/Customer برای Supplierهایی که Customer متناظر ندارند.
4. دلیل کاربرد Sale و RetSale در حساب Supplier-Customer دووجهی.
5. Parity عددی چند Supplier منتخب؛ حساب تحلیل فعلی EXEC ندارد و باید Query
   replica یا خروجی کنترل‌شده از اپلیکیشن رسمی تهیه شود.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_supplier_cardex_contract.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\supplier_cardex_contract_20260826.json
```
