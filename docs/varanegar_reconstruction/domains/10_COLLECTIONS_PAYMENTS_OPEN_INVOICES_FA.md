# دامنه ۱۰: وصول، ابزار دریافت، تخصیص پرداخت و مانده باز

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- منبع: `127.0.0.1 / NeginPakhsh_WebDev`
- وضعیت دیتابیس: `READ_ONLY`
- حساب تحلیل از نظر `UPDATE=0` و عضویت در `db_denydatawriter` کنترل شد؛ نام
  حساب در Artifact ذخیره نشده است.
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/collections_payments_open_invoices_20260826.json`

این مرحله ۱۹ جدول پایه، ۱۶۴ ارتباط FK رسمی، ۱٬۶۴۳ مصرف‌کننده ماژولی و ۷۶
کاندید ارتباط ضمنی را بررسی کرده است. ۱۲ قرارداد SQL منتخب نیز برای بازسازی
معنا ذخیره شده‌اند. هیچ ردیف مشتری/پرداخت، نام پرداخت‌کننده، شماره چک یا حساب،
شناسه صیاد، سریال POS، Comment، نام کاربر/میزبان یا Credential در Artifact
وجود ندارد.

## نتیجه اصلی: چهار لایه مستقل

```text
Receipt                         سربرگ رویداد دریافت
  ├─ RCash                      وجه نقد
  ├─ Acc.TblCheque              چک دریافتی
  ├─ Acc.TblBankOrders          واریز/حواله بانکی
  └─ RBankDraft                 مسیر Legacy و فعلاً خالی

Acc.tblPayments                 تخصیص و تعدیل حساب مشتری/فاکتور
  └─ Acc.tblPayType             معنا، علامت و گروه هر تخصیص

SLE.tblOpenInvoice              Projection بازسازی‌شونده مانده فاکتور

NGT.CustomerCallPayments        ثبت وصول موبایل در بستر تماس مشتری
  └─ CustomerCallPaymentDetails تخصیص موبایل به سفارش/فاکتور
