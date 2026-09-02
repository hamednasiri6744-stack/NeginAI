# مرز Atomicity اعمال و اعمال‌مجدد هزینهٔ فاکتور تأمین‌کننده

تاریخ شاهد: ۲۰۲۶-۰۸-۲۹  
دامنه: خرید، موجودی، حسابداری و مهاجرت  
وضعیت: **تأییدشده از Clone فقط‌خواندنی و IL هش‌سنجی‌شده؛ بدون اجرای Command**

## نتیجهٔ اصلی

در Snapshot فعلی ناسازگاری Status/Price دیده نشد، اما مسیر Legacy یک پنجرهٔ خرابی
ساختاری دارد. پنج Procedure اصلی Apply/ReApply تراکنش محلی صریح ندارند.
`usp_ApplySupInvoice` ابتدا قیمت‌های آیتم حواله را حذف و دوباره درج می‌کند؛
`usp_FastApplySupInvoice` همین بازسازی را انجام می‌دهد و سپس Status فاکتور را ۱
می‌کند. خطر مهم‌تر در `usp_ReApplySupInvoice` است: Status و ConfirmDate مجموعهٔ
فاکتورها پیش از حلقهٔ FastApply به حالت اعمال‌شده می‌روند. پس در صورت خطا، بدون
تراکنش بالادستِ قابل اتکا، «اعمال‌شده» می‌تواند پیش از تکمیل بازسازی هزینه منتشر
شود.

این شاهد وقوع خرابی تاریخی یا خرابی جاری را ثابت نمی‌کند؛ فقط شکل مسیر و پنجرهٔ
خطا را ثابت می‌کند.

## شاهد SQL و Snapshot جاری

- پنج Procedure اصلی و پنج Caller شناخته‌شده از Catalog با Hash تعریف و سیگنال
  تراکنش/ترتیب بررسی شدند؛ متن SQL ذخیره نشد.
- تعداد Procedure اصلی دارای `BEGIN TRANSACTION` محلی: صفر.
- ۳٬۲۸۵ فاکتور Status=1 همگی ConfirmDate دارند و ۲۹٬۰۷۸ آیتم مرتبط همگی رکورد
  `inv.tblVocherItmPrice` دارند؛ آیتم بدون قیمت صفر است.
- ۱۴۱ فاکتور Status=0 همگی ConfirmDate تهی دارند و ۱٬۳۵۴ آیتم مرتبط هیچ رکورد
  قیمت ندارند؛ آیتم قیمت‌دار در وضعیت صفر نیز صفر است.
- هیچ آیتمی میان جمعیت Status صفر و یک مشترک نیست.
- ConfirmDateها فقط در سه Bucket دیده شدند: ۲۰۲۵-۰۷ با ۱٬۱۷۵، ۲۰۲۶-۰۶ با ۳۷۰
  و ۲۰۲۶-۰۷ با ۱٬۷۴۰ فاکتور. تمرکز زمانی، به‌تنهایی نوع عملیات یا قصد ReApply را
  ثابت نمی‌کند.
- جدول قیمت ۱٬۴۱۹٬۶۵۶ رکورد با PK یکتا روی ID دارد. ۹۵ رکورد قیمت بدون آیتم
  حوالهٔ جاری دیده شد و FK مستقیمی از Price به VoucherItem وجود ندارد. علت این
  ۹۵ مورد به Apply فاکتور تأمین‌کننده نسبت داده نشده است.

## Caller و مالکیت تراکنش

Callerهای Catalog یکسان نیستند. `SLE.usp_CheckSupInvoice` مسیر Apply را بدون
تراکنش محلی صریح صدا می‌زند. برخی Callerهای دیگر، از جمله مسیر تأیید و مسیرهای
Save/Pricing، TRY/CATCH و تراکنش بالادست دارند. بنابراین نمی‌توان یک قرارداد
تراکنش واحد را از نام Procedure فرض کرد؛ هر Entry point باید جداگانه تست شود.

