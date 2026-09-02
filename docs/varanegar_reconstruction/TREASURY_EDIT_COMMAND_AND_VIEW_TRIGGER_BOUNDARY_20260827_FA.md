# مرز فرمان و View/Trigger در ویرایش ابزارهای دریافت

## نتیجه معماری

سه فرم Legacy ویرایش نقد، چک دریافتی و حواله/دستور بانکی، CRUD ساده نیستند.
هر سه در Handler دکمه تأیید، Transaction را از خود UI مدیریت می‌کنند و
`ExecuteNonQuery` مستقیم دارند. افزون بر آن، چک و حواله روی Viewهای قابل‌نوشتن
قرار گرفته‌اند که با Triggerهای `INSTEAD OF INSERT/UPDATE/DELETE` به جداول
حسابداری پل می‌زنند.

در ERP شخصی نگین این رفتار باید به Command handler دامنه منتقل شود؛ UI فقط
Command را ارسال می‌کند و نباید Transaction، SQL یا DataAdapter را مالک باشد.

## مسیرهای استاتیک سه فرم

| فرم | Method فرمان | مسیر Persist |
|---|---|---|
| `frmCashEdit` | `BtnOk_Click` | `RCash.Update` + SQL مستقیم برای `RCashDetail/Receipt` + Start/Commit/RollBack |
| `frmChequeEdit` | `btnOk_Click` | ۱۲ setter روی `RCheque` + `RChequeAdapter.PreUpdate` + SQL مستقیم Log/Accounting + Transaction |
| `frmRCashDraftEdit` | `btnOk_Click` | ۹ setter روی `RCashDraft` + `RCashDraftAdapter.PreUpdate` + SQL مستقیم Accounting + Transaction |

در مجموع ۷۳ Method body بررسی شد؛ سه Method فرمان Mutation، یک Method اعتبارسنجی
با Transaction، ۲۴ setter یکتا، ۲۹ Field یکتا و ۳۸ قطعه SQL/Business allowlist
شده ثبت شد. هیچ فرمان Legacy اجرا نشد و موفقیت Runtime/Idempotency/Parity صفر است.

## مدل منبع Clone

هشت Object دقیق مسیر فقط از کاتالوگ Clone خوانده شد:

| Object | نوع | ردیف تقریبی Clone | Trigger فعال |
|---|---:|---:|---:|
| `dbo.RCash` | Table | ۱۱٬۰۹۶ | ۱ |
| `dbo.RCashDetail` | Table | ۱۱٬۲۵۶ | ۴ |
| `dbo.Receipt` | Table | ۶۸٬۶۲۶ | ۸ |
| `dbo.RCheque` | **View** | نامربوط برای View | ۱ `INSTEAD OF` سه‌رویدادی |
| `dbo.tblRChequeLog` | Table | ۲٬۵۴۵ | ۰ |
| `Acc.TblCheque` | Table | ۲۳٬۸۲۲ | ۹ |
| `dbo.RCashDraft` | **View** | نامربوط برای View | ۱ `INSTEAD OF` سه‌رویدادی |
| `Acc.TblBankOrders` | Table | ۱۴۶٬۵۷۶ | ۵ |

دو Trigger پل عبارت‌اند از `Trg_RCheque_TblCheque` و
`Trg_RCashDraft_tblBankOrders`. کل سطح شامل ۲۳۵ ستون، ۷۵ مشاهده FK، ۲۹ Trigger
فعال و ۸۰۴ مشاهده ماژول ارجاع‌دهنده است. شمارش پارتیشن برای View صفر به معنی
خالی بودن داده نیست.

## Semantic footprint Triggerها

Definition هر ۲۹ Trigger فقط در حافظه خوانده، Comment/String ماسک و سپس حذف شد.
۱۳۳ Dependency و ۲۰ Mutation token ساختاری به دست آمد: پنج `INSERT`، سیزده
`UPDATE` و دو `DELETE`. دو Trigger `INSTEAD OF` هر سه عملیات را دقیقاً به
`Acc.TblCheque` و `Acc.TblBankOrders` می‌برند؛ Dependencyهای مشترک مهم آن‌ها
`Receipt`، `RPReason`، `Customer`، `vwDC`، `tblAccYear`، تبدیل تاریخ خورشیدی و
تشخیص Replication mode است. Trigger چک افزون بر این به `gnr.uspGetNextId`
وابسته است.

هیچ‌یک از دو Bridge، Transaction envelope یا Error handler مستقل در متن خود
ندارد؛ اتمیک‌بودن آن‌ها در Transaction دستور فراخوان و رفتار SQL Server است.
این شاهد، نتیجه موفق یا Effect parity همه Branchها را اثبات نمی‌کند.

## Lineage ستون View

