# دامنه ۲۰: چرخهٔ تأیید، حذف و انتقال سند خارجی به دفترکل

تاریخ استخراج: ۲۰۲۶-۰۸-۲۸  
وضعیت: **Binding و تراکنش هر سه فرمان اثبات شد؛ Snapshot نهایی سالم است؛ Side-effect پیش از Validation و شکاف مجوز عملیاتی کشف شد**

## نتیجهٔ کوتاه

نسخهٔ مستقر سه مسیر واقعی بعد از صدور دارد:

```text
Confirm / Unconfirm
  FormExternalVoucher.DoWorkConfirmed (یا ادامهٔ DoWorkSave)
  -> ExternalVoucherHeaderHandler.DoExternalVoucherConfirmed
  -> ExternalVoucherHeaderAdapter.DoExternalVoucherConfirmed
  -> dbo.usp_DoExternalVoucherConfirmed

Delete
  FormExternalVoucher.DoWorkDelete
  -> ExternalVoucherHeaderHandler.DoExternalVoucherDelete
  -> ExternalVoucherHeaderAdapter.DoExternalVoucherDelete
  -> dbo.usp_DoExternalVoucherDelete

Transfer to ledger
  FormExternalVoucher.DoWorkTransfer (یا ادامهٔ DoWorkSave)
  -> ExternalVoucherHeaderHandler.DoExternalVoucherTransfer
  -> ExternalVoucherHeaderAdapter.DoExternalVoucherTransfer
  -> dbo.usp_DoExternalVoucherTransfer
```

در هر مسیر، UI مقدار `DataContext=null` می‌دهد، Business یک
`DataContext(Transaction.Begin)` می‌سازد، Adapter را اجرا می‌کند، سپس Commit و
Dispose در Finally انجام می‌شود. هر سه Procedure عملیاتی فاقد `BEGIN TRAN`،
`COMMIT` و `ROLLBACK` هستند؛ پس Atomicity مسیر Desktop اثبات شده ولی Caller مستقیم
SQL یا Integration غیرمعمول نباید مجاز باشد.

## منابع و ایمنی

- Artifact ماشین‌خوان:
  `artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json`
- Extractor:
  `scripts/sql/extract_varanegar_voucher_creation_atomicity_policy.py`
- Test:
  `tests/test_varanegar_voucher_creation_atomicity_policy.py`
- هفت Assembly مستقر Version `5.9.0.376` با SHA-256 موجود در Inventory
  Hash-check و فقط با PE metadata/IL parser خوانده شدند؛ Load/Execute نشدند.
- SQL فقط روی `127.0.0.1 / NeginPakhsh_WebDev` با وضعیت `READ_ONLY`،
  `can_update=0` و `db_denydatawriter=1` خوانده شد.
- هیچ Procedure عملیاتی اجرا نشد و هیچ Row/شناسهٔ عملیاتی در Artifact ذخیره نشد.

## State machine اثبات‌شده

```text
ISSUED_UNCONFIRMED
  ├─ Confirm ───────────────> CONFIRMED_NOT_TRANSFERRED
  └─ Delete whole batch ────> REMOVED / source eligible for reissue

CONFIRMED_NOT_TRANSFERRED
  ├─ Unconfirm ─────────────> ISSUED_UNCONFIRMED
  └─ Transfer ──────────────> TRANSFERRED_TO_LEDGER

TRANSFERRED_TO_LEDGER
  ├─ Unconfirm: blocked
  └─ Delete external batch: blocked
```

این نمودار فقط چرخهٔ External Voucher است؛ تغییر وضعیت یا حذف خود `Voucher` در
دفترکل فرمان و قرارداد جدا دارد و نباید با Delete این صفحه یکی شود.

## قرارداد Confirm / Unconfirm

`dbo.usp_DoExternalVoucherConfirmed` این Guardها را اعمال می‌کند:

1. سال حسابداری، کاربر، فهرست Header و مقدار Confirm معتبر باشد؛
2. Confirm روی Header ازقبل تأییدشده رد می‌شود؛
3. برای Confirm، جمع بدهکار و بستانکار External line باید برابر باشد؛
4. Unconfirm روی Header ازقبل تأییدنشده رد می‌شود؛
5. Unconfirm پس از ساخته‌شدن `Voucher` دفترکل رد می‌شود؛
6. `Confirmed`، تأییدکننده و زمان تأیید با هم تغییر می‌کنند؛
7. پس از Update، پیداشدن Voucher هم‌زمان خطای Concurrency می‌دهد و تراکنش بیرونی
   Update را Rollback می‌کند.

Procedure هنگام Update همه Triggerهای `ExternalVoucherHeader` را موقتاً Disable
می‌کند. مقصد نباید این رفتار سراسری را کپی کند؛ Transition باید با شرط نسخه/State
در همان Row و Constraintهای پایگاه داده انجام شود.

## قرارداد Delete

Delete فقط وقتی مجاز است که همه Headerهای انتخابی:

- هنوز به `Voucher` دفترکل منتقل نشده باشند؛
- تأییدنشده باشند؛
- همگی متعلق به یک نسل Old/New system باشند.

