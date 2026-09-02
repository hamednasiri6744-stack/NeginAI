# مرز Match در مغایرت بانکی وارانگار

## نتیجه

مسیر واقعی Match از فرم `TreasuryOld.Forms.frmReconciliation` تا
`ReconcileItem` با تحلیل ایستای IL و کاتالوگ فقط‌خواندنی Clone تثبیت شد. نام
`DoVocherPass` گمراه‌کننده است: در این مسیر سند حسابداری صادر نمی‌شود؛ یک Link
تطبیق میان ردیف صورتحساب بانک و دقیقاً یکی از شش نوع منبع خزانه ساخته و با
`ReconcileItem.Update` ذخیره می‌شود.

این شاهد نتیجهٔ یک UI احراز هویت‌شده یا Commit موفق روی دادهٔ واقعی نیست. هیچ
فرم، Assembly، Procedure، Trigger یا Hook اجرا نشده و هیچ business row، تعریف
SQL، هویت یا literal ناشناخته در Artifact نگهداری نشده است.

## نگاشت نوع منبع به FK

| Type در Cardex | FK در ReconcileItem |
|---|---|
| `PCHEQUE` | `PChequeId` |
| `PWITHDRAW` | `PWithdrawId` |
| `RBANKDRAFT` | `RBankDraftId` |
| `RCASHDRAFT` | `RCashDraftId` |
| `RCHEQUE` | `RChequeId` |
| `TRANSFER` | `TransferId` |

هر شاخه `BankBillId` و `BankAccountCardexId` را از دو Grid می‌گیرد، FK نوع‌دار
را تنظیم می‌کند، AppUser/ModifiedDate را ثبت می‌کند و سپس مسیر
`ReconcileItem.Update` را فراخوانی می‌کند. مقصد باید invariant «دقیقاً یک FK
نوع‌دار» را در دامنه و پایگاه داده enforce کند؛ `Type` آزاد یا چند FK هم‌زمان
مجاز نیست.

## رفتار UI قدیمی

دو Event زیر Match را بلافاصله اجرا می‌کنند:

- `grdBankAccountCardex_CellValueChanged`
- `grdBankBill_SelectionChanged`

هر دو روی `Credit`، `Debit`، `VocherCredit` و `VocherDebit` محاسبه دارند، سیگنال
برابری دقیق Decimal و `Math.Abs` دیده می‌شود، تأیید کاربر می‌گیرند،
`DoVocherPass` را صدا می‌زنند و سپس Gridها و Summary را Refresh می‌کنند. این
شاهد برای تعیین tolerance، ارز، rounding یا جهت debit/credit کافی نیست؛ سیاست
مبلغ باید با مالک فرایند و Golden case واقعی تأیید شود.

Persistence مستقیم از Event گرید برای Web ممنوع است. مقصد باید فرمان صریح
`bank_reconciliation.match_instrument` داشته باشد و Event مرور/انتخاب صرفاً
state سمت کاربر را تغییر دهد.

## Read model و Scope

`RefreshGrids` این مسیرها را فراخوانی می‌کند:

- `FreeBankAccountCardexAdapter.GetFreeBankAccountCardexSWhere`
- `FreeBankBillAdapter.GetFreeBankBillSWhere`
- `BankBillAdapter.GetBankBillSWhere`
- `ReconcileItemAdapter.GetReconcileItemSByBankBillS`

فیلترهای allowlist‌شده، BankAccount، تاریخ `DateOf`/`VocherDate` تا تاریخ انتخابی
و Linkهای موجود ReconcileItem را نشان می‌دهند. در Clone، Viewهای
`FreeBankAccountCardex`، `FreeBankBill` و `BankBill2` حاضرند؛ ۲۷ ستون و ۱۱
وابستگی کاتالوگی بدون خواندن تعریف View یا ردیف تجاری ثبت شد. Summary از
`ReconcileAdapter.GetSummary` می‌آید. این متد `dbo.DoReconcile_GetSummary` را در
یک Transaction Legacy صدا می‌زند. امضای کاتالوگی روال ۱۴ پارامتر دارد:

- ورودی‌ها: `ReconcileId:int`، `VocherDate:varchar(10)` و
  `BankAccountId:int`؛
- خروجی‌های `money`: `RemainingLastReconcile`، `RemainingThisPeriod`،
  `RemainingBill`، `RemainingCardex`، `BillDebitOpenItems`،
  `BillCreditOpenItems`، `CardexDebitOpenItems`، `CardexCreditOpenItems`،
  `RealRemainingBill`، `RealRemainingCardex` و `Reconcile`.

شش dependency کاتالوگی روال عبارت‌اند از BankAccount، BankAccountCardex،
BankBill، FreeBankAccountCardex، FreeBankBill و Reconcile. نام/نوع/جهت پارامترها
در این Artifact اثبات شده‌اند ولی Definition عمداً خوانده نشده بود. Artifact
مکمل `BANK_RECONCILIATION_SUMMARY_SQL_SEMANTICS_20260827_FA.md` بعداً یازده
فرمول ایستا را Redacted اثبات کرد؛ علامت/Row-result parity هنوز Fixture می‌خواهد.

## مرز Transaction و Hook

`ReconcileItem.Update` Transaction استاتیک Legacy را Start/Commit/Rollback
می‌کند. Adapter پیش و پس از Update، وجود `BeforeReconcileItem` و
`AfterReconcileItem` را در Runtime probe می‌کند؛ هر دو نام در IL دیده شدند اما
در Clone حاضر نیستند.

در ERP مقصد:

- مالک Transaction فقط Application service است و Repository حق Commit ندارد.
- Retry با idempotency key و optimistic version کنترل می‌شود.
- Audit و Outbox در همان local transaction نوشته می‌شوند.
- کشف اختیاری Hook در Runtime حذف و side effectها صریح و نسخه‌دار می‌شوند.
- Unmatch فرمان جداگانه است و با انتخاب/لغو انتخاب گرید یکی نیست.

دو Handler عمومی حذف رکورد گرید (`vGrid_DeletingRecords` و
`vGrid_RecordsDeleted`) بدنهٔ مؤثر ندارند؛ شاهد Unmatch همان مسیر مستقل دکمهٔ
Delete و `BankBillAdapter.DeleteReconcileItem` است.

## قرارداد مقصد

سه Query لازم عبارت‌اند از:

- `bank_reconciliation.unmatched_statement_rows`
- `bank_reconciliation.match_candidates`
- `bank_reconciliation.summary`

Summary مقصد این ۱۱ metric نام‌دار را از Query service برمی‌گرداند، نه با اجرای
مستقیم Stored Procedure Legacy از Web. تا قبل از fixture/parity، نام metric
قرارداد است؛ فرمول ایستا اکنون اثبات شده ولی نتیجهٔ Runtime provisional می‌ماند.

فرمان Match باید account و as-of-date را enforce کند، دقیقاً یک منبع نوع‌دار را
بپذیرد، rule مبلغ تأییدشده داشته باشد، در یک Unit of Work اجرا شود و پاسخ Retry
پایدار بدهد. پیاده‌سازی یا فعال‌سازی عملیاتی هنوز انجام نشده است.

## بازتولید

```powershell
.\.venv\Scripts\python.exe scripts\sql\extract_varanegar_bank_reconciliation_matching_boundary.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --output artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_matching_boundary_20260827.json
```

خروجی فعلی `PASS` است: ۱۵ Method، شش نگاشت نوع‌دار، دو Event تطبیق، چهار ستون
مبلغ، پنج Object کاتالوگی، ۲۷ ستون View، ۱۱ Dependency برای Viewها، ۱۴ پارامتر
و شش Dependency برای Summary، صفر Hash mismatch، صفر خطای parse و صفر خطای
validation.