Metadata descriptor یک `SELECT *` را بدون اجرای Query توصیف کرد و برای هر ۹۷
ستون قابل‌نمایش، ۱۵ ستون Browse مخفی هم برگرداند. از ۹۷ ستون، ۸۹ ستون Source
lineage مستقیم دارند. نمونه‌های مهم:

- `RChequeId → Acc.TblCheque.ID`، `BankId → BankRef`،
  `RChequeDate → ChqDate`، `RChequeAmount → ChqAmount`،
  `CustomerId → CustRef` و `SayadNo → SayadNo`؛
- `RCashDraftId → Acc.TblBankOrders.ID`، `BankId → SenderBankRef`،
  `BankAccountId → DepBranchRef`، `RCashDraftDate → OrderDate`،
  `RCashDraftAmount → Amount` و `CustomerId → CustRef`؛
- ستون‌های تاریخچه چک از `Acc.tblChqHist` و عنوان‌های دفتر تفصیلی از
  `TRSL/SL/DL/FifthLedger/SixthLedger/SeventhLedger` می‌آیند.

هشت ستون visible Source مستقیم توصیف‌شده ندارند: در چک
`ChequeTypeId, RChequeNo, AccountNo, RChequeComment, IsReconciled, ModifiedDate`
و در حواله `RCashDraftNo, RCashDraftBranchName`. این‌ها حذف‌شده نیستند؛ Alias،
Expression یا محدودیت Metadata هستند. Parse درون‌حافظه‌ای Definition برای هر
هشت مورد Identifier candidate ساخت: از جمله `RChequeNo → Acc.TblCheque.ChqNo`،
`AccountNo → Acc.TblCheque.AccNo`، `RCashDraftNo → Acc.TblBankOrders.OrderNo`
و `RCashDraftBranchName → SenderBankBranch`. Definition یا Literal ذخیره نشد؛
این هشت رابطه تا Golden snapshot/Trigger parity همچنان Candidate می‌مانند.

## پیامد برای مقصد

1. `RCheque` و `RCashDraft` نباید به عنوان Aggregate table مستقل مهاجرت شوند؛
   مالکیت واقعی، تاریخچه، دفترکل و Crosswalk باید از جدول و Trigger زیرین اثبات شود.
2. Command مقصد باید تغییر ابزار دریافت، Log، مبلغ رسید و اثر حسابداری را با
   مرز اتمیک/Outbox صریح پوشش دهد.
3. Preview/Edit validation باید از Mutation جدا شود؛ Transaction داخل Validation
   Legacy نیازمند ردیابی مرحله‌به‌مرحله و Fault injection است.
4. Triggerهای تکرار/ChangeLog/Guard باید به invariant، event/outbox و audit صریح
   تبدیل شوند، نه اینکه خام کپی یا حذف شوند.

## قرارداد مقصد و Gate پذیرش

سه Command مقصد تعریف شد: ویرایش ابزار نقدی رسید، چک دریافتی و حواله بانکی.
هر سه `command_id + payload fingerprint`، `expected_version`، Context سازمانی،
Transaction owner واحد، Audit/Outbox و Reconciliation دارند و Write-back به
وارانگار/Clone را منع می‌کنند.

برای هر Command هفده Acceptance obligation، جمعاً ۵۱ مورد، ثبت شد: Allow/Deny،
Scope، Required/Amount/Date/Status، Concurrency، دو نوع Replay، سه Fault boundary،
دو Reconciliation، View/Trigger parity و No-write-back. این‌ها عمداً Golden case
اجراشده نامیده نشده‌اند: Owner-approved، Implemented و Executed هر سه صفر است.

## قواعد Validation کشف‌شده

هفت Method منتخب با ۲٬۴۶۱ Instruction و ۲۹ Field، چهارده Rule signal متمایز
دارند:

- نقد: وضعیت و جمع همه ابزارهای رسید، مبلغ تسویه، نوع/مانده صندوق و مرز Transaction؛
- چک: وضعیت/آخرین تاریخچه چک، تاریخ عملیات، تاریخ خورشیدی، تنظیم الزام مشتری،
  جمع ابزارهای رسید و مبلغ تسویه؛
- حواله بانکی: صحت تاریخ خورشیدی، ممنوعیت شماره تکراری وابسته به Setting،
  محدودیت تاریخ آینده، وضعیت/جمع رسید، مبلغ تسویه، مانده حساب بانکی و محاسبه
  `VosulDate` از فاصله تنظیم‌شده.

چهار Method Transaction signal و سه Method SQL Mutation مستقیم دارند. این‌ها
Method-level signal هستند؛ شرط دقیق هر Branch، پیام خطا و مقدار Effective Setting
هنوز Owner/Golden proof می‌خواهد.

## گراف Transitive Trigger

