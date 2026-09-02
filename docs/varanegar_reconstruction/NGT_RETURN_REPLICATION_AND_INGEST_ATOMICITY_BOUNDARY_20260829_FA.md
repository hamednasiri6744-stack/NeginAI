# مرز Replication، Crosswalk و Update برگشت NGT — ۲۰۲۶-۰۸-۲۹

## نتیجهٔ اجرایی

برگشت موبایلی NGT دو مرز شکست مستقل دارد:

1. ساخت RetOrder/RetSale در BackOffice و ثبت نتیجه در NGT یک Commit واحد نیست؛
2. به‌روزرسانی Header/Line/QtyDetail برگشت در `UpdateFromNGT` یک Aggregate
   transaction واحد نیست.

Snapshot فقط‌خواندنی دو Header و دو Line فعال دارد. یک Line هیچ History برگشتی
ندارد و فقط می‌توان آن را Pending/Rejected/Unattempted نامعین دانست. Line دیگر
یک نتیجهٔ دقیق `TourHistory(Type=2)` و Write-back سفارش برگشت دارد، اما RetOrder
هدف در Snapshot جاری وجود ندارد. هیچ‌کدام هدف RetOrder جاری ندارند. این وضعیت
علت تاریخی خطا یا وجود Duplicate فعلی را ثابت نمی‌کند، ولی Recreate خودکار را
ناامن می‌کند.

## مسیر Replication مستقر

```text
TourDomain.ReplicateTour
  ├─ NewReplicateTour                         offset 2358
  ├─ BeginTransaction مدیریت‌شده             offset 2524
  ├─ Commit میانی                            offset 18667
  ├─ 6 setter خط ReturnOrder/ReturnInvoice   offset 38911+
  ├─ 2 setter collection سفارش برگشت         offset 44725+
  └─ Commitهای بعد از Write-back

dbo.NGT_DoReplicateTour
  ├─ Transaction + TRY/CATCH/Rollback
  ├─ EXEC dbo.NGT_ReplicateTour
  ├─ COMMIT نتیجهٔ BackOffice
  └─ سپس Write-back ReturnOrder روی NGT line
```

IL پنج Assembly فقط به‌صورت PE metadata و byte خوانده شد؛ هیچ Assembly Load یا
Execute نشد. در `ReplicateTour` شش setter خطی برای UUID/Ref/No سفارش و فاکتور
برگشت و دو setter سطح Call برای مجموعه شماره‌های سفارش برگشت دیده شد. فراخوانی
`NewReplicateTour` پیش از اولین Transaction مدیریت‌شده و پیش از همهٔ setterهاست؛
Commit نیز در ترتیب IL هم قبل و هم بعد از setterها دیده می‌شود.

SQL این مرز را مستقل تأیید می‌کند: `dbo.NGT_DoReplicateTour` پس از اجرای
`NGT_ReplicateTour` Commit می‌کند و سپس Crosswalk سفارش برگشت را روی Lineهای NGT
می‌نویسد. این یک failure window ساختاری است؛ Branch دقیق و احتمال وقوع فقط با
Fault injection ایزوله قابل اندازه‌گیری است.

## نبود Guard یکتای مرتبط

- تنها Unique index مشاهده‌شده روی `TourHistory.EntityUniqueId` فیلتر
  `Type=1` دارد و از Typeهای برگشت ۲/۱۲ محافظت نمی‌کند؛
- هیچ Unique index روی ستون‌های `BackOfficeReturn*` در
  `NGT.CustomerCallReturnLines` وجود ندارد؛
- بنابراین کنترل هم‌زمانی و Retry برگشت به Constraint پایگاه داده متکی نیست.

در Snapshot جاری فقط یک History نوع ۲ وجود دارد، Duplicate group جاری صفر است
و Type=12 وجود ندارد. نبود Duplicate فعلی، نبود امکان Race/Retry تکراری را ثابت
نمی‌کند.

## وضعیت جاری و قرارداد مهاجرت

| حالت | تعداد Line | رفتار مجاز مقصد |
|---|---:|---|
| بدون History برگشت | ۱ | بدون شاهد Authoritative سند جدید نساز؛ وضعیت را تعیین تکلیف کن |
| History نوع ۲ + Write-back + هدف جاری مفقود | ۱ | Quarantine؛ Recreate خودکار ممنوع |
| RetOrder جاری معتبر | ۰ | — |
| Write-back فاکتور برگشت | ۰ | — |