## شاهد Managed Runtime

دو Assembly مستقر `VN.SDS.Stock.Business.dll` و
`VN.SDS.Stock.DataAccess.dll` دقیقاً با Binary Inventory قبلی هم‌هش بودند. چهار
Method Allowlist‌شده با مجموع ۴۶۴ Instruction فقط از PE metadata/IL خوانده شدند؛
Assembly Load/Execute نشد.

- `CalcPriceHandler.StartReApplySupInvoice` به Adapter متناظر می‌رسد.
- Adapter با `DataContext.Query` به Literal حاوی نام Allowlist‌شدهٔ
  `ICA.usp_ReApplySupInvoice` می‌رسد؛ در دو Method منتخب ReApply سیگنال صریح
  BeginTransaction یا Commit وجود ندارد.
- `SupInvInvoiceRelationHandler.ApplySupInvoice` Adapter Apply را صدا می‌زند و
  در ترتیب خطی IL یک `DataContext.Commit` پس از آن دارد.
- Adapter Apply از `DataContext.Execute` استفاده می‌کند.

وجود Constructor مربوط به DataContext به‌عنوان اثبات شروع تراکنش تفسیر نشد؛
همچنین ترتیب خطی IL، Reachability شاخه و رفتار خطا را ثابت نمی‌کند.

## ریسک و قرارداد مقصد

`R-071` با شدت بحرانی ثبت شد. شدت، اثر بالقوه بر هزینهٔ موجودی/حسابداری است و
احتمال وقوع یا وجود Incident فعلی را جعل نمی‌کند. قرارداد مقصد باید شامل این
موارد باشد:

- `SupplierCostApplicationAttempt` غیرقابل‌تغییر با CommandId، PayloadHash و
  نسخهٔ فاکتور؛
- State machine صریح `Pending → Applying → Applied/Failed`؛
- یک مالک تراکنش برای Validation، بازسازی قیمت، Status، ConfirmDate، Audit و
  Outbox؛
- ممنوعیت ثبت `Applied` پیش از تکمیل قیمت همهٔ Componentها؛
- Cost layer نسخه‌دار یا Audit append-only به‌جای جایگزینی بی‌ردپا؛
- قفل هم‌زمانی در سطح Component و Retry قطعی با همان کلید؛
- FK یا Tombstone/Reconciliation صریح برای مالکیت VoucherItemPrice.

## Gate پذیرش

Fault injection باید قبل و بعد از Delete، Insert/Rebuild، Status، Audit و Outbox
اجرا شود و همیشه یا وضعیت کامل قبلی یا وضعیت کامل بعدی باقی بگذارد. دو ReApply
هم‌زمان باید یک Attempt پذیرفته‌شده داشته باشند. تمام ۳٬۲۸۵/۲۹٬۰۷۸ و
۱۴۱/۱٬۳۵۴ Snapshot فعلی باید پس از Import تکرارپذیر Reconcile شوند و برای ۹۵
Orphan بدون ساختن علت تاریخی، Disposition ثبت شود.

## Artifactهای بازتولیدپذیر

- `artifacts/varanegar_analysis/domains/supplier_cost_apply_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/supplier_cost_apply_runtime_boundary_20260829.json`
- `scripts/sql/extract_varanegar_supplier_cost_apply_boundary.py`
- `scripts/sql/extract_varanegar_supplier_cost_apply_runtime_boundary.py`
- `scripts/windows/build_varanegar_supplier_cost_apply_checkpoint_20260829.py`
- `tests/test_varanegar_supplier_cost_apply_boundary.py`

هیچ Stored Procedure، فرم، Endpoint یا Command عملیاتی اجرا نشد؛ هیچ شناسه،
مبلغ، قیمت، متن SQL، رمز یا Connection String در Artifactها ذخیره نشده است.