گراف سه‌لایه از هر ۲۹ Trigger ریشه، بدون رسیدن به سقف ۵۰۰ Node، به ۳۷۶ Node و
۷۵۵ Edge رسید: ۲۷۰ Trigger، ۸۱ Table، پنج Procedure، ده Scalar function، یک
TVF و نه View. Definitionها فقط در حافظه ماسک و حذف شدند.

در این سطح ۲۳۵ Mutation token، ۴۲ Write target حل‌شده، ۹۹ Module دارای
Transaction signal، ده Try/Catch و هفت Dynamic-SQL signal دیده شد. ۱۶۰ Dependency
حل‌نشده صریح باقی ماند. دو Bridge اصلی Blast radius استاتیک بزرگی دارند:

- `Trg_RCheque_TblCheque`: ۱۲۱ Node قابل‌دسترسی، ۸۰ Trigger و ۱۰ Write target؛
- `Trg_RCashDraft_tblBankOrders`: ۹۳ Node، ۵۷ Trigger و ۱۱ Write target.

این اعداد «اثر حتمی هر ویرایش» نیستند؛ گراف Dependency/Trigger و همه Branchهای
ممکن‌اند. اما ثابت می‌کنند حذف یا کپی خام Triggerها بدون Inventory، Fault test
و Reconciliation مالی خطرناک است.

## واژه‌نامه فیلد آماده برای Web reconstruction

شواهد Control type، Field→Property، Property→Column، View lineage و Rule method
برای هر ۶۸ Field اعلام‌شده سه فرم ادغام شد:

- ۱۶ Field نامزد Property+ستون زیرین نسبتاً قوی دارند؛
- یک Field (`txtRCashDraftNo`) عمداً Conflict دارد: هم
  `Acc.TblBankOrders.OrderNo` و هم Setting
  `TRServerConfig.NotInsertDuplicateRCashDraftNo` در همان Method دیده می‌شوند؛
- دو Field فقط Property candidate و هفت Field فقط Validation/Command usage دارند؛
- ۴۲ مورد Label/Container/Button یا Control بدون Field contract هستند؛
- ۲۴ Field در Methodهای Validation/Command حاضرند و ۱۸ ستون زیرین یکتا ثبت شد.

این Artifact برای ساخت DTO/Form schema وب مناسب است، ولی Requiredness، Effective
rule و Runtime binding همه صفرند و باید در UAT مالک بسته شوند.

## عنوان‌ها و Screen contract نامزد وب

از `InitializeComponent` سه فرم، فقط انتساب‌های Inline و Allowlist‌شده‌ی
`Text/Caption/HeaderText/Title` استخراج شد. اسمبلی Load/Execute نشد. ۴۰ انتساب
استاتیک پیدا شد: ۳۷ مورد به Control اعلام‌شده وصل شدند و سه مورد عنوان فرم‌اند؛
هیچ Control مبهمی با بیش از یک متن دیده نشد. عنوان‌های منبع عبارت‌اند از:

- `frmCashEdit`: «فرم ویرایش مبلغ نقد»؛
- `frmChequeEdit`: «فرم اصلاح مشخصات چک»؛
- `frmRCashDraftEdit`: «فرم اصلاح مشخصات واریز».

ترکیب برچسب‌ها، ۶۸ Control، چهارده Rule signal، سه Command مقصد و ۵۱ Acceptance
obligation، سه Screen contract نامزد وب ساخته است. در آن‌ها ۲۷ Input، شش Command
control و ۳۱ Label جدا ثبت شده‌اند. فقط دو Input Caption مستقیم دارند؛ Pair کردن
۳۱ Label جدا با Inputها عمداً انجام نشده، چون ترتیب نام Control بدون Layout/Owner
proof کافی نیست. هر سه Screen هنوز `NOT_IMPLEMENTATION_READY`، Owner-approved صفر
و Runtime-Golden صفر هستند.

## مرز شواهد

- فقط IL Hash‌شده/Redacted و متادیتای کاتالوگ Clone فقط‌خواندنی استفاده شد.
- Definition هیچ View/Trigger/Procedure و مقدار هیچ ردیف تجاری خوانده یا ذخیره نشد.
- Branch order، نتیجه موفق، Rollback واقعی و برابری خروجی اثبات نشده است.

Artifactها:

- `artifacts/varanegar_analysis/ui/varanegar_treasury_edit_command_paths_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_treasury_edit_source_model_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_treasury_trigger_semantics_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_treasury_view_column_lineage_20260827.json`
- `artifacts/varanegar_analysis/ui/negin_erp_treasury_edit_target_contracts_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_treasury_edit_validation_contracts_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_treasury_trigger_transitive_graph_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_treasury_web_field_contract_candidates_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_treasury_ui_label_candidates_20260827.json`
- `artifacts/varanegar_analysis/ui/negin_erp_treasury_web_screen_contract_candidates_20260827.json`
