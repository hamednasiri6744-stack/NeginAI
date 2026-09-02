# مدل منبع مغایرت‌گیری بانکی وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS روی Clone فقط‌خواندنی؛ قرارداد طراحی، نه Result parity**

## نتیجه روشن

مغایرت‌گیری بانکی در وارانگار یک CRUD روی یک جدول نیست. Aggregate مشاهده‌شده
از Session مغایرت‌گیری، فایل/قالب ورودی بانک، ردیف‌های صورتحساب و لینک‌های
چندنــوعی به ابزارهای خزانه ساخته می‌شود. مسیر تأیید نیز Signal صریح برای
Transaction و به‌روزرسانی کاردکس حساب بانکی دارد.

## شواهد ساختاری

- ۱۵ Object درخواست‌شده و ۱۵ Object یافت‌شده؛
- هشت Object هسته و هفت منبع تطبیق؛
- ۲۶۹ ستون و ۶۵ FK رسمی؛
- ۴۷ FK از ۶۵ FK `not trusted` هستند؛
- ۲۱ Trigger فعال روی View/Tableهای منبع تطبیق/تنظیمات؛
- ۴۰٬۱۲۲ ردیف تجمیعی در Objectهای Table؛
- مقدار یا شناسه هیچ حساب، چک، حواله، ردیف بانک، فایل، توضیح یا کاربر ذخیره نشد.

هسته:

```text
Reconcile
├── BankBill
│   └── ReconcileItem
├── ReconcileDetail
└── BankBillFormat
    ├── BankBillFormatItem
    │   └── ReconciliationColumn
    └── BankBillFormatType
```

`ReconcileItem` هفت مرجع مشاهده‌شده دارد:

- `BankBillId`؛
- `PChequeId`؛
- `PWithdrawId`؛
- `RBankDraftId`؛
- `RCashDraftId` که به `Acc.TblBankOrders` می‌رسد؛
- `RChequeId` که به `Acc.TblCheque` می‌رسد؛
- `TransferId`.

تمام FKهای مستقیم `ReconcileItem` در Clone فعلی `not trusted` هستند. بنابراین
وجود FK برای اثبات کیفیت و یکتایی لینک کافی نیست و Import مقصد باید ردیف‌های
بدون Source، چندSource، تکراری یا مبهم را Quarantine کند.

## شاهد UI و DataAccess

چهار فرم مرتبط و شش قرارداد DataLayer به‌صورت Static تطبیق داده شدند:

- `frmReconciliationSetup`: انتخاب حساب/قالب، ساخت `Reconcile` و `BankBill`،
  Save، Delete، Cancel، Validation و Permission؛
- `frmReconciliation`: ساخت/حذف `ReconcileItem`، `Transaction.Start/Commit/RollBack`،
  ثبت Confirmer/ConfirmDate و `UpdateBankAccountCardex`؛
- `frmBankReconciliationList` و `frmBankReconciliation` با وجود نام مشابه، مسیر
  هستهٔ Reconcile اثبات‌شده نیستند: اولی loader خالی و coupling انتقال دارد و
  دومی preview فایل XLS است. Root آن‌ها تا telemetry/owner confirmation باز است؛
  سند اصلاحی: `BANK_RECONCILIATION_PROFILE_STATE_BOUNDARY_20260827_FA.md`.

وجود Signalهای بالا Branch واقعی، ترتیب دقیق SQL و اثر نهایی را ثابت نمی‌کند؛
هیچ Form، Procedure، Trigger یا Command اجرا نشده است.

Guardهای Method-level نیز مستقل ثبت شد: List علاوه بر مجوزهای Aliasشدهٔ
`TransferList`، بسته‌بودن تاریخ عملیات را می‌سنجد؛ Setup مجوزهای Edit/Delete و
سه ورودی حساب/تاریخ/فایل دارد؛ حذف Detail Transaction صریح دارد ولی Import/Save
در UI فاقد Signal Start/Commit/RollBack است. سند مرجع:
`BANK_RECONCILIATION_COMMAND_GUARDS_20260827_FA.md`.

مرز Parser فایل نیز نشان داد DBF/TXT/XLS با OleDb خوانده می‌شوند، Profile شامل
Format/HDR/Schema/SQL روی Dispatch اثر دارد و مسیر قدیمی Excel دارای Office
Automation/File side effect/Process.Kill است. این رفتار در وب کپی نمی‌شود؛ سند:
`BANK_STATEMENT_IMPORT_BOUNDARY_20260827_FA.md`.

Transaction تأیید نیز Nested است: UI، Reconcile.Update و Cardex update همگی
Start/Commit دارند و Legacy با شمارنده/Connection static آن‌ها را جمع می‌کند.
این الگو در Web مجاز نیست؛ سند:
`BANK_RECONCILIATION_TRANSACTION_BOUNDARY_20260827_FA.md`.

## محدودیت مهم Clone

هشت جدول هسته `Reconcile/BankBill/ReconcileItem/.../ReconciliationColumn` در Clone فعلی صفر ردیف
دارند. در نتیجه شکل چندنوعی از Schema و IL اثبات شده، اما Cardinality واقعی،
کیفیت Import، رفتار Match/Unmatch و توازن مبلغ از داده عملیاتی این Clone قابل
اثبات نیست. کوتاه یا بلندکردن پنجره سه‌ماهه این محدودیت را حل نمی‌کند.

## قرارداد مقصد

Aggregate مقصد `BankReconciliationSession` است و سه جزء مالک دارد:

1. `ImportedBankStatement` با هویت و Hash تغییرناپذیر فایل؛
2. `BankStatementRow` با شناسه پایدار Import؛
3. `TypedReconciliationLink` با Source type صریح.

Commandهای پیشنهادی:

- `bank_reconciliation.import_statement`؛
- `bank_reconciliation.match_instrument`؛
- `bank_reconciliation.unmatch_instrument`؛
- `bank_reconciliation.discard_imported_statement`؛
- `bank_reconciliation.confirm`؛
- `bank_reconciliation.cancel_session` (موقت تا تأیید مالک)؛
- `bank_reconciliation.reverse_confirmed_session`.

Write مستقیم Table از UI مجاز نیست. Import/Match باید Idempotent، حساب‌محور،
تاریخ‌محور، Auditشده و Transactional باشد و پیش از Confirm با کاردکس بانکی
Reconcile شود.

## شکاف‌های باقی‌مانده

- Entry point ریشه `frmBankReconciliationList` و `frmReconciliationSetup` پس از
  اسکن ۶۲ Assembly و ۸۵۳ فایل Deployment هنوز حل نشده است؛
- کاتالوگ/Assignment تجمیعی Permission روشن است، ولی مجوز مؤثر فرد احرازشده و
  Role-UAT انجام نشده است؛
- Shape Parser/Profile روشن است، اما سه جدول Profile در Clone صفر ردیف‌اند و
  مقدار واقعی/Parity قالب بانک در دسترس نیست؛
- Transaction/Cardex/Import persistence و Delete semantics روشن‌اند، ولی Target
  transaction owner و Runtime parity پیاده/اجرا نشده‌اند؛
- Cancel مستقل Legacy مشاهده نشده و تا sign-off مالک provisional است؛
- Result parity فقط روی Snapshot یا محیط مقصد ایزوله قابل اثبات است.

## بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_bank_reconciliation_source_model.py `
  --call-graph G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_priority_gap_call_graph_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_source_model_20260827.json

G:\NeginAI\.venv\Scripts\python.exe -m pytest `
  G:\NeginAI\tests\test_varanegar_ui_evidence.py -q `
  -k bank_reconciliation_source_model
```
