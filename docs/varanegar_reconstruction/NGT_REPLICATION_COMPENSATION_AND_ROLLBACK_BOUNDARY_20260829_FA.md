# مرز جبران Replication و Rollback در NGT — ۲۰۲۶-۰۸-۲۹

## نتیجهٔ اجرایی

مسیر جبران مستقر، `dbo.NGT_RollBackTour` است؛ Procedure هم‌نام قدیمی‌تر یعنی
`dbo.USP_NGT_UndoReplicateTour` کنترل عملیاتی قابل اتکا نیست. این Procedure در
ابتدای بدنه `RETURN` می‌کند و تمام ۲۱ Mutation مشاهده‌شدهٔ بعدی داخل Comment
قرار دارند.

مسیر فعال برای رسیدهای فعلی نیز کامل نیست. در دادهٔ فقط‌خواندنی، ۳۴۲ Receipt
متمایز از `TourHistory(Type=10)` هنوز وجود دارند و هر ۳۴۲ مورد حداقل یک وابستگی
فعال `NO_ACTION` از CashDetail، ChequeHistory یا Settlement payment دارند؛ ولی
`NGT_RollBackTour` دو جدول اول را پاک نمی‌کند و پاک‌سازی Payment را فقط از
`TourHistory(Type=11)` می‌گیرد، در حالی که Snapshot هیچ Type=11 ندارد.

این نتیجه یک **نقص ساختاری تأییدشده** در Compensator مستقر است، نه ادعای اینکه
در عملیات واقعی چند بار Rollback اجرا یا خطا داده است. هیچ Procedure یا Endpoint
اجرا نشده و هیچ Fault injection روی سیستم زنده انجام نشده است.

## مسیر واقعی Runtime

```text
SaveTourData / ReplicateTour
          │
          ▼
TourDomain.RollBackTour (20 IL instructions)
  ├─ RequestType = 20
  └─ ReplicatedCalls = ReplicateResult collection
  └─ نتیجهٔ RetrieveInfo با IL opcode `pop` دور ریخته می‌شود
          │
          ├─ VnLiteTourAdapter.RetrieveInfo / case 20
          └─ VnSdsTourAdapter.RetrieveInfo  / case 20
                    │
                    ├─ select ReplicateResult.EntityUniqueId
                    ├─ create/fill EntityUniqueId temp table
                    ├─ execute dbo.NGT_RollBackTour
                    ├─ Commit on success
                    └─ Rollback and false on exception
```

شواهد IL در پنج Assembly فقط به‌صورت PE metadata و IL byte خوانده شد؛ Assembly
Load یا Execute نشد. دو Adapter مستقل دقیقاً قرارداد زیر را دارند:

| مؤلفه | VnLite | VnSds |
|---|---:|---:|
| Branch درخواست | ۲۰ | ۲۰ |
| انتخاب‌گر `EntityUniqueId` | ۱ | ۱ |
| افزودن به collection جدول موقت | ۱ | ۱ |
| Execute در Branch | ۳ | ۳ |
| Commit | ۱ | ۱ |
| Rollback در Catch | ۱ | ۱ |
| اشاره به `NGT_RollBackTour` | ۱ | ۱ |

سه Execute به ترتیب برای ساخت Schema/temp، پرکردن temp و اجرای Procedure دیده
می‌شوند. در Branch 20 هیچ setter برای Crosswalkهای BackOffice ثبت نشد. رشته‌های
SQL خام ذخیره نشده‌اند؛ فقط Hash، طول و signal امن نام Procedure نگهداری شده است.

نکتهٔ کنترل خطا: `TourDomain.RollBackTour` یک بار `RetrieveInfo` را فراخوانی
می‌کند و دستور بلافاصلهٔ بعدی IL، `pop` است. بنابراین مقدار Boolean برگشتی
Adapter ــ از جمله `false` پس از Catch/Rollback ــ در Business دور ریخته می‌شود.
Callerهای `SaveTourData` و `ReplicateTour` نیز متد Business را بدون نتیجه صدا
می‌زنند. پس شکست جبران می‌تواند بدون یک سیگنال موفقیت/شکست قابل بررسی به Caller
برگردد؛ این شاهدِ رفتار استاتیک مسیر است، نه اثبات تعداد رخداد واقعی آن.

## دو Procedure که نباید با هم اشتباه شوند

