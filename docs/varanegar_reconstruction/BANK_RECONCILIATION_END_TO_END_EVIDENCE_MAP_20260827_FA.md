# نقشهٔ انتها‌به‌انتهای شواهد مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **جمع‌بندی شواهد معتبر؛ Runtime parity و Command execution هنوز صفر است**

## نقشهٔ جریان

```text
BankAccount selection
  └─ BankAccount2 profile projection
       └─ Legacy DBF/TXT/XLS parser dispatch
            └─ Reconcile header + BankBill rows
                 ├─ Summary: 11 signed metrics
                 ├─ Match: 6 typed instrument families → ReconcileItem
                 ├─ Unmatch: legacy delete by BankBillId
                 ├─ Confirm: markers + cardex instrument flags
                 └─ Discard/Delete: rows only, header may remain

Target Negin ERP
  ├─ Versioned approved Profile catalog
  ├─ Isolated parser + atomic Staging
  ├─ Scoped Session/Rows/Links/Summary read model
  ├─ Explicit lifecycle state + computed match progress
  └─ Five atomic commands: Match / Unmatch / Confirm / Cancel / Reverse
```

## رابطهٔ Aggregateهای مقصد

```text
BankStatementFormatProfileFamily
  └─ 1..* immutable ProfileVersion
       └─ 1..* FieldMapping
       └─ 0..1 typed ParserOptions
       └─ 0..* ImportJob
            ├─ 1 SourceObject
            ├─ 0..* StagedRow
            ├─ 0..* Diagnostic
            └─ on atomic Commit → 1 ReconciliationSession
                                  ├─ 1..* StatementRow
                                  ├─ 0..* MatchLink
                                  │      └─ exactly 1 typed Instrument reference
                                  ├─ 1 computed Summary projection
                                  └─ 0..* Audit / Outbox events
```

Profile aggregate، ImportJob و ReconciliationSession سه مرز Transaction جدا
هستند. تنها `CommitImportJob` از Staging به Session پل می‌زند؛ Match/Confirm یا
Repository helper حق ایجاد Commit مستقل در Aggregate دیگر ندارند.

## Stage به Stage

| Stage | Legacy اثبات‌شده | قرارداد مقصد | Gate باز |
|---|---|---|---|
| انتخاب حساب/Profile | View `BankAccount2` با ۴۶ ستون؛ چهار Field Runtime و سه Format dispatch | سه Entity Profile نسخه‌دار/Approved/Hash-bound | Profile واقعی Clone صفر؛ تصمیم 004 |
| Import | DBF/TXT دو `SQLStatement` Profile را اجرا می‌کنند؛ XLS Query ثابت و Office boundary دارد | Worker محدود، Signature/Format validation و هیچ SQL/Provider/Office/Path اجرایی | Sample file/Profile Redacted و Parser parity |
| Persistence | Header پیش از Parser Commit می‌شود؛ هر Row Update مستقل و Partial import ممکن است | چهار Entity Staging، Preview hash-bound و Commit کامل Header/Rows/Audit/Outbox در یک Transaction | Target implementation و Failure injection |
| Row mapping | شش ستون Canonical؛ Debit غیرصفر Credit را کنار می‌زند؛ Dedup بدون Account/Profile scope | Mapping typed، Decimal مستقل و Fingerprint scoped | تصمیم 002/003 و Fixture واقعی |
| Summary | ۱۴ Parameter، یازده Formula، شش Type/Status predicate و UI علامت/رنگ دقیق | چهار Projection، پنج Query scoped و Signed decimal API | Fixture یازده‌خروجی و دو Alias املایی |
| Match | شش نگاشت PCheque/PWithdraw/RBankDraft/RCashDraft/RCheque/Transfer؛ Grid path persistence فوری | Command صریح با Candidate snapshot، Version، Idempotency، Audit/Outbox | Tolerance/Conflict policy و UAT |
| Unmatch | Procedure همهٔ Linkهای یک `BankBillId` را حذف می‌کند؛ `LinkId` scope و Instrument reset صفر | حذف دقیق یک `link_id` فقط در Open state | Implementation و Regression tests |
| Confirm | Outer transaction Markerها را Commit می‌کند؛ Procedure نامرتب پس از اولین Link Return دارد | Prevalidate همه Linkها، Update همه Instrumentها و Marker در یک Transaction | Summary parity، SoD، Failure injection |
| Discard/Cancel | Discard فقط Collection ردیف‌ها را Delete/Update می‌کند؛ Header mutation صفر | Cancel مستقل و Archive/Transition اتمیک | تصمیم 007/Retention |
| Reverse | مسیر Legacy مستقل اثبات نشده؛ Unmatch معادل Reverse نیست | Capability/Role/State/Command مستقل و Reversal همه Instrumentها | تصمیم 006، Accounting policy و UAT |
| Authorization | دو Alias Legacy، هفت Child و Aggregate حق؛ مجوز فردی اثبات نشده | هفت Capability، شش Role، Deny-first + Feature/Scope/Date/State/Domain | هفت Principal slot و اجرای ۱۰۰ UAT |
| Root/navigation | Setup واقعی است ولی Launcher نامعلوم؛ List preview/template؛ SpecialOptionsDistrict مبهم | Route فقط با Runtime/Owner evidence | Telemetry سه Session و سه تصمیم Scope |

