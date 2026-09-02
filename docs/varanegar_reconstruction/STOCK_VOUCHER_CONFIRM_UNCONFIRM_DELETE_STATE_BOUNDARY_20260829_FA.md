# مرز وضعیت تأیید، ابطال تأیید و حذف سند انبار — ۲۰۲۶-۰۸-۲۹

## نتیجهٔ اصلی

سند انبار در وارانگار فقط یک Header با فلگ تأیید نیست. شواهد SQL و IL دو خانوادهٔ
اجرایی، چند مالک تراکنش و Projection موجودی مبتنی بر Trigger را نشان می‌دهد:

1. مسیر Procedureهای نام‌دار `ConfirmVocher`/`UnConfirmVocher`؛
2. مسیر Managed با `MainConfirmVocher`، SQL پویای Header و Commit روی
   `DataContext`؛
3. مسیر `Vocher_Save` که می‌تواند Confirm را داخل Transaction بیرونی فراخوانی
   کند؛
4. Triggerهای Header/Item که تغییر `StockGoods` را اجرا می‌کنند.

بنابراین مقصد باید تأیید، ابطال تأیید و حذف را State transitionهای نسخه‌دار بداند،
نه CRUD مستقیم. Snapshot جاری منظم است، اما انتخاب مسیر Runtime و Transaction
فیزیکی مشترک هنوز اثبات نشده است.

## قرارداد SQL تأیید

`dbo.USP_SDSNET_ConfirmVocher` ابتدا Validator را فراخوانی می‌کند و بعد برای هر
سند داخل Cursor، Transaction جدید یا Savepoint می‌سازد. Header شامل
`ConfirmDate/ConfirmedBy` تغییر می‌کند. در حالت بدون Transaction محیطی، متن
Procedure شامل Commit پیش از `inv.AfterInvVocherHdr` است.

این یک پنجرهٔ ساختاری فقط برای حالت بدون Ambient transaction است؛ وقوع خرابی یا
اجرای After خارج از Transaction در مسیر `dbo.usp_sdsnet_Vocher_Save` ادعا
نمی‌شود، چون Save خودش Transaction/Savepoint بیرونی دارد و Confirm را در همان
Scope صدا می‌زند. همچنین Enlistment فیزیکی مسیرهای Managed از IL حاضر معلوم نیست.

## قرارداد SQL ابطال تأیید

`dbo.USP_SDSNET_UnConfirmVocher` نیز پیش از Transaction اعتبارسنجی می‌کند، سپس
یک Transaction/Savepoint دارد و Rollback را مدیریت می‌کند. در مسیر منتخب:

- فیلدهای تأیید Header خنثی می‌شوند؛
- جزئیات، آیتم و Header پیوندخوردهٔ نوع ۱۵ می‌توانند حذف شوند؛
- `inv.AfterInvVocherHdr` پیش از Commit فراخوانی می‌شود.

پس Unconfirm فقط معکوس‌کردن یک فلگ نیست و باید Cleanup وابسته، موجودی، حسابداری
و Outbox را زیر یک مالک تراکنش صریح نگه دارد.

## Projection موجودی و استثناها

Trigger فعال Header انتقال تأیید/ابطال تأیید را به `StockGoods` Project می‌کند و
Trigger آیتم، تغییرات آیتم سند تأییدشده را به Projection می‌برد. این Triggerها:

- `SET XACT_ABORT OFF` دارند؛
- مسیر bypass مرتبط با Replication دارند؛
- برای انواع ویژه شامل ۲۱، ۶۰، ۶۴ و ۶۵ و بخشی از نوع ۲۰ رفتار skip دارند.

وجود skip یا bypass به معنی خطای جاری نیست. در مقصد باید سیاست هر نوع سند و
Replication صریح، نسخه‌دار و با Reconciliation بعد از اجرا باشد.

## Audit و ماشین حالت مشاهده‌شده

Triggerهای Audit روی `inv.tblVocherHdrLog` رخدادهای I/U/D کامل را نگه می‌دارند؛
Trigger I/U یک تغییر محدود تاریخ سندِ تأییدشده را suppress می‌کند. از Log باقی‌مانده:

| Transition | کل | سه‌ماههٔ June–August 2026 |
|---|---:|---:|
| Confirm | ۷۵٬۵۶۹ | ۸٬۸۲۲ |
| Unconfirm | ۱۳٬۰۲۱ | ۱٬۷۷۱ |
| Delete | ۲۷٬۴۵۰ | ۳٬۲۰۰ |
| Draft update | ۱۷٬۷۷۷ | ۱٬۸۱۰ |
| Confirmed update | ۴۶٬۶۸۸ | ۴٬۱۹۳ |

هر ۲۷٬۴۵۰ حذف یکی از این دو شکل است:

- ۱۰٬۴۵۸ حذف پس از حداقل یک Unconfirm؛ شامل ۱۰٬۱۶۹ حالت بلافاصله و ۲۸۹ حالت
  Unconfirm قدیمی‌تر؛
- ۱۶٬۹۹۲ حذف سندی که در Log retained هیچ Confirm قبلی ندارد.

حذف مستقیمِ سند تأییدشده بدون Unconfirm در این جمعیت صفر است. این گزاره دربارهٔ
Log باقی‌مانده است و جای Constraint مقصد را نمی‌گیرد.

## Snapshot جاری و شکاف تاریخی