### ۱. `dbo.NGT_RollBackTour` — مسیر فعال

- ورودی مستقیم ندارد و به `#EntityUniqueIdList` ساخته‌شده توسط Adapter وابسته است؛
- Transaction محلی ندارد؛ Transaction را Adapter مالک است؛
- برای Typeهای مختلف History رفتار متفاوت دارد؛
- در پایان، Historyهای Entityهای ورودی را حذف می‌کند.

رفتار استاتیک آن:

| Type | هدف مورد انتظار | رفتار Rollback |
|---:|---|---|
| ۱ | Order | حذف `visit_BOOrder`، Item و Header |
| ۲ | Return order | حذف Item و Header |
| ۸ | Sale | تبدیل Sale به Voucher با Procedure دیگر |
| ۱۰ | Receipt | حذف Cash، Cheque، BankOrder و Receipt |
| ۱۱ | Payment/Settlement | حذف `Acc.tblPayments` بر اساس History مستقل |
| ۱۲ | Return sale | حذف Item، Voucher مرتبط و Header |
| ۱۶ | Cancelled sale | بازگرداندن `CancelFlag` |
| ۱۷ | Distributed sale | بازگرداندن `DistRef` و حذف Voucher نوع ۴۶ |

نکتهٔ مهم: متن Procedure به `RCashDetail` و `Acc.tblChqHist` اشاره نمی‌کند.
بنابراین حذف Parentهای Cash و Cheque به‌تنهایی Dependencyهای آن‌ها را جمع نمی‌کند.

### ۲. `dbo.USP_NGT_UndoReplicateTour` — مسیر مرده

- در خط اجرایی آغازین `RETURN` دارد؛
- تمام Mutationهای بعدی داخل یک block comment هستند؛
- کد Commentشده برخلاف Procedure فعال، `RCashDetail` و `tblChqHist` را هم در
  ترتیب حذف آورده است؛
- وجود این متن فقط Intent تاریخی را نشان می‌دهد و نباید به‌عنوان Control فعال
  یا امکان Undo در ERP مقصد مدل شود.

## وضعیت جاری TourHistory

| Type | History | Entity متمایز | هدف شناخته‌شدهٔ موجود |
|---:|---:|---:|---:|
| ۱ | ۱٬۱۱۸٬۲۴۴ | ۱٬۱۱۸٬۲۴۴ | ۱٬۱۱۲٬۷۱۱ |
| ۲ | ۱ | ۱ | ۰ |
| ۸ | ۳٬۷۳۱ | ۳٬۵۹۳ | ۳٬۷۳۱ |
| ۱۰ | ۴۴۷ | ۳۴۴ | ۴۳۸ History / ۳۴۲ Receipt متمایز |

Typeهای ۱۱، ۱۲، ۱۶ و ۱۷ در Snapshot جاری صفرند. نبود Type=11 مهم است، چون
تنها Delete مربوط به `Acc.tblPayments` در Procedure فعال از همین Type تغذیه
می‌شود.

## چرا Receipt Rollback فعلی گیر می‌کند

برای ۳۴۲ Receipt موجودِ Type=10، شکل Dependency ناشناس زیر مشاهده شد:

| وابستگی | تعداد Receipt |
|---|---:|
| دارای RCash | ۷۲ |
| دارای RCashDetail | ۷۲ |
| دارای Cheque | ۶۴ |
| دارای ChequeHistory | ۶۴ |
| دارای BankOrder | ۳۳۰ |
| دارای `tblPayments.DocReceiptId` | ۳۴۲ |
| Payment متصل به RCash | ۷۲ |
| Payment متصل به Cheque | ۶۴ |
| Payment متصل به BankOrder | ۳۳۰ |
| دارای حداقل یک Blocker واقعی `NO_ACTION` | ۳۴۲ |

FKهای کلیدی همگی Enabled و `NO_ACTION` هستند:

- `RCashDetail.RCashId → RCash.RCashId`؛
- `tblChqHist.ChqRef → TblCheque.ID`؛
- `tblPayments.RCashId → RCash.RCashId`؛
- `tblPayments.ChqRef → TblCheque.ID`؛
- `tblPayments.BankOrderRef → TblBankOrders.ID`.

