# مرز Unapply، حذف فاکتور خرید و برگشت هزینه

تاریخ شاهد: ۲۰۲۶-۰۸-۲۹  
وضعیت: **تأییدشده از Clone فقط‌خواندنی و IL هش‌سنجی‌شده؛ بدون اجرای Command**

## نتیجهٔ اصلی

Reverse فاکتور خرید در وارانگار یک قرارداد واحد ندارد. مسیر Unlink، کل Header را
`Status=0` و `ConfirmDate=NULL` می‌کند و بعد `Price/UnitPrice` آیتم‌های Voucher
انتخاب‌شده را صفر می‌کند؛ مسیرهای دیگر Relation، Item/Toll یا Header را حذف
می‌کنند. از هشت ماژول منتخب فقط سه مورد تراکنش محلی صریح دارند.

Snapshot فعلی کاملاً سازگار است و این یافته وقوع خرابی جاری را ثابت نمی‌کند،
اما ترکیب «State در سطح Invoice» با «برگشت قیمت در سطح Voucher» برای رابطهٔ N:M
یک مرز بحرانی طراحی است.

## قرارداد SQL Unlink

`ICA.uspLinkUnlinkSupInvoiceInv`:

- تراکنش محلی، TRY/CATCH و XACT_ABORT ندارد؛
- تاریخ قطعی قیمت‌گذاری خرید و آخرین تاریخ قطعی خرید را کنترل می‌کند؛
- در مسیر Unlink ابتدا Status کل فاکتور را صفر و ConfirmDate را تهی می‌کند؛
- سپس Price و UnitPrice آیتم‌های Voucher انتخاب‌شده را صفر می‌کند؛
- Branch وابسته به ApplicationName برای Rollback دارد؛
- خودش Relation را حذف نمی‌کند؛ حذف Relation در Orchestrator/Caller انجام می‌شود.

`UspSupInvoiceHdrOperation → UspSupInvoiceHdrDelete →
UspSupInvoiceHdrDeleteItemsAndTolls` نیز در ماژول‌های منتخب تراکنش محلی صریح
ندارد. در مقابل `usp_sdsnet_SupInvoice_Save`،
`RemoveVocherForSupinvoice` و `UspDeleteTransferedVchrs` تراکنش محلی دارند، اما
Semantics آن‌ها یکسان نیست؛ یکی Relation/Header/Item/Toll و Price را دستکاری
می‌کند، دیگری Relation و State را، و یکی حتی Trigger رابطه را موقتاً Disable
می‌کند.

## مسیر Managed/Desktop

سه Assembly مستقر با Binary Inventory قبلی هم‌هش بودند. چهار Method و ۳۶۹
Instruction فقط از PE metadata/IL خوانده شدند.

- DeleteCommand در List، `LastClosedDate_Buy` را می‌خواند و SaveCommand عمومی را
  پیش از Commit صدا می‌زند؛ سیگنال تشخیص Settlement نیز دارد.
- DeleteCommand در DataEntry نیز SaveCommand عمومی را پیش از Commit دارد.
- Business `Unlink` ابتدا SaveCommand رابطه، سپس Operation code=3 روی Adapter و
  بعد Commit را در ترتیب خطی IL دارد.
- Adapter دو `DataContext.Execute` و صفر Commit دارد.

این شاهد نشان می‌دهد مسیر Managed تلاش می‌کند Relation و Unlink را زیر یک
DataContext نگه دارد، اما جدول دقیق SaveCommand، Reachability شاخه‌ها و اشتراک
تراکنش فیزیکی همهٔ SQLهای تو‌در‌تو اثبات نشده است.

## جمعیت و N:M جاری

- ۱۴۱ فاکتور Unapplied: همه ConfirmDate تهی، همه دارای Relation، ۱۷ فاکتور
  چندرسیدی و بیشینه سه Relation.
