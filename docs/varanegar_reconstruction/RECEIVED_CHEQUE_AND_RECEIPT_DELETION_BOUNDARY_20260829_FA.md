# مرز حذف چک دریافتی و رسید — ۲۰۲۶-۰۸-۲۹

## نتیجهٔ اصلی

حذف چک دریافتی در وارانگار یک Command یکنواخت نیست. سه قرارداد متمایز در شواهد
مستقر دیده می‌شود:

1. `Acc.uspCHQDelete` اعتبارسنجی می‌کند و History را پیش از Master در Transaction
   محلی حذف می‌کند؛
2. `dbo.usp_sdsnet_Receipt_Save` Transaction/Savepoint دارد و در شاخهٔ حذف کامل،
   History چک، Master چک و سپس Receipt را پاک می‌کند؛
3. Trigger نوع `INSTEAD OF` روی View یعنی `dbo.Trg_RCheque_TblCheque` مستقیماً
   Master را حذف می‌کند و در متن خودش حذف History یا Receipt ندارد.

چهار Candidate مستقیم دیگر نیز وجود دارند و Transaction/Cleanup یکسانی ندارند.
پس در ERP مقصد، `DeleteReceivedCheque` و `DeleteReceipt` باید دو Command و دو
Tombstone مستقل باشند؛ مجاورت رخدادهای Log برای ساختن علت، کاربر یا Procedure
قطعی کافی نیست.

## شواهد ایستای SQL

ده ماژول منتخب Fingerprint شدند؛ هفت ماژول حذف مستقیم `Acc.TblCheque` دارند:

| مسیر | Transaction محلی | حذف History | حذف Receipt | نکته |
|---|---:|---:|---:|---|
| `Acc.uspCHQDelete` | بله | بله | خیر | Validator → History → Master → Commit/Rollback |
| `dbo.DeleteDataFromAccyear` | بله | بله | خیر | پاک‌سازی سال مالی |
| `dbo.DoPOrder_ReSendPayment` | خیر | بله | بله | Cleanup پرداخت/رسید |
| `dbo.NGT_RollBackTour` | خیر | خیر | خیر | مسیر جبران NGT؛ مالک Transaction بیرونی محتمل است |
| `dbo.Trg_RCheque_TblCheque` | خیر | خیر | خیر | پل حذف View به Master |
| `dbo.usp_RollbackTourToReceivedStatue` | خیر | بله | خیر | مسیر Rollback دریافت |
| `dbo.usp_sdsnet_Receipt_Save` | بله | بله | بله | Transaction/Savepoint و شاخهٔ حذف کامل رسید |

وجود این مسیرها قابلیت Mutation را ثابت می‌کند، نه اینکه هرکدام در بازهٔ Log
اجرا شده باشند. `Acc.UspChequeOperation` برای Operation type حذف به
`Acc.uspCHQDelete` وصل است و `BeforeRCheque` نیز در بعضی شاخه‌ها Cleanup History
دارد.

## تطبیق Log حذف Master

در Log باقی‌مانده:

- ۳۱ `Acc.TblCheque DELETE` وجود دارد؛ ۱۱ مورد در June–August 2026 است؛
- هر ۳۱ شناسهٔ Log‌شده اکنون در Master غایب‌اند؛
- `insert-only absent` و `deleted-but-present` برای این جمعیت هر دو صفر است؛
- همهٔ ۳۱ حذف، در پنجرهٔ ناشناس همان Session حداقل یک History DELETE پیش از خود
  دارند؛ ۲۷ مورد دقیقاً بلافاصله پس از History DELETE هستند و چهار مورد در Batch
  چندچکی، پس از Master DELETE قبلی آمده‌اند.

طبقه‌بندی tail:

| شکل | Master حذف‌شده | توضیح محدود |
|---|---:|---|
| Receipt DELETE tail | ۲۳ | در ۱۹ Batch با دقیقاً ۲۳ History DELETE |
| Receipt UPDATE tail | ۷ | Receipt باقی مانده و Update شده است |
| Isolated tail | ۱ | در پنجرهٔ انتخابی رخداد بعدی ثبت نشده است |

