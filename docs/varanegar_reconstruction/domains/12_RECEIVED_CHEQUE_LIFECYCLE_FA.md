# دامنه ۱۲: چرخه چک دریافتی و تسویه چک برگشتی

تاریخ استخراج: ۲۰۲۶-۰۸-۲۶  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی**

## مرز و منبع شاهد

- منبع: `127.0.0.1 / NeginPakhsh_WebDev`
- وضعیت دیتابیس: `READ_ONLY`
- حساب تحلیل با `UPDATE=0` و عضویت در `db_denydatawriter` کنترل شد.
- Extractor قابل تکرار:
  `scripts/sql/extract_varanegar_received_cheque_domain.py`
- Artifact کامل:
  `artifacts/varanegar_analysis/domains/received_cheque_lifecycle_20260826.json`

این مرحله ۱۸ جدول پایه، ۱۲۴ FK رسمی، ۱٬۰۵۸ مصرف‌کننده ماژولی، ۱۶ ارتباط ضمنی
و ۱۶ قرارداد SQL منتخب را بررسی کرده است. شماره چک/حساب/صیاد، کد ملی، نام
پرداخت‌کننده یا مشتری، Comment، نام کاربر/میزبان، Credential و ردیف خام Payment
در Artifact ذخیره نشده است.

## نتیجه اصلی: وضعیت چک Event-sourced است

```text
Receipt(status=confirmed)
  └─ Acc.TblCheque                 هویت و مبلغ چک
       └─ Acc.tblChqHist [1..10]   رخدادهای وضعیت و محل نگهداری
             ├─ PreviousHistRef    زنجیره رخداد
             ├─ PreviousStatRef    وضعیت قبلی
             ├─ TransitionId       قرارداد Workflow
             └─ IsLast=1           دقیقاً یک وضعیت جاری

Acc.tblPayments.ChqRef             اثر چک روی فاکتور
Acc.tblPayments.RetChequeRef       تسویه بدهی چک برگشتی
SLE.tblOpenInvoice                 Projection مانده فاکتور/چک برگشتی
```

`TblCheque` هیچ ستون وضعیت جاری ندارد. هر Query که بدون `tblChqHist.IsLast=1`
وضعیت را حدس بزند، از نظر دامنه نادرست است.

## Master وضعیت و تفاوت دو Workflow

Master فعال `Acc.tblChqStatus` هشت وضعیت دارد:

| کد | عنوان | مصرف تاریخچه | وضعیت جاری |
|---:|---|---:|---:|
| ۱ | نزد صندوق | ۴۷٬۱۱۶ | ۷۰۳ |
| ۲ | نزد بانک | ۹٬۴۸۱ | ۵۳ |
| ۳ | وصولی | ۸٬۲۸۴ | ۸٬۲۸۴ |
| ۴ | برگشتی | ۲٬۲۱۶ | ۱۳۸ |
| ۵ | استرداد | ۱٬۹۵۶ | ۱٬۹۵۶ |
| ۷ | واگذار به غیر | ۱۳٬۷۴۴ | ۱۲٬۶۳۵ |
| ۸ | انتقال بین صندوق | ۲۳٬۲۵۷ | ۰ |
| ۹ | حقوقی | ۷۷ | ۵۳ |

`dbo.RchequeStatus` یک کد ۶ با عنوان «پیگیری وصول» نیز دارد، اما این کد در
Master فعال Acc و تاریخچه فعلی وجود ندارد. نباید آن را بدون State Contract به
Workflow مقصد وارد کرد؛ فقط به‌عنوان Legacy Capability نگه داشته می‌شود.

`Acc.tblChqStatFlow` فقط پنج انتقال اصلی بانکی را تعریف می‌کند:

```text
1 صندوق → 2 بانک → 3 وصولی
                 └→ 4 برگشتی → 2 بانک
                              └→ 5 استرداد
```

