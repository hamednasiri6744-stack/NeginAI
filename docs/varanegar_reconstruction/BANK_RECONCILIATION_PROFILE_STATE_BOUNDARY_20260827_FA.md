# مرز Profile و State مغایرت بانکی وارانگار

## نتیجه

Profile واقعی مسیر Import و State واقعی Session با IL ایستا، Artifact مدل منبع
Clone و کاتالوگ فقط‌خواندنی SQL جدا شد. Profile از View توسعه‌یافتهٔ
`dbo.BankAccount2` وارد فرم Setup می‌شود و State صریحی در جدول `Reconcile`
وجود ندارد؛ تأیید فقط با جفت `ConfirmerId/ConfirmDate` علامت‌گذاری می‌شود.

هیچ فرم، Assembly، Parser، Procedure یا Command اجرا نشده، هیچ ردیف تجاری
خوانده نشده و متن SQL/Profile value/File content نگهداری نشده است.

## Profile انتخاب‌شده برای حساب

`frmReconciliationSetup.cmbBankAccountName_ValueChanged` با
`BankAccountAdapter.GetBankAccountWhere` حساب را می‌خواند و چهار مقدار زیر را
به state فرم منتقل می‌کند:

- `FormatExtension`
- `HDR`
- `SQLStatement`
- `SchemaFile`

SQL inline این Adapter فقط با Hash و طول ۷۳۲ ثبت شده و متن آن ذخیره نشده است.
شناسهٔ allowlist‌شدهٔ Source آن `BankAccount2` است. View جاری Clone دارای ۴۶
ستون است و هفت dependency دارد: Bank، BankAccount، BankAccountType،
BankBillFormat، BankBillFormatType، GetBankAccountBalance و
PChequePrintFormat. هفت ستون Profile در View شامل FormatFileName،
BankBillFormatId، BankBillFormatTypeId، FormatExtension، SQLStatement،
SchemaFile و HDR هستند.

Dispatch فرم روی سه کلید دقیق `dbf`، `txt` و `xls` انجام می‌شود. Tableهای
BankBillFormat، BankBillFormatItem، BankBillFormatType و ReconciliationColumn
در Snapshot فعلی جمعاً صفر ردیف دارند؛ بنابراین Shape قطعی است ولی هیچ Profile
واقعی بانک یا Result parity موجود نیست.

سه ستون `StartRow`، `Seperator` و `IsArabic` در جدول BankBillFormat وجود دارند،
اما getter آن‌ها در مسیر فرم Setup مشاهده نشد. همچنین جدول‌های Profile هیچ
ستون Version/EffectiveDate/Active/Approval ندارند. مقصد نباید این نبودن را کپی
کند.

## State ذخیره‌شده

`dbo.Reconcile` ستون Status/State ندارد. ستون‌های مرتبط عبارت‌اند از:

- `ConfirmerId int NULL`
- `ConfirmDate datetime NULL`
- `Amount money NULL`

فرمان UI با Key دقیق `Ok` پس از سؤال تأیید، `DoAccept` را صدا می‌زند. این متد
در Transaction، ConfirmerId و ConfirmDate را می‌نویسد، Reconcile را Update و
سپس BankAccountCardex را Update می‌کند. نکتهٔ مهم: قبل از `set_Amount` مقدار
`System.Decimal.Zero` بارگذاری می‌شود؛ پس `Reconcile.Amount` در Confirm این
نسخه، نتیجهٔ محاسبهٔ Summary نیست و نباید به‌عنوان مقدار تراز قطعی مهاجرت شود.

Normalization پیشنهادی مقصد:

- `IMPORTED_UNCONFIRMED`: هر دو marker تهی؛
- `CONFIRMED`: هر دو marker غیرتهی؛
- `INCONSISTENT_LEGACY_MARKERS_QUARANTINED`: دقیقاً یکی از دو marker تهی.

هیچ marker یا Command مستقل Cancel/Reverse در این مسیر مشاهده نشد. این دو State
از Legacy استنتاج نمی‌شوند و تا قرارداد مالک فرایند provisional هستند.

فرم Detail متد permission مستقل و OperationDate guard ندارد؛ مجوز را نمی‌توان
از Parent UI به‌طور ضمنی به Web منتقل کرد. Confirm مقصد باید State، Capability،
BankAccount scope، operation date و optimistic version را روی Server enforce
کند.

## اصلاح نام‌های گمراه‌کننده

`frmBankReconciliationList` صف اثبات‌شدهٔ Reconcile نیست:

- `ApplyingFilter` فقط یک instruction و صفر call دارد؛
- Permission آن از `TransferList.AddNew/Edit/Delete` می‌آید؛
- تغییر ردیف `Transfer.get_IsTransferGenerated` را می‌خواند؛
- Child آن، `frmBankReconciliation`، فایل XLS را با Office Interop preview می‌کند.

بنابراین این Root فعلاً
`UNRESOLVED_TEMPLATE_OR_FILE_PREVIEW_SURFACE_NOT_A_PROVEN_RECONCILIATION_QUEUE`
است. ساخت Route/Command مقصد یا حذف آن مجاز نیست؛ فقط Runtime telemetry یا
تأیید مالک می‌تواند وضعیت را ببندد. مسیر هستهٔ اثبات‌شده همان
`frmReconciliationSetup` و `frmReconciliation` است.

## قرارداد مقصد

Profile مقصد یک Aggregate نسخه‌دار و تأییدشده است؛ پس از استفاده immutable
می‌شود و با Bank/AccountType انتخاب می‌شود. Browser هیچ SQLStatement، provider
یا path اجرایی نمی‌فرستد و ParserKind یک Enum type-safe است. Import با یک نسخهٔ
مشخص Profile audit می‌شود تا بازتولید و rollback ممکن باشد.

State مقصد صریح است و markerهای Legacy فقط در Migration adapter تفسیر می‌شوند.
Confirm idempotent است، از `IMPORTED_UNCONFIRMED` شروع می‌شود و Audit/Outbox را
در همان Unit of Work می‌نویسد.

## بازتولید

```powershell
.\.venv\Scripts\python.exe scripts\windows\extract_varanegar_bank_reconciliation_profile_state_boundary.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --binary-inventory artifacts\varanegar_analysis\ui\varanegar_binary_inventory_20260827.json `
  --source-model artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_source_model_20260827.json `
  --output artifacts\varanegar_analysis\ui\varanegar_bank_reconciliation_profile_state_boundary_20260827.json
```

خروجی فعلی `PASS` است: ۱۰ Method، چهار فیلد Runtime Profile، سه فرمت، چهار جدول
Profile با صفر ردیف، View با ۴۶ ستون/هفت dependency، سه ستون marker، صفر State
صریح، صفر Hash mismatch، صفر parse error و صفر validation error.