## Defectها و Non-inferenceهای حیاتی

1. Confirm Legacy در هر اجرا حداکثر یک Instrument را Mark می‌کند؛ این رفتار
   Regression test است، نه Requirement مقصد.
2. `ConfirmerId/ConfirmDate` Marker هستند؛ `Amount=0` نتیجهٔ Summary نیست.
3. Unmatch Legacy همه Linkهای Bill را پاک می‌کند و Instrument flag را Reset نمی‌کند.
4. Parser failure یا Discard می‌تواند Header خالی باقی بگذارد.
5. `RBANKDARFT/RBANKDRAFT` و `RCASHDRAF/RCASHDRAFT` بدون تصمیم/Parity Normalize نمی‌شوند.
   Snapshot تجمیعی Clone برای زوج دوم `0/146576` ثبت کرده و ریسک حذف Legacy را
   تقویت می‌کند، ولی نتیجهٔ Procedure یا رفتار Production را ثابت نمی‌کند.
6. وجود HDR/StartRow/Seperator/IsArabic در جدول به معنی مصرف Runtime نیست.
7. `Edit` حق Confirm و `Delete` حق Cancel/Reverse نمی‌سازد.
8. Aggregate permission count دسترسی هیچ فرد معینی را ثابت نمی‌کند.
9. نبود Reference استاتیک برای سه Root مجوز حذف یا خروج از Scope نیست.
10. صفر بودن Snapshot جاری اثبات سلامت Production نیست؛ Clone Fixture ندارد.

## آنچه الان واقعاً آماده است

- شروع محدود Schema/Query برای Profile catalog؛
- ساخت Parser worker و Staging ایزوله در Target test environment؛
- ساخت Read model/Summary پشت Gate Parity؛
- State machine، Command envelope، UAT runbook و Evidence request pack به‌عنوان
  قرارداد آماده‌اند، نه اجرای Command.

Match/Unmatch/Confirm/Cancel/Reverse، Pilot و Production هنوز آماده نیستند.

## اعداد Checkpoint

- ۳۰ Artifact ورودی قرارداد آمادگی؛
- ۱۱۶ Acceptance تفاضلی، ۹۳ Golden و ۱۰۰ UAT بدون هویت؛
- هفت تصمیم مالک، Approved صفر؛
- ۱۶۷ Source در Drift baseline همان Checkpoint بانک با `NO_SEMANTIC_DRIFT`؛
- ۱۸ Domain و ۱۷۸ Artifact ماشین‌خوان Bundle با `PASS`؛
- ۱۴۵ تست شواهد Pass؛
- Operational write، Form/Procedure execution و Business-row change صفر.

## نقطهٔ شروع بعدی

بستهٔ `BANK_RECONCILIATION_EVIDENCE_ACCESS_REQUEST_PACK_20260827_FA.md` نه درخواست
کم‌دسترسی را به ترتیب Snapshot/Profile/Summary → Owner/UAT → Failure/Root مشخص
کرده است. هیچ Production write access برای ادامهٔ شناخت لازم نیست.
