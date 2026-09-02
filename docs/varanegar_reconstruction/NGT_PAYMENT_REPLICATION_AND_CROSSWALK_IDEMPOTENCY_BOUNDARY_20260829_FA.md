# مرز Replication پرداخت NGT، رسید BackOffice و Idempotency Crosswalk

تاریخ استخراج: ۲۰۲۶-۰۸-۲۹  
وضعیت: **تأییدشده روی Clone فقط‌خواندنی و IL ایستای Assembly مستقر**

این مرحله ادامه‌ی مستقیم مرز پرداخت NGT است و پاسخ می‌دهد که پرداخت موبایل چگونه
به `Receipt`، ابزار خزانه‌داری و `Settlement` پشت‌دفتر تبدیل می‌شود، نتیجه کجا
ذخیره می‌شود و Retry در چه نقطه‌ای می‌تواند نتیجه‌ی تکراری یا Crosswalk ناقص
باقی بگذارد.

هیچ Procedure، endpoint یا Command اجرا نشد. چهار متن SQL فقط در حافظه خوانده
شدند و فقط hash، طول، نام امن Object، شمارش Token و Aggregate ناشناس ذخیره شد.
Assemblyها نیز فقط به‌صورت فایل PE/IL خوانده شدند و Load یا Execute نشدند.
هیچ متن SQL، GUID، ردیف پرداخت/مشتری، شماره چک/حساب، Credential یا مقدار تنظیمی
در Artifact جدید وجود ندارد.

## زنجیره‌ی واقعی صدور اثر مالی

زنجیره‌ی مستقر چهار Procedure اصلی دارد:

```text
TourDomain.ReplicateTour
  └─ TourDomain.NewReplicateTour
       └─ dbo.NGT_DoReplicateTour
            └─ dbo.NGT_ReplicateTour
                 ├─ dbo.NGT_CreateReceipt_ForDistInfo
                 │    ├─ dbo.Receipt
                 │    ├─ dbo.RCash + dbo.RCashDetail
                 │    ├─ Acc.TblCheque + Acc.tblChqHist
                 │    ├─ Acc.tblBankOrders
                 │    └─ #FinalResult(Type=10)
                 └─ dbo.NGT_CreateSettlement_Merge
                      └─ Settlement / تخصیص به فروش و برگشت
```

`NGT_CreateReceipt_ForDistInfo` و `NGT_CreateSettlement_Merge` Transaction محلی
ندارند. آن‌ها در Transaction صریح `NGT_ReplicateTour/NGT_DoReplicateTour`
اجرا می‌شوند؛ بنابراین Receipt، ابزارها، Settlement و `TourHistory(Type=10)` در
مسیر موفق SQL یک مرز تراکنشی مشترک دارند. تحلیل ایستا جای اجرای Fault injection
را نمی‌گیرد، اما شکل مالکیت Transaction را با اطمینان بالا ثابت می‌کند.

هفت نوع تسویه در Literalهای SQL به Master معتبر `SettlementType` نگاشت شدند:
نقد، چک، کارت‌خوان، رسید، تخفیف، پرداخت از مانده بستانکاری و پرداخت با واسطه.
چهار نوع اول در جمعیت فعلی `CustomerCallPayments` دیده شده‌اند؛ سه نوع دیگر
قابلیت Procedure هستند و صفر/کم‌بودن جمعیت فعلی مجوز حذف آن‌ها نیست.

## `TourHistory(Type=10)` دفتر نتیجه‌ی پرداخت است

Schema جدول `dbo.TourHistory` برای Type=10 این معنا را نشان می‌دهد:

- `EntityUniqueId`: شناسه‌ی `NGT.CustomerCallPayments.Id`؛
- `BackOfficeUniqueId`: UUID رسید؛
- `BackOfficeRef`: شناسه‌ی عددی رسید؛
- `BackOfficeNo`: شماره‌ی رسید؛
- `CreatedDate`: زمان ثبت نتیجه‌ی Replication.