در Snapshot فعلی ۹۶٬۵۰۲ Header وجود دارد: ۹۶٬۴۹۵ تأییدشده و هفت تأییدنشده.
Log شامل ۱۲۳٬۹۶۷ شناسه است؛ ۹۶٬۵۰۲ مورد حاضر و ۲۷٬۴۶۵ مورد غایب‌اند. برای
۲۷٬۴۵۰ مورد هم Insert و هم Delete ثبت شده و `deleted-but-present` صفر است.

۱۵ شناسه Insert-log شده، اکنون غایب‌اند ولی Delete retained ندارند. همه در
۲۸ تا ۳۰ March 2024 قرار دارند و نمونهٔ سه‌ماهه ندارند. علت آن‌ها به Migration،
پاک‌سازی یا bypass نسبت داده نمی‌شود و باید به‌عنوان شکاف Audit جدا قرنطینه شوند.

در سه‌ماهه، نوع ۶۰ دقیقاً ۱٬۴۴۲ Unconfirm و ۱٬۴۴۲ Delete دارد. نوع ۱۲ نیز
۱٬۶۸۲ Delete اخیر دارد، ولی Confirm اخیر در گروه استخراج‌شده ندارد. این‌ها
Pattern نوع سند هستند، نه اثبات علت یا Procedure اجرایی.

## مرز Runtime

دو Assembly هم‌هش با Inventory، ۱۲ Method و ۵۹۶ Instruction فقط از PE
metadata/IL خوانده شد:

- `MainConfirmVocher` دو overload جدا برای Validation و Writer دارد؛ Validator
  Cardex/OnHand/Projection را بررسی می‌کند؛
- Writer، Updateهای مستقیم را پیش از `DataContext.Commit` صدا می‌زند و در Method
  منتخب Adapterهای Confirm/Unconfirm را صدا نمی‌زند؛
- Update مستقیم Header از SQL پویا و بدون Commit محلی در همان Method استفاده
  می‌کند؛
- Business methodهای نازک به Adapter واگذار می‌کنند؛ Adapter Confirm و Unconfirm
  Procedure نام‌دار را Execute و سپس Commit می‌کنند؛
- در Methodهای منتخب سیگنال Rollback صریح دیده نشد.

External callsite، انتخاب overload/branch و Enlistment فیزیکی میان Dynamic SQL،
Adapter و Save بیرونی اثبات نشده است. پس هیچ‌کدام مسیر Runtime غالب اعلام نمی‌شود.

## ارتباط با تطبیق رسمی موجودی

مقایسهٔ ناقص `StockGoods` با Cardex-only نشان می‌دهد:

- موجودی سالم: ۳۳٬۳۱۴ کلید مقایسه، ۳۱٬۷۲۰ exact و ۱٬۵۹۴ difference؛
- موجودی آسیب‌دیده: ۳۳٬۳۱۴ exact و صفر mismatch؛
- رزرو: ۳۳٬۳۱۴ exact و صفر mismatch.

این ۱٬۵۹۴ مورد مغایرت واقعی نیست. فرمول رسمی Legacy، تعهد فروش فعالِ هنوز
خارج‌نشده را از Cardex کم می‌کند؛ همین تعهد دقیقاً ۱٬۵۹۴ کلید و ۱۰۴٬۴۷۰ واحد
است و پس از اعمال آن، Residual هر ۳۳٬۳۱۴ کلید صفر می‌شود. این شاهد به مسیر
Confirm/Unconfirm خاص نسبت داده نمی‌شود؛ در مقصد Cardex، تعهد فروش و Snapshot
سه Projection جدا با Reconciliation رسمی هستند.

## قرارداد مقصد

- `ConfirmStockVoucher` و `UnconfirmStockVoucher` با expected state/version و
  idempotency key؛
- یک مالک Transaction فیزیکی برای Validation، Header، Cleanup نوع ۱۵، Projection،
  Accounting و Outbox؛
- Event append-only و Tombstone برای حذف، بدون جعل Actor/Reason/Route؛
- Projector صریح و deterministic برای موجودی، با policy نسخه‌دار انواع ویژه؛
- Route-parity برای Adapter Procedure، Dynamic writer و Outer Save؛
- تست Fault injection در همهٔ مرزها و Reconciliation رسمی پیش از Release write.

## ریسک ثبت‌شده

`R-076` با شدت Critical ثبت می‌شود. این ریسک دربارهٔ تفاوت مسیر، مالک تراکنش و
Projection است؛ وقوع خرابی جاری را ادعا نمی‌کند و ۱٬۵۹۴ کلید را درست به‌عنوان
تعهد فروش، نه مغایرت موجودی، حفظ می‌کند.

## ایمنی و محدودیت

- Clone فقط‌خواندنی بود و هیچ Procedure، Trigger، Form یا Command اجرا نشد؛
- Assemblyها Load/Execute نشدند؛ فقط PE metadata/IL خوانده شد؛
- هیچ شناسه، کالا، انبار، تأمین‌کننده، سند، توضیح، کاربر یا ردیف Log ذخیره نشد؛
- شمارش‌های Log ناشناس‌اند و Call stack، علت، Actor یا شاخهٔ Runtime نمی‌سازند.

## خروجی‌های بازتولیدپذیر

- `scripts/sql/extract_varanegar_stock_voucher_state_boundary.py`
- `scripts/sql/extract_varanegar_stock_voucher_state_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/stock_voucher_state_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/stock_voucher_state_runtime_boundary_20260829.json`