هیچ Trigger هدف از نوع `INSTEAD OF` نیست. بنابراین Triggerهای AFTER نمی‌توانند
قبل از بررسی FK این Parentها را قابل حذف کنند. FKهای مرتبط غالباً untrusted
هستند، اما Disabled نیستند؛ Aggregateهای Join نیز وجود واقعی Childهای فعلی را
نشان می‌دهند.

ترتیب Procedure فعال Cash، Cheque و BankOrder را قبل از Receipt حذف می‌کند،
اما Childهای بالا را حذف نمی‌کند. پس برای شکل فعلی Receipt، آن Deleteها با
وابستگی‌های فعال برخورد دارند. چون Branch Adapter در RequestType 20 فقط temp
table، Procedure و Commit/Rollback را اجرا می‌کند، پاک‌سازی مکمل دیگری در همان
Branch مشاهده نشد.

## پیامد برای ERP شخصی نگین

Rollback نباید یک Delete جمعی مبهم باشد. مدل مقصد باید این اجزا را جدا کند:

1. `ReplicationAttempt` تغییرناپذیر با idempotency key و payload hash؛
2. `CurrentCrosswalk` یکتا و نسخه‌دار؛
3. `CompensationRequest` با وضعیت Requested/Running/Blocked/Completed؛
4. برنامهٔ جبران وابسته به نوع ابزار مالی و ترتیب FK؛
5. Reversal مالی یا Void رسمی به‌جای حذف، هرجا سند وارد چرخهٔ حسابداری شده است؛
6. حفظ History و Evidence تا پایان موفق جبران؛
7. صف قرنطینه برای تعارض، هدف مفقود یا Dependency جدیدتر.

پیش از مجاز شدن Command مقصد، Fault test باید بعد از هر مرحلهٔ Receipt، Cash،
Cheque، BankOrder، Settlement، History و Crosswalk تزریق شود و نشان دهد که
Retry و Compensation هم‌زمان فقط به یک نتیجهٔ جاری همگرا می‌شوند.

## ریسک و Traceability

`R-065` با شدت `CRITICAL` اضافه شد. پس از این مرز:

- ۶۵ ریسک باز؛
- ۳۷ ریسک بحرانی؛
- ۲۵ ریسک بالا؛
- ۳ ریسک متوسط؛
- ۲۵۶ اتصال Requirement↔Risk؛
- صفر ماژول Command-ready.

این صفر یعنی شناخت برای طراحی بیشتر شده، اما مسیر نوشتن هنوز تا تکمیل
Idempotency، Saga، Reversal، Fault injection و Reconciliation مجاز نیست.

## Artifactها و بازتولید

- `scripts/sql/extract_varanegar_ngt_replication_compensation_boundary.py`
- `scripts/sql/extract_varanegar_ngt_replication_compensation_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/ngt_replication_compensation_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_replication_compensation_runtime_boundary_20260829.json`
- `tests/test_varanegar_ngt_replication_compensation_boundary.py`
- `scripts/windows/build_varanegar_ngt_replication_compensation_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/varanegar_ngt_replication_compensation_checkpoint_20260829.json`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_ngt_replication_compensation_boundary.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_replication_compensation_boundary_20260829.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_ngt_replication_compensation_runtime_boundary.py `
  --source-directory "\\192.168.1.171\exe\NGTApp\Server\bin" `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_replication_compensation_runtime_boundary_20260829.json

G:\NeginAI\.venv\Scripts\python.exe -m pytest `
  G:\NeginAI\tests\test_varanegar_ngt_replication_compensation_boundary.py -q

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\build_varanegar_ngt_replication_compensation_checkpoint_20260829.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\varanegar_ngt_replication_compensation_checkpoint_20260829.json
```

## حدود شاهد

- هیچ Rollback واقعی اجرا نشده است؛ تعداد و زمان رخداد عملیاتی نامعلوم است.
- Current-state aggregate تاریخچهٔ کامل تلاش‌های جبران را بازسازی نمی‌کند.
- متن Commentشده رفتار اجرایی نیست.
- رفتار شاخه‌های IL با کنترل جریان استاتیک تعیین شده؛ نتیجهٔ واقعی خطا فقط با
  Fault injection در محیط ایزوله قابل اثبات است.
- طراحی Reversal نهایی باید با مالک مالی دربارهٔ وضعیت سند و ممنوعیت حذف پس از
  ثبت حسابداری تأیید شود.