اما Workflow کامل UI در `dbo.RChequeWorkflow` و
`dbo.RChequeAllWorkflow` هجده انتقال فعال دارد و واگذاری، بازگشت از واگذاری،
انتقال صندوق و حقوقی را نیز پوشش می‌دهد. پس جدول پنج‌ردیفی به‌تنهایی Master
کامل مجوز Transition نیست.

## جمعیت و کیفیت هویت چک

`Acc.TblCheque` تعداد ۲۳٬۸۲۲ چک دارد:

- UUID همه پر و یکتا؛
- مبلغ همه مثبت؛
- همه به Receipt معتبر و Status=2 «تأییدشده» وصل‌اند؛
- بانک و ChequeType یتیم صفر؛
- همه نوع ۱ «عادی» و نوع ۲ «دیجیتال» بدون مصرف؛
- `MainChqRef` در داده فعلی صفر؛
- `IsReconciled=1` در داده فعلی صفر؛
- ۲۳۹ ردیف Converted؛
- سررسیدها از `۱۴۰۱/۰۲/۲۷` تا `۱۴۰۵/۱۲/۲۳` و ثبت از `۱۴۰۳/۰۱/۱۱` تا
  `۱۴۰۵/۰۵/۳۱`.

کلید‌های زیر هیچ Duplicate ندارند:

```text
UniqueId
(BankRef, ChqNo, ChqDate, AccNo)
```

مقادیر چهار جزء کلید دوم عمداً ذخیره نشده‌اند؛ فقط تعداد گروه تکراری صفر ثبت
شده است.

پوشش صیاد بدون ذخیره مقدار:

| سال ثبت | چک | دارای صیاد | Converted |
|---:|---:|---:|---:|
| ۱۴۰۳ | ۸٬۵۷۰ | ۸٬۲۹۷ | ۲۳۹ |
| ۱۴۰۴ | ۱۱٬۰۹۸ | ۱۱٬۰۹۸ | ۰ |
| ۱۴۰۵ | ۴٬۱۵۴ | ۴٬۱۵۳ | ۰ |

در مجموع ۲۳٬۵۴۸ چک صیاد و ۱۰٬۵۳۲ چک NationalCode پر دارند. این اعداد فقط
Coverage هستند و مجوز نمایش یا Logکردن مقادیر حساس نیستند.

## تمامیت زنجیره ۱۰۶٬۱۳۱ رخداد

هر ۲۳٬۸۲۲ چک حداقل یک و حداکثر ده History دارد؛ میانگین ۴٫۴۵۵ رخداد است.
برای همه چک‌ها دقیقاً یک `IsLast=1` وجود دارد و همان ردیف، بزرگ‌ترین ID تاریخچه
آن چک است.

از ۱۰۶٬۱۳۱ رخداد:

- ۲۳٬۸۲۲ رخداد اولیه‌اند؛
- ۸۲٬۳۰۹ رخداد `PreviousHistRef` و `TransitionId` دارند؛
- Previous History یتیم: صفر؛
- Previous History متعلق به چک دیگر: صفر؛
- اختلاف `PreviousStatRef` با Status رخداد قبلی: صفر؛
- Transition یتیم یا ناسازگار با Old/New Status: صفر.

۲۳٬۷۷۱ چک با وضعیت ۱ شروع شده‌اند. ۵۱ چک Legacy مستقیماً با وضعیت ۴ شروع
شده‌اند؛ این‌ها نباید با ساخت یک رخداد مصنوعی «نزد صندوق» بازنویسی شوند.

پرتکرارترین انتقال‌های واقعی:

| انتقال | رخداد |
|---|---:|
| ۱ → ۸ انتقال بین صندوق | ۲۳٬۲۵۷ |
| ۸ → ۱ پایان انتقال صندوق | ۲۳٬۲۵۷ |
| ۱ → ۷ واگذاری به غیر | ۱۳٬۷۳۶ |
| ۱ → ۲ واگذاری به بانک | ۹٬۳۶۲ |
| ۲ → ۳ وصول | ۸٬۲۸۴ |
| ۴ → ۵ استرداد | ۱٬۸۷۴ |
| ۲ → ۴ برگشت | ۱٬۰۹۰ |
| ۷ → ۴ برگشت از واگذاری به غیر | ۱٬۰۷۵ |
| ۴ → ۲ واگذاری مجدد به بانک | ۱۱۹ |
| ۴ → ۹ ارجاع حقوقی | ۷۷ |