- ۳٬۲۸۵ فاکتور Applied: همه ConfirmDate حاضر، همه دارای Relation، ۱۹۲ فاکتور
  چندرسیدی و بیشینه هفت Relation.
- ۲۹٬۰۷۸ آیتم مرتبط Applied همگی Price دارند و Zero-price صفر است.
- ۱٬۳۵۴ آیتم مرتبط Unapplied هیچ Price row ندارند.
- در کل جدول Price، ۸۳ ردیف Price/UnitPrice صفر وجود دارد؛ از این شاهد به Unlink
  نسبت داده نشدند.

## Lifecycle واقعی Relation

Triggerهای Replication رابطه ۳٬۹۰۲ Insert و ۲۱۳ Delete نگه داشته‌اند؛ ۱۵ Delete
در June–August 2026 رخ داده است. ۳٬۸۹۲ ID لاگ‌شده شامل ۳٬۶۸۹ Relation جاری و
۲۰۳ Relation غایب است. آخرین Event برای هر ۲۰۳ غایب DELETE و برای هر ۳٬۶۸۹
جاری INSERT است. چهار ID پس از Delete دوباره حاضر شده‌اند؛ هشت ID چند Insert و
شش ID چند Delete دارند.

این Log فعال‌بودن Lifecycle و امکان Relink را ثابت می‌کند، نه دلیل کسب‌وکاری،
هویت عامل یا تغییر متناظر Status/Price را. Header و Price هیچ Trigger Audit
ندارند و هر سه جدول Header/Relation/Price Non-temporal و بدون CDC/Change
Tracking هستند.

## Dependency حذف

- دو Settlement موجود هر دو به Invoice Applied وصل‌اند.
- ۲۷ Return Header به ۱۲ Invoice منبع وصل‌اند: یک Return/Invoice در Status صفر
  و ۲۶ Return روی ۱۱ Invoice در Status یک.
- FKهای مشاهده‌شده فعال ولی untrusted و `NO_ACTION` هستند؛ Relation و Return
  قرارداد FK کامل به Header ندارند.

وجود این داده‌ها به‌تنهایی حذف نادرست را ثابت نمی‌کند، اما مقصد باید Settlement،
Return، دورهٔ بسته و Cost مصرف‌شده را در تمام مسیرهای Desktop/SDSNET یکسان Guard
کند.

## قرارداد مقصد و Gate

`R-072` با شدت بالا ثبت شد. مقصد به `SupplierCostReversalAttempt` append-only،
نسخهٔ Cost قبل/بعد، State machine صریح، یک Transaction owner، Audit/Outbox و
Tombstone نیاز دارد. Reverse باید در Grain کل Connected Component رابطهٔ N:M
تعریف شود؛ نباید Header را Unapplied نشان دهد درحالی‌که فقط بخشی از Receiptها
Reverse شده‌اند.

Fault injection باید قبل و بعد از Relation removal، Status، هر Cost reversal،
Audit و Outbox اجرا شود. هر ۱۷ Unapplied و ۱۹۲ Applied چندرسیدی Golden case
مستقل می‌خواهند. ۲۱۳ Delete تاریخی باید بدون جعل علت Disposition شوند و ۸۳
Zero-price فقط پس از تحلیل Provenance طبقه‌بندی شوند.

## خروجی‌های بازتولیدپذیر

- `artifacts/varanegar_analysis/domains/supplier_unapply_delete_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/supplier_unapply_delete_runtime_boundary_20260829.json`
- `scripts/sql/extract_varanegar_supplier_unapply_delete_boundary.py`
- `scripts/sql/extract_varanegar_supplier_unapply_delete_runtime_boundary.py`
- `scripts/windows/build_varanegar_supplier_unapply_delete_checkpoint_20260829.py`
- `tests/test_varanegar_supplier_unapply_delete_boundary.py`

هیچ Procedure، Trigger، Form یا Command اجرا نشد؛ هیچ شناسه، قیمت، مبلغ، متن SQL،
Log script، Credential یا هویت عامل ذخیره نشده است.
