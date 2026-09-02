# مرز خروجی Summary تا نمایش UI مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ نگاشت و Presentation اثبات شد؛ فرمول ایستا در Artifact مکمل اثبات و Row parity همچنان باز است**

## کشف اصلی

متد `frmReconciliation.RefreshSummary` سه Scope ورودی
`ReconcileId / VocherDate / BankAccountId` و یازده خروجی `money` را به‌ترتیب با
Reference از `ReconcileAdapter.GetSummary` می‌گیرد. هر خروجی دقیقاً به یک Label
وصل است:

| خروجی | Label مقصد |
|---|---|
| RemainingLastReconcile | lblRemainingLastReconcileValue |
| RemainingThisPeriod | lblRemainingThisPeriodValue |
| RemainingBill | lblRemainingBillValue |
| RemainingCardex | lblRemainingCardexValue |
| BillDebitOpenItems | lblBillDebitOpenItemsValue |
| BillCreditOpenItems | lblBillCreditOpenItemsValue |
| CardexDebitOpenItems | lblCardexlDebitOpenItemsValue |
| CardexCreditOpenItems | lblCardexlCreditOpenItemsValue |
| RealRemainingBill | lblRealRemainingBillValue |
| RealRemainingCardex | lblRealRemainingCardexValue |
| Reconcile | lblReconcileValue |

## Presentation دقیق

- برای هر یازده خروجی مقایسه با `Decimal.Zero` انجام می‌شود؛
- مقدار منفی در Local copy در `Decimal.MinusOne` ضرب و به‌صورت قدرمطلق داخل
  پرانتز و قرمز نمایش داده می‌شود؛
- صفر و مقدار مثبت DarkBlue نمایش داده می‌شوند؛
- این تبدیل فقط Presentation است و هیچ Entity یا جدول را Update نمی‌کند؛
- رنگ State، Permission یا معنای حسابداری قطعی نیست.

IL شامل ۳۹۴ Instruction، یازده Compare، یازده Multiply، ۲۲ Text assignment و
۲۲ ForeColor assignment است. Hash اسمبلی با Inventory معتبر برابر بود. هیچ
String literal، دادهٔ تجاری، اتصال دیتابیس یا اجرای فرم/Procedure در Artifact
ثبت یا انجام نشد.

## قرارداد مقصد

- API باید مقدارهای Decimal علامت‌دار و Key پایدار برگرداند؛ ترتیب پارامتر Wire
  identity نیست.
- Formatting باید از Query/formula جدا باشد و Sign ماشین‌خوان حفظ شود.
- UI نباید فقط به رنگ تکیه کند؛ Sign/متن دسترس‌پذیر لازم است.
- Transaction ایستای Adapter نباید وارد UI مقصد شود.
- Formulaهای ایستا بعداً در
  `BANK_RECONCILIATION_SUMMARY_SQL_SEMANTICS_20260827_FA.md` اثبات شدند؛ تا
  Row-result parity، این نگاشت همچنان مجوز اجرای Command یا Pilot نیست.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_summary_ui_boundary_20260827.json`
- `scripts/windows/extract_varanegar_bank_reconciliation_summary_ui_boundary.py`
- `tests/test_varanegar_ui_evidence.py`

در این Extractor تعریف Stored Procedure و Business rowها عمداً خوانده نشدند؛
فرمول‌ها در Extractor مکمل و فقط از Definition به‌صورت Redacted بازیابی شدند.