Status=8 هیچ Current Row ندارد و یک Event میانی انتقال صندوق است؛ در مقصد
بهتر است `SafeTransferStarted/Completed` باشد، نه وضعیت قابل توقف دائمی.

در پنجره `۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱` تعداد ۱۲٬۰۸۸ رخداد برای ۳٬۶۸۹ چک و هر
هشت Status ثبت شده است. این شاهد فعالیت واقعی سه‌ماهه همان Clone است.

## Context لازم برای هر Status

داده جاری Contractهای عملی زیر را تأیید می‌کند:

- همه ۷۰۳ چک «نزد صندوق» Safe دارند؛
- همه ۵۳ چک «نزد بانک» DepBranch دارند؛
- همه ۸٬۲۸۴ چک «وصولی» سابقه/Context واگذاری بانک دارند؛
- هر ۱۳۸ چک «برگشتی» هم UnpaidReason و هم UnpaidPlace دارد؛
- هر ۱۲٬۶۳۵ چک «واگذار به غیر» Safe و `History.PayId2` معتبر دارد؛ ۱۲٬۶۲۷
  مورد Master `PayId` نیز دارند و هشت مورد فقط Master projection خالی دارند؛
- از ۵۳ چک حقوقی، ۱۸ مورد LegalType=2 و ۳۵ مورد LegalType نامشخص دارند؛ هر
  ۵۳ مورد PersonnelId دارند و Personnel نوع Legal را تعیین نمی‌کند.

تحلیل تکمیلی ثابت کرد هشت مورد بدون Master `PayId` لینک مفقود نیستند: هر هشت
Pay تأییدشده و `History.PayId2` معتبر دارند. ۳۵ LegalType تهی نیز باید
`UNKNOWN_SOURCE` بمانند و از Personnel حدس زده نشوند. در عین حال مسیر Confirm
گروهی Deploy‌شده LegalType را به History پاس نمی‌دهد؛ قرارداد و Runbook کامل در
`RECEIVED_CHEQUE_PAY_PROJECTION_AND_LEGAL_TYPE_DIAGNOSTIC_20260827_FA.md` است.

## اثر وضعیت چک روی مانده فاکتور

Procedure رسمی `Acc.usp_GetSalePayAmount` فقط Paymentهای چکی نوع ۲ و ۱۰۰۸ را
در PayAmount لحاظ می‌کند که چک مؤثر آن‌ها وضعیت جاری ۴، ۵ یا ۹ نداشته باشد.

```text
وضعیت‌های مؤثر در پرداخت: 1, 2, 3, 7, 8
وضعیت‌های حذف‌کننده اثر: 4 برگشتی، 5 استرداد، 9 حقوقی
```

واگذاری به غیر (۷) همچنان پرداخت معتبر مشتری است؛ از دست‌رفتن مالکیت فیزیکی
چک اثر وصول مشتری را حذف نمی‌کند. در مقابل، انتقال به حقوقی (۹) مانند برگشتی
از PayAmount حذف می‌شود.

در Snapshot فعلی ۴٬۶۹۲ Allocation چکی نوع ۲/۱۰۰۸ برای ۲٬۰۱۸ چک و ۴٬۳۴۷ Sale
به‌علت Status ۴/۵/۹ از PayAmount رسمی حذف می‌شوند. این اثر ۱٬۱۸۲٬۰۹۴٬۲۶۵٬۴۵۷
واحد پولی دارد. UI نباید مبلغ Payment خام را به‌عنوان پرداخت مؤثر نشان دهد.