برای سندهای Old system، حذف باید از آخرین سند هر نوع و به‌شکل پیوسته باشد. سپس یک
Command اتمیک این مجموعه را حذف می‌کند:

1. `PreVoucher`؛
2. `ExternalVoucherHeaderXExternalVoucherType`؛
3. `TblExternalRelation`؛
4. `ExternalVoucher`؛
5. `ExternalVoucherHeader`.

SQL متن عملیات را با `InsertToLog` ثبت و Session context مخصوص Delete را فعال
می‌کند. کنترل Concurrency پس از Mutation دوباره وجود دارد و در Caller استاندارد با
خطا کل حذف Rollback می‌شود.

نتیجهٔ مهم: PreVoucher «برای همیشه» immutable نیست. Snapshot فقط تا وقتی Batch
صادرشده برقرار است immutable است؛ حذف رسمیِ Batch تأییدنشده Source را برای Reissue
آزاد می‌کند. ERP مقصد باید `DeleteIssuedBatch` را فرمان مستقل، Audit‌شده و دارای
Reason کند؛ حذف فیزیکی بدون Tombstone برای بازسازی تاریخچه مناسب نیست.

## قرارداد Transfer به دفترکل

انتقال فقط Header تأییدشده و هنوز انتقال‌نیافته را می‌پذیرد و بعد از کنترل Fiscal
mapping، `usp_DoExternalVoucherTransferValidation` را اجرا می‌کند. در مسیر موفق:

- `Voucher` ساخته و شماره/Serial محاسبه می‌شود؛
- `VoucherStatusHistory` و Pointer وضعیت ساخته می‌شود؛
- `VoucherEditLog` ثبت می‌شود؛
- همه `VoucherItem`ها از External line منتقل می‌شوند؛
- `SetVoucherNo` برای نمایش Crosswalk شماره‌ها ساخته می‌شود؛
- کنترل Concurrency از ساخته‌شدن Voucher موازی جلوگیری می‌کند.

Procedure TRY/CATCH دارد و خطای SQL را دوباره Raise می‌کند؛ Transaction همچنان
مالک Server procedure نیست و در Business ایجاد شده است.

## قرارداد مجوز و Scope

شاهد Hash-pinned فرم، قالب پایه، Business/DataAccess و SQL این تفکیک را نشان
می‌دهد:

- Query گرید با `AccYear` و `DC` نشست محدود می‌شود و درخت‌های DC/نوع سند نیز از
  Handlerهای session-aware استفاده می‌کنند؛ این **Scope خواندن** است.
- `usp_DoExternalVoucher` تاریخ سند را در بازهٔ سال مالی و در برابر تاریخ نهایی
  سیستم منبع کنترل می‌کند؛ این **Guard نهایی‌شدن منبع** است، اما پوشش خرید کامل
  نیست و `OperationId=5` استثنا دارد. جزئیات در دامنهٔ ۲۱ ثبت شده است.
- قالب پایه برای New/Edit/Delete/Print/Excel مجوز Toolbar می‌سنجد، اما Confirm،
  Unconfirm و Transfer در آن Gate نیستند. Override همین فرم New/Edit/View را
  پنهان و Confirm/Unconfirm را Visible می‌کند.
- کنترل‌های سفارشی Save و Transfer هیچ اتصال مشاهده‌شده‌ای به Permission ندارند؛
  خود متدهای صدور، Confirm، Unconfirm، Delete و Transfer نیز صفر فراخوانی
  `HasPersmission` دارند.
- چهار Procedure عملیاتی صدور/تأیید/حذف/انتقال هیچ کنترل Access/action
  authorization ندارند. صدور فقط وجود User/DC را کنترل می‌کند و ارتباط مجاز
  User→DC را نمی‌سنجد؛ Delete حتی Actor نمی‌گیرد.

این شاهد ثابت نمی‌کند که «هر کاربر» حتماً به صفحه دسترسی دارد؛ یک Gate کلی منو یا
Middleware خارج از مسیر فرمان ممکن است وجود داشته باشد. آنچه تأیید شده این است
که پس از رسیدن Principal به این فرم/endpoint، مجوز مستقل سمت Server برای پنج عمل
حساس و Scope منبع پیدا نشد. دسترسی صفحه جای مجوز Command نیست.

قرارداد مقصد باید برای `Issue / Confirm / Unconfirm / Delete / Transfer` پنج
مجوز مستقل، Deny-first scope سال/DC/نوع/Header، تفکیک وظایف issuer/approver/poster،
Actor برگرفته از Context احراز هویت‌شده و Audit تصمیم Policy داشته باشد. این شکاف
با `R-049` بحرانی ردیابی شده است.

## شکاف دقیق: Mutation پیش از Validation

ترتیب واقعی در `dbo.usp_DoExternalVoucherTransfer` چنین است:

```text
reject already-transferred header
-> DELETE stale SetVoucherNo for selected headers
-> run transfer validation
-> if validation rows exist: RETURN normally
-> Business commits
```