هر ۴۴۷ History نوع ۱۰ به یک Payment موجود و فعال وصل است؛ Entity یتیم صفر است.
از این ۴۴۷ ردیف، ۴۳۸ مورد از طریق UUID و Ref به یک Receipt یکسان می‌رسند و شماره
نیز برابر است. ۹ History متعلق به چهار Payment دیگر در Snapshot فعلی Receipt
قابل حل ندارند. تمام ۴۳۸ هدف موجود `ReceiptStatusId=2` دارند.

## دو شکل کاملاً متفاوت Crosswalk جاری

۳۴۴ Payment حداقل یک History نوع ۱۰ دارند:

| شکل جاری | Payment | History | نتیجه |
|---|---:|---:|---|
| یک History | ۲۷۴ | ۲۷۴ | UUID + Ref + No جاری و دقیقاً برابر History |
| چند History | ۷۰ | ۱۷۳ | فقط No جاری؛ UUID و Ref هر دو خالی |

این تفکیک در داده کامل است: هیچ Payment تک-History با Crosswalk ناقص و هیچ
Payment چند-History با Crosswalk کامل وجود ندارد.

در گروه دوم:

- ۷۰ Payment دارای History تکراری‌اند؛
- ۷۲ گروه تکرار دقیق `Entity + UUID + Ref + No` و در مجموع ۱۷۳ History وجود دارد؛
- بیشینه‌ی History برای یک Payment شش است؛
- ۶۸ Payment حداقل یک Receipt موجود دارند؛
- دو Payment هیچ هدف موجود ندارند؛
- دو Payment بیش از یک UUID هدف تاریخی دارند؛
- ۹ History در چهار Payment هدف مفقود دارند؛ دو مورد از آن چهار Payment هم‌زمان
  یک هدف موجود دیگر نیز دارند.

این اعداد وجود History تکراری و Crosswalk جاری ناقص را ثابت می‌کنند، اما ثابت
نمی‌کنند که هر History تکراری الزاماً یک اثر مالی تکراری ساخته است. ۶۸ Payment
بیشتر، Historyهای تکراری یک هدف یکسان دارند. فقط دو Payment چند هدف متمایز دارند
و همان‌ها باید با شاهد عملیاتی Quarantine و تعیین تکلیف شوند.

## چرا Type=10 یکتا نیست

`TourHistory` هیچ FK و Trigger ندارد. تنها Index یکتای `EntityUniqueId` فیلترش
برای `Type=1` است؛ Type=10 را پوشش نمی‌دهد. بنابراین پایگاه داده مانع چند History
پرداخت برای یک Entity نمی‌شود.

در متن SQL نیز Guard یکسان نیست: یکی از Branchهای Receipt قبل از Insert نوع ۱۰
`NOT EXISTS(EntityUniqueId, Type=10)` دارد، ولی Branchهای دیگر Type=10 را بدون
Guard عمومی درج می‌کنند. وجود ۷۲ گروه تکرار دقیق با این تفاوت کد سازگار است.

## شکاف Commit و Write-back برنامه

`dbo.NGT_DoReplicateTour` پس از اجرای Procedure داخلی، Transaction SQL را Commit
می‌کند. سپس در بخش NGT فقط `CustomerCallPayments.BackOfficeReceiptNo` را از
`TourHistory(Type=10)` به‌روزرسانی می‌کند؛ در همان Update، UUID و Ref نوشته
نمی‌شوند.

IL مستقر `TourDomain.ReplicateTour` یک call به `NewReplicateTour` و سپس سه setter
مجزای زیر را روی Payment نشان می‌دهد:

- `BackOfficeReceiptUniqueId`؛
- `BackOfficeReceiptRef`؛
- `BackOfficeReceiptNo`.

در ترتیب خطی IL، Commit هم پیش و هم پس از این setterها وجود دارد. این شاهد قوی
یک مرحله‌ی جداگانه‌ی Write-back است، ولی به‌تنهایی ثابت نمی‌کند هر سه Commit در
یک Branch runtime واحد طی می‌شوند. برای اثبات کامل مسیر باید Fault injection
کنترل‌شده انجام شود. داده‌ی جاری ۷۰ حالت «History چندگانه + فقط No» شاهد واقعی
است که Crosswalk جزئی در سیستم پذیرفته و نگهداری شده است.