منطق رسمی همچنین `MainChqRef` را برای چک جایگزین و `PaymentRef` را برای مسیر
تسویه پیشرفته پشتیبانی می‌کند، هرچند MainChqRef در Snapshot فعلی مصرف نشده
است. قابلیت نباید به‌علت صفر بودن داده حذف شود و برای آن Golden Case لازم است.

## تسویه بدهی چک برگشتی

`Acc.tblPayments.RetChequeRef` مسیر جداگانه تسویه چک برگشتی است:

- ۵٬۶۵۰ Payment؛
- ۱٬۳۲۰ چک؛
- ۹۴۱ Customer؛
- مرجع چک/History یتیم: صفر؛
- همه Amountها مثبت.

از ۲٬۱۴۷ چک جاری در وضعیت‌های ۴/۵/۹:

| وضعیت تسویه در سطح چک | چک |
|---|---:|
| بدون هیچ تسویه | ۸۲۷ |
| تسویه جزئی | ۴۶۳ |
| تسویه کامل | ۸۵۷ |
| بیش‌تسویه | ۰ |

`Acc.GetRetChequeRemAmount` مانده هر چک را چنین می‌سازد:

```text
ChequeRemaining = ChqAmount - Σ Payments.Amount WHERE RetChequeRef = ChequeId
```

اما `SLE.tblOpenInvoice.RetChequeRemainAmount` **در سطح Sale** محاسبه می‌شود،
نه برای یک چک مشخص:

```text
InvalidChequeAmount(sale)
  = Σ allocation where current cheque status in (4,5,9)

ReturnedChequeSettlement(sale)
  = Σ payment where RetChequeRef is not null

RetChequeRemainAmount(sale)
  = max(InvalidChequeAmount - ReturnedChequeSettlement, 0)
```

این فرمول برای هر ۲۱۴٬۹۷۱ ردیف OpenInvoice بازسازی شد: ۲۱۴٬۹۷۱ تطبیق دقیق،
اختلاف صفر، و ۲٬۰۰۸ Sale با مانده مثبت. در نتیجه Paymentهای RetChequeRef برای
Projection فاکتور در سطح Sale Pool می‌شوند؛ تطبیق یک‌به‌یک چک و Payment برای
این ستون اشتباه است.

۴۹ Payment مربوط به ۱۷ چک، Customer متفاوتی از `TblCheque.CustRef` دارند. تحلیل
تکمیلی ثابت کرد هر ۴۹ ردیف دقیقاً به Allocation اولیه‌ی همان
`Cheque + Sale + Payment Customer` وصل‌اند؛ ردیف بی‌توضیح و Pair بیش‌تسویه صفر
است. ۴۸ ردیف Saleدار همگی با Customer فاکتور برابرند و هیچ‌کدام با مالک چک
برابر نیستند. پس این‌ها خرابی نیستند، بلکه Cross-party allocation رسمی‌اند.
`ManualCustRef` فقط در دو مورد برابر است و مرجع تخصیص نیست. قرارداد کامل در
`RETURNED_CHEQUE_CROSS_CUSTOMER_DIAGNOSTIC_20260827_FA.md` ثبت شده است.

## مسیرهای فعال، Legacy و خالی

`tblRChequeLog` تعداد ۲٬۵۴۵ رخداد ویرایش برای ۲٬۱۶۷ چک معتبر از ۲۰۲۴-۰۴-۲۹
تا ۲۰۲۶-۰۸-۲۲ دارد. مقادیر خام قبل/بعد در Artifact ذخیره نشده‌اند. این Log
ویرایش هویت چک است و جایگزین State History نیست.

جدول‌های زیر در Snapshot خالی‌اند:

- `Acc.tblChqChangeStatus` و Item آن؛
- `dbo.RChequeRefund`؛
- `dbo.CessionToOther` و Refund آن.

بااین‌حال ۱۲٬۶۳۵ چک جاری وضعیت واگذاری به غیر و ۱۲٬۶۳۵ History PayId2 معتبر
دارند؛ Master PayId برای ۱۲٬۶۲۷ مورد پر است. مسیر رسمی Approved Pay به History
متکی است؛ خالی بودن جدول جدید یا Master projection مجوز حذف قابلیت نیست.