پس Validation از دید Command خالص نیست: اگر رکورد مانده‌ای در `SetVoucherNo`
وجود داشته باشد ولی Voucher فعال وجود نداشته باشد، خطای کسب‌وکار Validation با
`RETURN` عادی می‌تواند Cleanup قبلی را Commit کند. Snapshot فعلی هیچ مورد مانده‌ای
ندارد؛ بنابراین این یک **ریسک قابل‌دسترسی در کد** است، نه خرابی مشاهده‌شده در داده.

قرارداد مقصد:

1. `ValidateTransfer` فقط Read و بدون Mutation باشد؛
2. هر Cleanup بعد از Validation PASS و داخل Command انتقال انجام شود؛
3. Business failure و Exception هر دو Result صریح داشته باشند و هیچ‌کدام Commit
   جزئی نکنند؛
4. Idempotency key و Row version از Transfer موازی جلوگیری کند.

## وضعیت Snapshot

| Scope | Header | Confirmed | دقیقاً یک Voucher فعال | SetVoucherNo | چند Voucher فعال | Orphan/duplicate شماره |
|---|---:|---:|---:|---:|---:|---:|
| کل Clone | ۱۹۷٬۵۱۸ | ۱۹۷٬۵۱۸ | ۱۹۷٬۵۱۸ | ۱۹۷٬۵۱۸ | ۰ | ۰ |
| ۱۴۰۵/۰۳/۰۱..۱۴۰۵/۰۵/۳۱ | ۲۰۴ | ۲۰۴ | ۲۰۴ | ۲۰۴ | ۰ | ۰ |

در Snapshot هیچ Header تأییدنشده، Confirmed-but-not-transferred یا Delete-eligible
باقی نمانده است. این پاکیزگی State نهایی را ثابت می‌کند، نه رفتار شاخه‌های منفی؛
برای آنها Fixture مصنوعی و Fault injection لازم است.

## ماتریس Verification

| نیاز/ریسک | Observable | شاهد | نتیجه / Gap |
|---|---|---|---|
| Binding دقیق هر سه فرمان | UI→Business→Adapter→SQL literal | IL مستقر Hash-pinned | PASS |
| Atomicity Caller استاندارد | Begin→Query→Commit→Finally Dispose | IL مستقر | PASS؛ SQL مستقیم ممنوع |
| Guardهای State | Confirmed/Voucher/balance/year/list checks | Definition SQL | PASS ساختاری |
| Delete کامل Batch | پنج Delete مرتبط + Concurrency check | Definition SQL | PASS ساختاری؛ نمونه جاری ندارد |
| Transfer کامل دفترکل | Voucher/Item/Status/EditLog/number crosswalk | Definition SQL | PASS ساختاری |
| State نهایی یک‌به‌یک | Aggregate کل Clone و سه‌ماهه | Clone فقط‌خواندنی | PASS |
| Validation بدون Side effect | Delete شماره پیش از Validator و RETURN عادی | SQL + Commit مسیر Business | FAIL؛ Snapshot خرابی ندارد |
| مجوز جداگانهٔ پنج عمل حساس | Permission IL + SQL authorization signals | شش DLL Hash-pinned + SQL | FAIL؛ Gate کلی صفحه خارج مسیر ممکن است |
| نهایی‌شدن عملیات منبع پیش از صدور | Fiscal range + per-system final date | Definition + coverage | PASS ترتیب؛ FAIL پوشش کامل خرید |

## Golden و Fault tests مقصد

1. Confirm سند نامتوازن باید بدون تغییر State رد شود.
2. Unconfirm سند منتقل‌شده باید بدون تغییر State رد شود.
3. Delete سند تأییدشده یا منتقل‌شده باید رد شود.
4. Delete مجاز باید Batch را Tombstone کند و Source را با Reason برای Reissue آزاد
   کند.
5. خطای بعد از هر Write انتقال باید Voucher/Item/Status/EditLog/شماره را همگی
   Rollback کند.
6. Validation failure حتی با Crosswalk مانده، هیچ Mutation نکند.
7. دو Transfer موازی فقط یک Voucher فعال بسازند و Retry همان Result را بگیرد.
8. یک انتقال موفق باید Header→Voucher و Header→SetVoucherNo دقیقاً یک‌به‌یک باشد.
9. ماتریس نقش باید View-only، issuer-only، approver-only و poster-only را برای هر
   عمل و Scope سال/DC/نوع/Header با Positive/Deny test پوشش دهد.
10. شناسهٔ User ارسالی Client نباید Actor مجوز باشد؛ Server باید Principal
    احراز هویت‌شده را ثبت و Cross-scope IDهای جعل‌شده را رد کند.

## سطح اطمینان و محدودیت

- Binding، Transaction mechanics و Procedure contract: **تأییدشده**.
- پاکیزگی State نهایی Clone: **تأییدشده**.
- اثر بالقوهٔ Cleanup پیش از Validation: **تأییدشده از مسیر کد**؛ وقوع تاریخی
  آن در Snapshot اثبات نشده است.
- رفتار زیر Load/Deadlock یا Caller غیرDesktop: **اثبات‌نشده**؛ هیچ Mutation یا
  Fault injection روی وارانگار اجرا نشد.
