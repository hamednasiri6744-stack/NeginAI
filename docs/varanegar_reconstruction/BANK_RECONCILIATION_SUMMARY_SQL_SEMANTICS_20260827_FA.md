# معنای Redacted فرمول‌های SQL Summary مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ فرمول ایستا اثبات شد، اجرای Procedure و Row-result parity صفر است**

## روش و مرز ایمنی

تعریف `dbo.DoReconcile_GetSummary` از `sys.sql_modules` در Clone فقط‌خواندنی
خوانده و فقط در حافظه Parse شد. متن SQL، Literalهای غیرمجاز و دادهٔ تجاری ذخیره
نشدند. حساب تحلیل `can_update=0` و `db_denydatawriter` است؛ Procedure اجرا نشد.

Definition جاری ۳٬۰۷۰ Character، چهارده پارامتر و شش Dependency دارد. سیزده
Pattern فرمول/Branch همگی Match شدند و هیچ Keyword جهش‌داده‌ای
`INSERT/UPDATE/DELETE/MERGE` دیده نشد.

## یازده فرمول اثبات‌شده

1. `RemainingLastReconcile`: اگر برای حساب هیچ `Reconcile.Amount` غیر Null نیست،
   اولین `BankBill.Balance` همان Reconcile بر اساس `BankBillId ASC`؛ در غیر این
   صورت آخرین `Reconcile.Amount` حساب بر اساس `ReconcileDate DESC`.
2. `RemainingThisPeriod = SUM(BankBill.VocherCredit) - SUM(BankBill.VocherDebit)`
   با Scope برابر Reconcile و `VocherDate <= input`.
3. `RemainingBill = RemainingLastReconcile - RemainingThisPeriod`.
4. `RemainingCardex = SUM(BankAccountCardex.Credit) - SUM(Debit) + InitialBalance`
   با Scope حساب، تاریخ و Predicate نوع/وضعیت.
5. `BillDebitOpenItems = SUM(FreeBankBill.VocherDebit)` در Reconcile.
6. `BillCreditOpenItems = SUM(FreeBankBill.VocherCredit)` در Reconcile.
7. `CardexDebitOpenItems = SUM(FreeBankAccountCardex.Debit)` تا تاریخ حساب.
8. `CardexCreditOpenItems = SUM(FreeBankAccountCardex.Credit)` تا تاریخ حساب.
9. `RealRemainingBill = RemainingBill + CardexDebitOpenItems - CardexCreditOpenItems`.
10. `RealRemainingCardex = RemainingCardex + BillDebitOpenItems - BillCreditOpenItems`.
11. `Reconcile = RealRemainingCardex - RealRemainingBill`.

تمام Aggregateهای Null با `ISNULL(...,0)` به صفر Normalized می‌شوند.

## Predicate حساس Type/Status

Summary دقیقاً این شش ثابت را برای `BankAccountCardex` می‌پذیرد:

| Type | Status لازم |
|---|---:|
| RCHEQUE | ۳ |
| RBANKDARFT | ۱ |
| PCHEQUE | ۳ |
| TRANSFER | ندارد |
| PWITHDRAW | ندارد |
| RCASHDRAF | ندارد |

دو اختلاف املایی مادی‌اند: Match از `RBANKDRAFT` و `RCASHDRAFT` استفاده می‌کند،
اما Summary دارای `RBANKDARFT` و `RCASHDRAF` است. این‌ها نباید با «تصحیح املا»
ادغام شوند؛ Fixture واقعی باید نشان دهد Alias، قرارداد تاریخی یا Bug هستند.

## اثر روی ERP مقصد

اکنون ساخت Candidate فقط‌خواندنی Summary ممکن است، اما Pilot هنوز ممنوع است:

- تاریخ `varchar(10)` باید با Typed date و Fixture شمسی Parity شود؛
- Branch ماندهٔ اولیه باید Caseهای «بدون Reconcile قبلی» و «با Reconcile قبلی» داشته باشد؛
- دو Alias املایی باید روی دادهٔ واقعی Redacted تست شوند؛
- همهٔ یازده نتیجه باید Row-by-row با Legacy مقایسه شوند؛
- `Reconcile.Amount=0` در Confirm جایگزین هیچ‌یک از این فرمول‌ها نیست.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_summary_sql_semantics_20260827.json`
- `scripts/sql/extract_varanegar_bank_reconciliation_summary_sql_semantics.py`
- `tests/test_varanegar_ui_evidence.py`

این سند منطق Definition جاری Clone را ثابت می‌کند، نه نتیجهٔ Runtime یا صحت
کسب‌وکاری آن را.