## نتیجه‌ی معماری برای ERP شخصی نگین

پورت مستقیم `TourHistory` کافی نیست. مقصد باید دو مفهوم جدا داشته باشد:

1. `PaymentReplicationAttempt`: تاریخچه‌ی append-only هر تلاش، Payload hash،
   نتیجه، خطا و زمان؛
2. `PaymentReceiptCrosswalkCurrent`: دقیقاً یک نگاشت جاری و versioned از Payment
   منبع به Receipt مقصد.

Command باید کلید پایدار زیر یا معادل مصوب آن را داشته باشد:

```text
source_system + source_payment_id + source_payment_version
```

همان کلید و همان Payload باید نتیجه‌ی قبلی را برگرداند؛ همان کلید با Payload
متفاوت باید پیش از Mutation رد شود. Commit رسید باید یک Outbox یا Saga state
«ReceiptCreated / CrosswalkPending» بسازد تا شکست Write-back به Retry کور صدور
رسید تبدیل نشود.

حالت پذیرفته‌شده‌ی نهایی فقط وقتی مجاز است که UUID، Ref و No هر سه به یک Receipt
حل شوند. حالت number-only باید `PENDING_RECONCILIATION` یا `QUARANTINED` باشد، نه
موفقیت نهایی.

## ریسک و Gate

- `R-007` با شاهد split write-back پرداخت توسعه یافت؛
- `R-064` با شدت Critical برای Idempotency صدور Receipt و Crosswalk جاری افزوده
  شد؛
- Risk register اکنون ۶۴ ریسک، شامل ۳۶ Critical دارد؛
- Traceability تعداد ۲۵۲ تخصیص ریسک و صفر ماژول Command-ready دارد.

پیش از هر Write یا Retry در مقصد باید این Golden Caseها عبور کنند:

1. Cash، POS، Cheque و Receipt با یک نتیجه‌ی یکتا؛
2. Retry همان Payload قبل و بعد از هر Commit؛
3. Retry هم‌زمان از دو Worker؛
4. Payload متفاوت با همان Idempotency key؛
5. Fault پس از Receipt و پیش از Instrument؛
6. Fault پس از Instrument و پیش از Settlement؛
7. Fault پس از Settlement و پیش از Crosswalk؛
8. Fault هنگام نوشتن هر یک از UUID/Ref/No؛
9. بازیابی ۷۰ Payment number-only بدون ساخت Receipt تازه؛
10. تعیین تکلیف دو Payment چندهدف و چهار Payment دارای History با هدف مفقود.

## سطح اطمینان و محدودیت

- ساختار Procedure، ترتیب ایستای اثرها، جدول‌های مقصد و مرزهای Transaction:
  **اطمینان بالا**؛
- جمعیت و سازگاری Crosswalk در Snapshot Clone: **اطمینان بالا**؛
- اینکه تمام Historyهای تکراری ناشی از Retry یکسان‌اند: **اثبات نشده**؛
- اینکه هر History تکراری اثر مالی تکراری ساخته: **اثبات نشده و ادعا نمی‌شود**؛
- Branch دقیق هر اجرای تاریخی و علت ۹ هدف مفقود: بدون telemetry/Fault test قابل
  تعیین قطعی نیست.

## Artifactهای بازتولیدپذیر

- `scripts/sql/extract_varanegar_ngt_payment_replication_boundary.py`
- `artifacts/varanegar_analysis/domains/ngt_payment_replication_boundary_20260829.json`
- `scripts/sql/extract_varanegar_ngt_payment_replication_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/ngt_payment_replication_runtime_boundary_20260829.json`
- `scripts/windows/build_varanegar_ngt_payment_replication_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/varanegar_ngt_payment_replication_checkpoint_20260829.json`
- `tests/test_varanegar_ngt_payment_replication_boundary.py`
