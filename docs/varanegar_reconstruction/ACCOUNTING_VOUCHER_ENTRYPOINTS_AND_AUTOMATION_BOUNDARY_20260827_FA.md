# مرز سند حسابداری خودکار، تأیید انبار و سند دستی

## نتیجهٔ اصلی

سه سطح متفاوت در وارانگار وجود دارد و نباید در ERP جدید یکی شوند:

1. `FormExternalVoucher`: تولید/تأیید/حذف/انتقال سند حسابداری از اسناد مبدأ؛
2. `FormConfirmVocher`: Worklist فیلترشدهٔ تأیید/عدم‌تأیید سند انبار؛
3. `FormManualVoucherDataEntry2`: ثبت دستی بدهکار/بستانکار با ابعاد حساب.

قرارداد ایستا ۷۱ Method body، ۲۱ Method نوشتاری، چهار Method برگشتی/حذفی،
هفت Command candidate و هشت Rule signal را ثبت می‌کند. هیچ Command اجرا نشده و
Owner-approved یا Runtime-effect-proven صفر است.

## سند خودکار

چهار Handler صریح دیده شد:

- `DoExternalVoucher`
- `DoExternalVoucherConfirmed`
- `DoExternalVoucherDelete`
- `DoExternalVoucherTransfer`

انتخاب DC، نوع سند مبدأ، `MinFreeOperationDate`/`MaxVoucherDate` و تنظیمات
FiscalYear/ServerConfig در تصمیم اثر دارند. تنظیمات ساخت سراسری، تفکیک شعبه فروش
و ستاد نیز در Call contract حضور دارند. بنابراین مقصد باید «سند مبدأ» و نسخهٔ
قواعد تولید را نگه دارد و Generate/Confirm/Delete/Transfer را Transitionهای
مستقل و قابل Audit پیاده کند.

## سند دستی

سند دستی فقط Amount و دو حساب نیست؛ طرف بدهکار و بستانکار می‌توانند SL، DL،
Dealer، SaleOffice و ابعاد پنجم/ششم/هفتم داشته باشند و Mandatory بودن ابعاد از
ساختار حساب می‌آید. Save و Cancel باید تراز، Scope سال مالی/مرکز و وضعیت سند را
کنترل کنند. این مسیر جایگزین تولید خودکار از سند مبدأ نیست.

## سطح SQL Clone

جست‌وجوی فقط‌خواندنی کاتالوگ با سه Token نامی ۱۲۸ Candidate برگرداند: ۴۰
Procedure، ۲۷ View، ۱۱ Table، ۹ Trigger و Constraint/Functionهای دیگر؛ مجموع
۱۹۰ Parameter و ۵۸۱ Dependency. این‌ها فقط `NAME_MATCH_ONLY` هستند: Binding
دقیق UI/Handler به SQL، Definition، Result shape و Runtime parity همگی صفرند و
نباید از این فهرست API ساخته شود.

## قرارداد مقصد و Gate

- Command خودکار باید SourceDocumentId، SourceVersion، RuleVersion،
  CommandId و ExpectedVersion داشته باشد؛
- Generated voucher با Manual voucher یک Aggregate/Permission واحد نیست؛
- Preview/validate با Generate/Confirm/Delete/Transfer تفکیک می‌شود؛
- Ledger، سند مبدأ و Posting state با Outbox و Reconciliation بسته می‌شوند؛
- تا Binding دقیق Handler→SQL و Golden balance/source-link/fault tests بسته
  نشده، این Commandها Implementation-ready نیستند.

## شواهد

- `varanegar_accounting_voucher_entrypoint_contracts_20260827.json`
- `varanegar_accounting_voucher_sql_candidates_20260827.json`

اتصال Clone `READ_ONLY`، `can_update=0` و `db_denydatawriter` بود؛ هیچ Definition،
Row value، Procedure، Trigger یا Command برنامه اجرا/ذخیره نشد.

## تکمیل Binding ساخت سند در ۲۰۲۶-۰۸-۲۸

برای Command `DoExternalVoucher` شکاف Name-match-only بسته شد. تحلیل Hash-pinned
IL مسیر دقیق زیر را ثابت کرد:

`FormExternalVoucher.DoWorkSave -> ExternalVoucherHeaderHandler.DoExternalVoucher
-> ExternalVoucherHeaderAdapter.DoExternalVoucher -> dbo.usp_DoExternalVoucher
-> dbo.usp_DoPreVoucher`.

فرم Context را `null` می‌دهد و Business یک `DataContext(Transaction.Begin)`
می‌سازد؛ Commandهای SQL به همان Transaction متصل و پس از تکمیل Adapter Commit
می‌شوند. بنابراین Atomicity مسیر Desktop ثابت است، ولی Procedure خودش Transaction
owner نیست. همچنین Policy جاری Mode 1 سال ۱۴۰۵ با ۳۶۶ Header چندمنبعی تاریخی
ناسازگار است؛ نسخهٔ مؤثر Policy روی Batch ذخیره نشده است.

جزئیات در `domains/19_VOUCHER_CREATION_ATOMICITY_AND_POLICY_FA.md`، Artifact
`voucher_creation_atomicity_and_policy_20260828.json` و Risk `R-047` ثبت شده است.
Binding دقیق Confirm/Delete/Transfer اکنون در
`domains/20_EXTERNAL_VOUCHER_LIFECYCLE_FA.md` بسته شده است. شکاف مجوز پنج Action،
Cleanup پیش از Validation و پوشش ناقص Finality خرید به‌ترتیب با `R-049`، `R-048`
و `R-050` باز مانده‌اند؛ مرز Finality در دامنهٔ ۲۱ مستند است. Runtime parity مقصد
و اجرای Golden/Fault testها همچنان باز است.