```

این چهار لایه جایگزین یکدیگر نیستند. «ثبت دریافت»، «ابزار دریافت»، «تخصیص به
فاکتور» و «مانده باز» باید در مدل وب Transaction و State جدا داشته باشند.

## سربرگ Receipt و ماشین حالت

`dbo.Receipt` تعداد ۶۸٬۶۲۶ ردیف از `۱۴۰۳/۰۱/۰۱` تا `۱۴۰۵/۰۵/۳۱` دارد؛ UUID
همه ردیف‌ها پر و یکتاست. Master چهار وضعیت تعریف می‌کند:

| کد | عنوان | مصرف فعلی |
|---:|---|---:|
| ۱ | رسید | ۱ |
| ۲ | تأیید شده | ۶۸٬۶۲۵ |
| ۳ | انتقال یافته | ۰ |
| ۴ | ابطال شده | ۰ |

تنها ۳۹٬۱۴۱ Receipt دارای `ConfirmDate` است؛ در نتیجه ۲۹٬۴۸۴ ردیف با Status
تأییدشده Timestamp تأیید ندارند. Status جاری شاهد Workflow است و
`ConfirmDate` باید Optional بماند؛ پرکردن مصنوعی تاریخ ممنوع است.

هر ۶۸٬۶۲۶ ردیف `IsManual=1` دارد، درحالی‌که ۲۷۴ Receipt Crosswalk معتبر NGT
دارند. پس `IsManual` منشأ UI/Integration را اثبات نمی‌کند و نباید برای تشخیص
کانال ایجاد استفاده شود. `TourId` نیز در همه ردیف‌ها خالی/صفر است.

از ۶۵ دلیل Receipt فقط ۱۰ دلیل مصرف فعلی دارد. دو دلیل غالب:

- «تسویه فاکتور مشتری»: ۴۳٬۰۸۱ Receipt؛
- «تسویه فاکتور تیم پخش»: ۲۴٬۳۵۶ Receipt.

در پنجره `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` تعداد ۷٬۰۷۳ Receipt ثبت شده که ۷٬۰۷۲
مورد Status تأییدشده دارند و هشت Reason متمایز را پوشش می‌دهند.

شماره مثبت Receipt با ترکیب زیر یکتا است:

```text
(AccYearId, DCId, SaleOfficeRef, ReceiptNo)
```

۲۶۴ Receipt دارای `ReceiptNo=0` هستند و تنها گروه تکراری همین Sentinel است.
UUID منبع برای هر ۲۶۴ ردیف یکتا مانده است؛ بنابراین کلید تجاری صفر نباید
Unique Constraint مقصد را بشکند و باید در Quarantine/Legacy Number Policy
مدیریت شود.

## ابزارهای واقعی دریافت و تطبیق مبلغ

جمع ابزارهای زیر برای تک‌تک Receiptها با `ReceiptAmount` دقیقاً برابر است:

| ترکیب ابزار | Receipt |
|---|---:|
| فقط نقد | ۲٬۷۸۲ |
| فقط چک | ۱۶٬۷۴۳ |
| فقط واریز/حواله بانکی | ۳۹٬۱۱۱ |
| ترکیبی | ۹٬۹۸۸ |
| بدون ابزار و با مبلغ صفر | ۲ |

تعداد ردیف ابزارها:

- `RCash`: ۱۱٬۰۹۶؛
- `Acc.TblCheque`: ۲۳٬۸۲۲؛
- `Acc.TblBankOrders`: ۱۴۶٬۵۷۶؛
- `RBankDraft`: صفر.

تطبیق مبلغ Receipt با مجموع ابزارها در ۶۸٬۶۲۶ از ۶۸٬۶۲۶ مورد دقیق و اختلاف
مطلق صفر است. هیچ ابزار یتیم یا ابزار بدون Receipt وجود ندارد. ۱۱٬۲۵۶
`RCashDetail` نیز برای تمام ۱۱٬۰۹۶ Cash Header از نظر مبلغ دقیق است؛ ۱۰۹
Cash Header بیش از یک Customer Split دارند.

این Invariant باید در مقصد Constraint سرویس دامنه باشد:

```text
Receipt.amount = Σ cash + Σ received_cheque + Σ bank_order + Σ bank_draft
```

## دفتر تخصیص `Acc.tblPayments`

این جدول ۴۹۳٬۴۹۴ ردیف با UUID یکتا دارد. همه Amountها مثبت‌اند، اما اثر مالی
از `tblPayType.PlusMinus` می‌آید. بنابراین علامت در Amount ذخیره نشده است.

| شاخص | مقدار |
|---|---:|
| متصل به Sale | ۴۳۰٬۴۸۴ |
| متصل به چک | ۶۰٬۲۴۲ |
| متصل به BankOrder | ۱۷۷٬۱۳۷ |
| متصل به Cash | ۱۸٬۹۵۰ |
| متصل به RBankDraft | ۰ |
| دارای دقیقاً یک ابزار Receipt | ۲۵۶٬۳۲۹ |
| بدون ابزار Receipt | ۲۳۷٬۱۶۵ |
| دارای چند ابزار هم‌زمان | ۰ |

۲۵۶٬۳۲۹ تخصیص ابزار به ۶۷٬۱۷۸ Receipt وصل می‌شوند و هیچ تضاد Parent Receipt
ندارند. ۲۳۷٬۱۶۵ ردیف بدون ابزار، الزاماً خطا نیستند؛ تخفیف، برگشت فروش،
اعلامیه بدهکار/بستانکار و انتقال حساب نیز در همین Ledger ثبت می‌شوند.

از ۵۱ `PayType`، تعداد ۳۵ نوع مصرف شده است. پرتکرارترین‌ها:

| نوع | علامت | ردیف |
|---|---:|---:|
| واریز | +۱ | ۱۶۸٬۶۰۲ |
| تخفیف نقدی توزیع | +۱ | ۹۴٬۰۵۸ |
| چک | +۱ | ۵۴٬۴۴۶ |
| سایر بدهکار | −۱ | ۲۶٬۴۴۵ |
| تخفیف نقدی وصول | +۱ | ۲۰٬۴۱۲ |
| تخفیف | +۱ | ۲۰٬۱۳۱ |
| نقد | +۱ | ۱۸٬۱۹۰ |
| تسویه از محل برگشت فاکتور | +۱ | ۱۴٬۵۸۶ |
| تسویه از محل بستانکاری | +۱ | ۱۱٬۸۵۳ |

در پنجره سه‌ماهه ۶۵٬۵۴۳ تخصیص برای ۹٬۹۲۸ مشتری، ۲۸٬۷۴۷ Sale و ۲۹ PayType
ثبت شده است. ۲۰۷٬۲۹۹ Sale حداقل یک تخصیص دارند؛ ۱۶۱٬۲۲۳ Sale چند تخصیص و
حداکثر یک Sale ۸۲ تخصیص دارد. هیچ Sale، Customer، PayType یا ابزار یتیمی در
Ledger پیدا نشد.

## مانده تخصیص‌نیافته ابزارها

Trigger رسمی `Acc.CheckReceiptRemainAmount` مانع تخصیص بیش از مبلغ ابزار و
Receipt می‌شود. داده فعلی این قرارداد را تأیید می‌کند:

| ابزار | بدون تخصیص | تخصیص دقیق | کمتر از مبلغ | بیشتر از مبلغ |
|---|---:|---:|---:|---:|
| Cash | ۹ | ۱۱٬۰۸۷ | ۰ | ۰ |
| Cheque | ۷۱۴ | ۲۳٬۱۰۴ | ۴ | ۰ |
| BankOrder | ۱٬۲۹۳ | ۱۴۵٬۲۸۲ | ۱ | ۰ |

در سطح Receipt، تعداد ۶۷٬۱۷۱ Receipt تخصیص کامل، ۷ Receipt تخصیص ناقص و
۱٬۴۴۸ Receipt بدون تخصیص دارند؛ هیچ Over-allocation وجود ندارد. «ثبت Receipt»
و «تسویه کامل آن» دو State جدا هستند.

## Projection مانده باز

`SLE.tblOpenInvoice` تعداد ۲۱۴٬۹۷۱ ردیف یکتا دارد:

- ۸٬۷۸۷ مانده مثبت؛
- ۲۰۶٬۱۶۷ مانده صفر؛
- ۱۷ مانده منفی؛
- ۱۱٬۶۸۳ ردیف با مؤلفه برگشت فروش؛
- ۲٬۰۰۸ ردیف با مانده چک برگشتی؛
- ۱۱۸٬۵۹۴ ردیف با `LastPayDate`.

برای همه ردیف‌ها رابطه زیر دقیق است:

```text
OpenAmount = TotalAmount - ISNULL(PayAmount, 0)
```

اما `PayAmount` جمع خام Ledger نیست. Procedure رسمی
`Acc.usp_GetSalePayAmount` این موارد را لحاظ می‌کند:

- `PayType.PlusMinus`؛
- وضعیت جاری چک و حذف اثر چک برگشتی/ابطالی؛
- انتقال و چک جایگزین؛
- `PaymentRef` و `AdvancedReceiptRef`؛
- برگشت فروش نوع ۱۰۰۶ و برگشت Legacy؛
- تسویه تأمین‌کننده؛
- آخرین تاریخ مؤثر پرداخت.

در مقایسه با Projection رسمی، جمع خام `tblPayments.Amount` برای ۴٬۷۴۴ فاکتور
و حتی جمع ساده `Amount × PlusMinus` برای ۴٬۶۷۷ فاکتور اختلاف دارد. پس این
منطق نباید به یک Formula ساده در UI یا Report تبدیل شود.

`RetSaleAmount` و `RetChequeRemainAmount` مؤلفه‌های توضیحی/کنترلی‌اند و نباید
دوباره از `OpenAmount` کسر شوند. اثر معتبر آن‌ها قبلاً در PayAmount رسمی لحاظ
شده است.

Projection به ۲۱۴٬۹۷۱ از ۲۱۴٬۹۷۳ Sale فعال وصل است؛ دو Sale فعال در Snapshot
نیستند. هیچ Projection یتیم یا متعلق به Sale ابطال‌شده وجود ندارد. آخرین Full
Refresh ثبت‌شده `2026-08-22 18:00:03.820` و مدت آن ۱۹۴ میلی‌ثانیه است.
`tblOpenInvoicePrepareHistory` نیز ۷۷۰٬۰۷۷ اجرای Customer-specific برای
۳۵٬۴۷۸ مشتری ثبت کرده است. این جدول Event مالی نیست؛ Log بازسازی Cache است.

`PassDate` Contract قابل اتکای وضعیت جاری نیست: ۸۳٬۸۵۷ مانده صفر/منفی بدون
PassDate و ۱۷ مانده مثبت با PassDate وجود دارد. وضعیت پرداخت باید از Amount و
قواعد دامنه محاسبه شود و PassDate فقط شاهد تاریخی بماند. ۱۷ مانده منفی نیز
نباید در UI به صفر Clamp شوند.

## پل وصول NGT

`NGT.CustomerCallPayments` تعداد ۳٬۵۲۳ Header و
`CustomerCallPaymentDetails` تعداد ۳٬۹۱۷ Detail دارد. همه فعال و Amountها
مثبت‌اند. نوع تسویه Headerها:

| نوع | Header |
|---|---:|
| کارت‌خوان | ۳٬۱۷۹ |
| نقد | ۱۸۰ |
| چک | ۱۵۹ |
| رسید | ۵ |

همه Headerها به CustomerCall معتبر وصل‌اند. ۲۷۴ Header هم ReceiptRef عددی و
هم ReceiptUUID دارند؛ هر دو برای تمام ۲۷۴ مورد به یک Receipt واحد اشاره
می‌کنند، شماره Receipt نیز منطبق و Status همه تأییدشده است. همه این Receiptها
Reason «تسویه فاکتور تیم پخش» دارند.

بااین‌حال مبلغ NGT فقط در ۴ مورد با مبلغ Receipt برابر و در ۲۷۰ مورد متفاوت
است. بنابراین Crosswalk، همانندی Record را ثابت می‌کند ولی Receipt تیم پخش
می‌تواند Scope تجمیعی متفاوتی از یک CustomerCallPayment داشته باشد. تبدیل
مبلغ یا نسبت ثابت نیز در داده تأیید نشد.

در Detailها فقط ۱۷۲ ردیف `IsOldInvoice=1` دارای BackOffice Sale ID/UUID هستند؛
شناسه عددی و UUID در هر ۱۷۲ مورد منطبق‌اند. باقی Detailها بیشتر به
`CustomerCallOrderUniqueId` متکی‌اند و هنوز Crosswalk فاکتور BackOffice ندارند.

۱۴ Header هیچ Detail فعالی ندارند. مجموع Detail در ۳٬۴۶۶ Header تا دقت یک
صدم با Header برابر است؛ ۵۷ Header اختلاف دارند که ۱۴ مورد بدون Detail و ۴۳
مورد Under-allocation هستند. Over-allocation صفر است. این اختلاف‌ها باید State
تخصیص‌نیافته/درانتظار باشد، نه حذف خودکار.

## تنظیمات روش پرداخت و POS

View `NGT.PaymentTypeOrders` از دو Master واقعی `GNR.tblPaymentType` و
`GNR.tblPaymentUsance` ساخته می‌شود. ۴۰۴ Term قابل مشاهده است اما فقط ۱۵ Term
فعال و ۱۲ Term فعال مجاز به Receipt هستند. بنابراین کپی‌کردن همه ۴۰۴ مقدار به
SelectBox فعال اشتباه است؛ تاریخچه Removed باید جدا حفظ شود.

`NGT.DealerPaymentTypes` تعداد ۲٬۵۲۱ اتصال فعال برای ۴۵۰ فروشنده و ۳۸ Term
دارد. ۴۸۲ اتصال فعال به Termهایی اشاره می‌کنند که View آن‌ها را Removed نشان
می‌دهد. این رابطه باید Effective Status مستقل داشته و در Migration گزارش
Reconciliation بگیرد.

`NGT.Pos` تعداد ۴۷ دستگاه برای چهار حساب بانکی دارد و یک دستگاه Removed است.
سریال هیچ دستگاهی در Artifact ذخیره نشده است. تخصیص POS، حساب بانکی و مجوز
عامل باید یک دامنه امنیتی جدا از ثبت Payment باشد.

## قرارداد اولیه مدل مقصد

حداقل موجودیت‌ها و Projectionها:

- `Receipt` با Status Event، Reason، Business Number و Source Provenance؛
- `ReceiptInstrument` به‌صورت Union نوع‌دار برای Cash/Cheque/BankOrder/Draft؛
- `ReceiptInstrumentAllocation` با Amount و مانده تخصیص‌نیافته؛
- `CustomerAccountEntry` برای اثر علامت‌دار PayType؛
- `InvoiceSettlementAllocation` برای اتصال Ledger به Sale؛
- `PaymentType` و `ReceiptReason` به‌صورت Master نسخه‌دار؛
- `ChequeStateEvent` مستقل از Payment Allocation؛
- `OpenInvoiceProjection` بازسازی‌شونده، نه Source of Truth؛
- `MobileCollection` و `MobileCollectionAllocation`؛
- Crosswalkهای مستقل Receipt ID/UUID و Sale ID/UUID؛
- `PaymentTerm` و `DealerPaymentTermEligibility` با وضعیت مؤثر؛
- `PosDeviceAssignment` بدون افشای Serial در Log/Audit عمومی.

فرمان ثبت Receipt، تخصیص ابزار، تخصیص فاکتور و Refresh Projection باید
Idempotency Key و Audit جدا داشته باشند. API رسمی نباید به `tblOpenInvoice`
به‌عنوان Ledger بنویسد.

## Golden Caseهای لازم

1. Receipt ترکیبی نقد + چک + واریز با مجموع دقیق.
2. Receipt تأییدشده Legacy بدون ConfirmDate.
3. Receipt با ابزار کامل ولی Allocation ناقص.
4. چک برگشتی که اثر آن از PayAmount رسمی حذف و مانده باز بازگردانده می‌شود.
5. برگشت فروش که در PayAmount لحاظ می‌شود ولی دوباره از OpenAmount کسر نمی‌شود.
6. Sale با چند PayType مثبت/منفی و انتقال حساب.
7. NGT Payment دارای Receipt Crosswalk ولی مبلغ Scope متفاوت.
8. NGT Header بدون Detail و Detail در انتظار BackOffice Sale.
9. Dealer PaymentTerm فعال که Master Term آن Removed است.
10. OpenInvoice منفی و PassDate ناسازگار، بدون Clamp یا اصلاح خودکار.

## ابهام‌های باز

1. Scope دقیق Receipt تیم پخش در برابر یک CustomerCallPayment و علت اختلاف
   مبلغ ۲۷۰ Crosswalk.
2. دلیل ۲ Sale فعال خارج از Projection در Snapshot Clone.
3. علت ۷ Receipt با تخصیص ناقص و اینکه مانده آن‌ها عمداً باز است یا Legacy.
4. معنای عملیاتی ۱۷ `OpenAmount` منفی و ۱۷ مانده مثبت دارای PassDate.
5. چرخه کامل وضعیت چک و تسویه مجدد چک برگشتی؛ مرحله بعدی باید History چک را
   به‌صورت دامنه مستقل ببندد.
6. سیاست صحیح ۴۸۲ DealerPaymentType متصل به Term حذف‌شده.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_collection_payment_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\collections_payments_open_invoices_20260826.json
```