UUID مدل NGT، شناسهٔ عددی FRU، `TourHistory.EntityUniqueId` و شناسه/شمارهٔ سند
BackOffice باید با نقش و Provenance جدا نگهداری شوند. FKهای RetOrder/RetSale به
مدل عددی FRU اشاره می‌کنند، نه UUID مدل NGT.

## مرز UpdateFromNGT

`CustomerCallReturnDomain.UpdateFromNGT` در IL:

- چهار setter حذف منطقی روی Line/Detailهای ادغام‌شونده؛
- یک setter `IsCanceled` روی Header؛
- سه `SaveChanges`؛
- صفر سیگنال Begin/Commit/Rollback محلی.

Caller مشاهده‌شده یعنی `CustomerCallDomain.UpdateFromNGT` نیز یک `SaveChanges`
دیگر و صفر سیگنال Transaction دارد. بنابراین Header، Line، QtyDetail و Tombstone
ها چهار durable boundary در یک Graph منطقی دارند. این شاهد وجود Incident جاری
نیست و وجود Ambient transaction خارج از متدهای دیده‌شده را مطلقاً نفی نمی‌کند؛
اما قرارداد مقصد باید یک Aggregate transaction صریح باشد.

## طراحی لازم برای ERP شخصی نگین

1. `ReturnReplicationAttempt` تغییرناپذیر با idempotency key و payload hash؛
2. `ReturnCrosswalkHistory` append-only و `CurrentReturnCrosswalk` یکتای نسخه‌دار؛
3. Outbox یا Saga برای اتصال Commit BackOffice به انتشار Crosswalk؛
4. Reconciliation که هدف Commit‌شده و Write-back مفقود را پیدا کند و فقط لینک
   را ترمیم کند، نه اینکه سند مالی/انبار تازه بسازد؛
5. Aggregate transaction واحد برای Header/Line/QtyDetail/Tombstone؛
6. optimistic concurrency و Fault test قبل/بعد از هر مرز Legacy؛
7. Quarantine جدا برای No-history، Historical-target-missing و Conflict.

`R-066` با شدت بحرانی برای Replication/Idempotency و `R-067` با شدت بالا برای
Atomicity ورودی افزوده شد. رجیستر اکنون ۶۷ ریسک، ۳۸ بحرانی، ۲۶ بالا، ۲۶۳ اتصال
Traceability و صفر ماژول Command-ready دارد.

## Artifactها و بازتولید

- `scripts/sql/extract_varanegar_ngt_return_replication_boundary.py`
- `scripts/sql/extract_varanegar_ngt_return_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/ngt_return_replication_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_return_runtime_boundary_20260829.json`
- `tests/test_varanegar_ngt_return_replication_boundary.py`
- `scripts/windows/build_varanegar_ngt_return_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/varanegar_ngt_return_checkpoint_20260829.json`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_ngt_return_replication_boundary.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_return_replication_boundary_20260829.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_ngt_return_runtime_boundary.py `
  --source-directory "\\192.168.1.171\exe\NGTApp\Server\bin" `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_return_runtime_boundary_20260829.json

G:\NeginAI\.venv\Scripts\python.exe -m pytest `
  G:\NeginAI\tests\test_varanegar_ngt_return_replication_boundary.py -q

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\build_varanegar_ngt_return_checkpoint_20260829.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\varanegar_ngt_return_checkpoint_20260829.json
```

## حدود شاهد

- هیچ Endpoint، Stored Procedure یا Assembly اجرا نشده است؛
- هیچ UUID، شماره سند، مشتری، مبلغ، متن SQL یا ردیف خام ذخیره نشده است؛
- دو ردیف جاری نمونهٔ آماری کافی برای برآورد Frequency نیستند؛
- Linear IL برای ترتیب ساختاری شاهد قوی است، اما Reachability هر Branch به Fault
  test نیاز دارد؛
- تصمیم Reversal/Retain/Recreate برای هدف تاریخی مفقود باید با مالک فروش، انبار
  و مالی تأیید شود.