## قرارداد اولیه مدل مقصد

حداقل موجودیت‌ها و قواعد:

- `ReceivedCheque` برای هویت، مبلغ، سررسید و Referenceهای حساس رمزگذاری‌شده؛
- `ChequeStateEvent` Append-only با PreviousEvent و Transition؛
- `ChequeStateProjection` با دقیقاً یک وضعیت جاری؛
- `ChequeCustodyTransfer` برای انتقال صندوق با From/To Safe؛
- `ChequeBankDeposit` برای وضعیت نزد بانک؛
- `ChequeCession` برای واگذاری به غیر و Pay linkage؛
- `ChequeReturnDetail` برای علت و محل برگشت؛
- `ChequeLegalCase` برای مسیر حقوقی؛
- `InvoiceChequeAllocation` برای اثر اولیه روی Sale؛
- `ReturnedChequeSettlement` با `RetChequeRef`؛
- `ReturnedChequeSaleProjection` برای Pool سطح Sale؛
- `ChequeReplacementLink` برای Main/Replacement با Effective Cheque resolution؛
- `ChequeSensitiveIdentity` جدا، رمزگذاری‌شده و خارج از Log عمومی؛
- `SourceCrosswalk` برای ID و UUID قدیمی.

Command تغییر وضعیت باید Transition مجاز، Context لازم، Concurrency Version،
Idempotency Key و Audit داشته باشد. Update مستقیم `IsLast` یا حذف History از UI
ممنوع است.

## Golden Caseهای لازم

1. دریافت چک و ایجاد رخداد اولیه نزد صندوق.
2. انتقال صندوق به صندوق با Eventهای ۱→۸→۱ و تغییر Custody.
3. واگذاری بانک، وصول و حفظ اثر Payment.
4. برگشت از بانک با علت/محل و حذف اثر از OpenInvoice.
5. واگذاری مجدد چک برگشتی به بانک.
6. واگذاری به غیر و بازگشت از واگذاری؛ Status 7 همچنان پرداخت مؤثر.
7. مسیر حقوقی و سپس استرداد.
8. تسویه جزئی و کامل چک برگشتی بدون Over-settlement.
9. دو چک برگشتی روی یک Sale و Poolکردن تسویه در سطح Sale.
10. چک جایگزین با MainChqRef و Receipt فعال/ابطال‌شده.
11. Retry فرمان تغییر وضعیت بدون History تکراری.
12. Import چک Legacy که اولین رخداد آن Status=4 است.
13. Status 7 با Master PayId تهی ولی History PayId2 معتبر؛ بدون Quarantine.
14. LegalType نوع ۱، نوع ۲ و `UNKNOWN_SOURCE` با حفظ Personnel مستقل.
15. Confirm تغییر وضعیت که LegalType را اتمیک به History می‌برد و Fault بین
    Parent/Event را Rollback می‌کند.
16. Cross-customer returned-cheque settlement با Allocation provenance دقیق.

## ابهام‌های باز

1. دلیل دقیق باقی‌ماندن Master PayId برای ۱۲٬۶۲۷ Approved Pay و خالی‌شدن آن در
   هشت مورد؛ این تفاوت Authority عملیاتی را عوض نمی‌کند.
2. منشأ دقیق ۳۵ LegalType نامشخص؛ مقدار از شواهد فعلی قابل بازیابی نیست.
3. نرخ Runtime مسیر Confirm گروهی که LegalType را به History پاس نمی‌دهد.
4. کاربرد واقعی `IsReconciled` که در همه ردیف‌های فعلی صفر است.
5. مسیر و داده کنترل‌شده برای MainChqRef/چک جایگزین که Procedure پشتیبانی
   می‌کند ولی نمونه جاری ندارد.
6. تفاوت کاربردی جدول‌های ChangeStatus/Cession جدید با مسیر Legacy PayId.

## دستور بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_received_cheque_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\received_cheque_lifecycle_20260826.json
```