از ۲٬۳۵۱ حذف Receipt باقی‌مانده، فقط ۱۹ Batch شامل پاک‌سازی Master چک‌اند.
در سه ماه اخیر ۲۳۸ Receipt حذف شده و پنج Batch آن‌ها شامل پنج Master/پنج History
بوده است. شکل ۱۹ Batch با شاخهٔ حذف کامل `usp_sdsnet_Receipt_Save` سازگار است،
ولی چون `GNR.tblLog` Call stack ندارد، این تطبیق Attribution قطعی Procedure نیست.

## مرز Runtime فرم‌ها

IL هش‌سنجی‌شدهٔ `TreasuryOld.Forms.dll` بدون Load/Execute خوانده شد:

- `frmRChequeTracking.DeleteRCheque` در ۲۸ Instruction ابتدا Confirmation، سپس
  `DataRow.Delete` و بعد `RCheque.Update` دارد؛ در همین Method سیگنال Transaction
  صریح دیده نشد؛
- `frmRChequeTrackingNew.DeleteRCheque` در شش Instruction فقط Confirmation
  قابل‌مشاهده دارد و DataRow delete/update در Method منتخب دیده نشد.

هر دو فرم در Binary موجودند، اما انتخاب Runtime آن‌ها ثابت نشده است. همچنین
اتصال دقیق `RCheque.Update` به شاخهٔ DELETE Trigger با Static IL حاضر مستقلاً
اثبات نشده؛ فقط View/Trigger و Callهای سازگار در دو شاهد مستقل دیده می‌شوند.

## وابستگی و Audit

History، Payment، Supplier settlement، Cession/Refund، Transfer و Reconcile چند
FK از نوع `NO_ACTION` به Master چک دارند. حذف Master همچنین `tblRChequeLog` را با
FK از نوع `CASCADE` پاک می‌کند. Receipt نیز ترکیبی از `NO_ACTION` و `CASCADE`
دارد. بنابراین ترتیب Cleanup فقط جزئیات پیاده‌سازی نیست؛ بخشی از قرارداد صحت و
Audit است.

هر پنج جدول منتخب `TblCheque`، `tblChqHist`، `Receipt`، `RCash` و `RCashDetail`
Non-temporal و بدون CDC/Change Tracking هستند. Log عمومی Tombstone حداقلی می‌دهد،
اما Payload کامل Domain event یا Reason/Actor قابل اتکا نمی‌سازد.

## قرارداد مقصد

- `DeleteReceivedCheque` و `DeleteReceipt` Commandهای مستقل، نسخه‌دار و idempotent؛
- Tombstone append-only پیش از حذف Projection با Source evidence و بدون جعل علت؛
- یک Transaction owner صریح برای History/Master/Receipt/Cash/Accounting/Outbox؛
- کنترل پیش از Mutation برای FKهای `NO_ACTION` و Export audit پیش از Cascade؛
- حفظ سه Evidence state مستقل در مهاجرت: Receipt-delete batch، Receipt-update tail
  و Isolated tail؛
- Route parity برای Legacy dataset، View trigger، Direct procedure و SDSNET.

## ریسک ثبت‌شده

`R-075` با شدت High ثبت شد. رجیستر اکنون ۷۵ ریسک شامل ۴۱ Critical، ۳۱ High و
سه Medium دارد؛ Traceability شامل ۲۹۵ اتصال ریسک و صفر ماژول Command-ready است.

## محدودیت و ایمنی

- تحلیل Clone فقط‌خواندنی و Aggregate ناشناس است؛
- هیچ Procedure، Trigger، Form یا Command اجرا نشد؛
- Assemblyها Load/Execute نشدند و فقط PE metadata/IL خوانده شد؛
- هیچ ID، OperationScript، مشتری، بانک، مبلغ، توضیح یا کاربر ذخیره نشد؛
- پنجرهٔ مجاورت ۳۰ ثانیه/ID-bounded برای Shape است و Call stack نیست.

## خروجی‌های بازتولیدپذیر

- `scripts/sql/extract_varanegar_received_cheque_delete_boundary.py`
- `scripts/sql/extract_varanegar_received_cheque_delete_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/received_cheque_delete_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/received_cheque_delete_runtime_boundary_20260829.json`
