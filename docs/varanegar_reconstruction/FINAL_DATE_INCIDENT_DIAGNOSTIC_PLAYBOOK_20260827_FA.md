# راهنمای تشخیص رخدادهای تاریخ عملیات و تاریخ قطعی ورانگر

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای تحلیل Static، Aggregate و IL؛ اجرای Command و اثبات Runtime برابر صفر**

## نتیجهٔ اصلی

`GNR.tblOprDate` یک «تنظیم تاریخ» ساده نیست. این جدول هم‌زمان چهار مفهوم مستقل
را نگه می‌دارد: تاریخ جاری عملیات (`OprDate`)، مرز قطعی (`LastDate`)، مجوز ستاد
(`LicenseDate`) و بسته‌بودن سال/زیرسیستم (`IsClosed`). کلید معنایی آن ترکیب
`DCRef + AccYear + SysRef` است و `SysRef`های مهم ۱ فروش، ۲ مالی/خزانه، ۳ هزینه
شعب، ۵ خرید و ۷ تنخواه هستند.

در Clone، ۲۵۶ ماژول SQL متن‌محور به این جدول اشاره می‌کنند و Catalog نیز ۲۴۷
مصرف‌کنندهٔ وابسته را نشان می‌دهد؛ بنابراین خطای این جدول می‌تواند در فروش،
انبار، خزانه، خرید، حسابداری، توزیع، POS و NGT دیده شود، حتی اگر پیام خطا نام
«تاریخ قطعی» را نیاورد.

## مسیر واقعی از فرم تا SQL

پنج AccessNode برای مدیریت تاریخ قطعی وجود دارد. سه فرم جدید خرید، مالی و
تنخواه از UI به `FinalDateManagementHandler`، سپس
`FinalDateManagementAdapter` و در نهایت SPهای مستقل `USP_SDSNET_*` می‌رسند.
Adapter هر هشت Validation/Update را با `System.String.Format` به متن SQL تبدیل
می‌کند و پارامتر Database واقعی به `DataContext.Query` نمی‌دهد. هیچ Assembly
لود یا اجرا نشد؛ این مسیر مستقیماً از PE metadata و IL خوانده شده است.

مجوز ثبت جدا از مجوز صفحه در درخت ثبت‌شده دیده نشد. از ۱۴۱ کاربر فعال ناشناس،
برای هر Route فقط ۸ یا ۹ نفر Effective allow دارند که ۷ نفر آن‌ها Admin هستند؛
هیچ Explicit deny ثبت نشده و بقیه Neutral/no-allow هستند. این آمار هویت هیچ
فردی را نشان نمی‌دهد و مجوز کاربر جاری را ثابت نمی‌کند.

## یازده کشف تشخیصی

| شناسه | شدت | کشف | نشانهٔ معمول |
|---|---|---|---|
| FD-001 | بحرانی | شش مسیر Insert ستون اجباری و بدون Default به نام `UserRef` را نمی‌فرستند | ثبت اول خطا می‌دهد ولی ویرایش رکورد موجود کار می‌کند |
| FD-002 | بالا | ساخت اولیهٔ تنخواه در SP تجمیعی با فیلدهای فروش Guard شده است | تنخواه فقط وقتی ردیف از قبل وجود دارد ذخیره می‌شود |
| FD-003 | بالا | دو شرط Validation غیرقابل‌وقوع‌اند: `@BuyDate<@BuyDate` و خالی/ناخالی هم‌زمان | Validation موفق است ولی قاعدهٔ مورد انتظار اصلاً اجرا نشده |
| FD-004 | بالا | `CASE` مربوط به `LicenseDate` مالی و تنخواه `ELSE` ندارد | `LicenseDate` ناخواسته NULL می‌شود |
| FD-005 | بالا | چهار SP اصلی Update تراکنش صریح ندارند | بخشی از SysRefها تغییر کرده و بخش دیگر خطا داده است |
| FD-006 | بحرانی | Trigger بازکردن مالی، Statement نوع ۱۰۰۵ را بر اساس DC حذف می‌کند ولی `AccYear` ندارد | بازکردن یک سال می‌تواند ماندهٔ اول دورهٔ سال‌های دیگر را حذف کند |
| FD-007 | بحرانی | بازکردن فروش، وضعیت ۴/۷ توزیع را برای همهٔ سال‌های DC جابه‌جا می‌کند | توزیع‌های سال‌های قبل ناگهان خاتمه‌یافته/توزیع‌شده می‌شوند |
| FD-008 | بالا | Trigger فروش `@ErrMsg` خروجی SP توزیع را نادیده می‌گیرد | تاریخ باز می‌شود ولی تغییر توزیع به‌علت پیش‌شرط انجام نشده است |
| FD-009 | بالا | Triggerها از `TOP 1` یا متغیر Scalar روی `inserted/deleted` استفاده می‌کنند | Bulk/Replication فقط یک ردیف دلخواه را مبنا می‌گیرد |
| FD-010 | بالا | Adapter فرمان‌ها را با Text interpolation می‌سازد | ورودی بدشکل به خطای Syntax/Quote تبدیل می‌شود |
| FD-011 | متوسط | درخت فعلی مجوز Save مستقل از صفحه ندارد | دسترسی صفحه با مجوز Command اشتباه گرفته می‌شود |

### جزئیات FD-001

`UserRef` در `GNR.tblOprDate` اجباری است و Default ندارد. با این حال مسیرهای زیر
در Insert آن را حذف کرده‌اند:

- `GNR.USP_SDSNET_UpdateBuyDateManagement`
- `GNR.USP_SDSNET_UpdateMaliDateManagement`
- `GNR.USP_SDSNET_UpdateTankhahDateManagement`
- `dbo.DoOprDate_Open`
- `dbo.DoPOrder_UpdateOprDate`
- `dbo.usp_sdsnet_OperationDate_Save`

این موضوع با Snapshot فعلی مهم‌تر می‌شود: در آخرین سال مالی، از دو DC
پیکربندی‌شده برای `SysRef=5` و `SysRef=7` هیچ ردیفی وجود ندارد؛ `SysRef=3` نیز
کاملاً غایب است. پس عیب فقط نظری نیست: مسیر First-create دقیقاً در ناحیه‌ای
قرار دارد که دادهٔ فعلی به آن نیاز پیدا می‌کند. هیچ Command برای اثبات نتیجه
اجرا نشده، بنابراین این نتیجه «ریسک قطعی Static + وضعیت Aggregate» است، نه گزارش
یک اجرای واقعی.

### جزئیات بازکردن مالی

`GNR.Trg_DeleteStatement` روی تغییر `IsClosed: 1→0` اجرا می‌شود و این Delete را
انجام می‌دهد:

```text
StatementTypeRef = 1005 AND DcRef = DC جاری
```

فیلتر `AccYear` وجود ندارد. در Clone فعلی رکورد نوع ۱۰۰۵ صفر است، بنابراین Blast
radius فعلی صفر ثبت شد؛ اما نبود داده، نقص Scope را اصلاح نمی‌کند. قبل از هر
Reopen واقعی باید شمارش همین نوع Statement به تفکیک DC و سال، Backup/Restore و
تأیید مالک مالی وجود داشته باشد.

### جزئیات بازکردن فروش و توزیع

بازشدن فروش، `SLE.usp_tblDist_BackupBeforeRD` را فراخوانی می‌کند. این SP:

- جدول Backup را بدون قید DC پاک می‌کند؛
- بسته به تنظیم `RetDist` همهٔ وضعیت‌های ۴ را به ۷ یا همهٔ ۷ها را به ۴ تغییر
  می‌دهد؛
- شرط سال مالی در Update Comment شده است؛
- همهٔ Triggerهای `SLE.tblDist` را موقتاً Disable می‌کند؛
- پیام خروجی پیش‌شرط در Trigger فراخوان نادیده گرفته می‌شود.

Blast radius دو شاخه در Snapshot فعلی ۱۲ توزیع وضعیت ۴ در یک سال و ۲۳٬۳۸۲
توزیع وضعیت ۷ در سه سال است. مقدار واقعی `RetDist` عمداً خوانده یا ذخیره نشده؛
پس قبل از Command باید هر دو شاخه خطر تلقی شوند. اکنون ۷ Trigger جدول توزیع
همگی فعال‌اند و Backup صفر ردیف دارد.

## فعالیت سه‌ماهه

از Log چهل‌وشش‌میلیونی فقط بازهٔ هویتی متناظر با سه ماه اخیر Scan شد. هیچ Script
خام ذخیره نشد. ۱۶۰ رویداد مرتبط با `tblOprDate` پیدا شد که هر ۱۶۰ مورد Update
بودند؛ Insert و Delete ثبت‌شده صفر بود:

| ماه | جهت ۱ | جهت ۲ | جمع |
|---|---:|---:|---:|
| ۲۰۲۶-۰۵ | ۱۱ | ۰ | ۱۱ |
| ۲۰۲۶-۰۶ | ۷۷ | ۳ | ۸۰ |
| ۲۰۲۶-۰۷ | ۳۸ | ۰ | ۳۸ |
| ۲۰۲۶-۰۸ | ۳۱ | ۰ | ۳۱ |

این الگو نشان می‌دهد عملیات فعال است، اما Insert صفر به‌تنهایی ثابت نمی‌کند فرم
First-create استفاده نشده؛ Log می‌تواند ناقص باشد و مسیرهای خطاداده اصلاً ثبت
نشوند. `ModifiedDate` نیز شاخص قابل‌اتکای کامل نیست، چون همهٔ SPها آن را Update
نمی‌کنند.

## Runbook حل مسئله

برای سؤال یا رخداد واقعی، ترتیب بررسی باید این باشد:

1. نشانه را دقیق نام‌گذاری کن: بازنشدن فرم، خطای Save، بسته‌بودن سند، تفاوت
   تاریخ، NULL شدن مجوز، یا تغییر ناخواستهٔ توزیع/مانده.
2. `DCRef`، سال مالی و `SysRef` را جداگانه تعیین کن؛ `DC=0` و DC شعبه هم‌معنا
   نیستند.
3. پیش از تحلیل پیام UI، وجود ردیف دقیق `DCRef+AccYear+SysRef` را بررسی کن.
4. `OprDate`، `LastDate`، `LicenseDate` و `IsClosed` را مستقل مقایسه کن.
5. Route access، دامنهٔ داده و مجازبودن Command را سه Gate جدا بدان.
6. SiteType و Replication mode را وارد تحلیل کن؛ رفتار CN/DC/SingleDC/DBOne
   یکسان نیست.
7. برای Reopen مالی، Statement نوع ۱۰۰۵ را در همهٔ سال‌های همان DC شمارش کن.
8. برای Reopen فروش، هر دو Blast radius وضعیت ۴ و ۷ و وضعیت Backup/Triggerها را
   محاسبه کن.
9. بعد از Save، همهٔ SysRefها و اثرات Accounting/Distribution را دوباره تطبیق
   بده؛ موفقیت UI Atomicity را ثابت نمی‌کند.

## قرارداد نسخهٔ وب

نسخهٔ شخصی ERP نباید این قابلیت را به یک Update عمومی تبدیل کند. حداقل نیازها:

- Commandهای مستقل فروش، مالی، خرید و تنخواه؛
- کلید نسخه‌دار `DC + FiscalYear + System`؛
- پارامترهای Typed و عدم Text interpolation؛
- Reopen مستقل با Reason، Approval و Preview دامنهٔ اثر؛
- تراکنش اتمیک برای Boundary، Audit، Outbox و اثرات جانبی؛
- Scope صریح سال مالی در حذف/تغییر Statement و Distribution؛
- مجوز مستقل `view`، `set-final-date`، `reopen` و `close-year`؛
- Idempotency و Fault test بین هر اثر جانبی؛
- Reconciliation پس از اجرا و امکان Rollback عملیاتی.

## Artifact و دستور بازتولید

- Artifact: `artifacts/varanegar_analysis/ui/varanegar_final_date_diagnostic_contract_20260827.json`
- Extractor: `scripts/sql/extract_varanegar_final_date_diagnostic_contract.py`

```powershell
$env:PYTHONUTF8='1'
.\.venv\Scripts\python.exe scripts\sql\extract_varanegar_final_date_diagnostic_contract.py `
  --source-directory '\\192.168.1.171\exe\VN.SDS.Container' `
  --output artifacts\varanegar_analysis\ui\varanegar_final_date_diagnostic_contract_20260827.json
```

## Gate و محدودیت

این سند برای تشخیص Static و طراحی Runbook معتبر است. برای اجرای هر Command هنوز
Golden Case اجرایی، کاربر احرازشده، Backup/Restore، UAT مالک، Target ایزوله،
Fault injection و Reconciliation لازم است. هیچ تاریخ کسب‌وکار، هویت، مقدار
تنظیم، متن خام Log یا نتیجهٔ Validation ذخیره نشد؛ هیچ SP/فرم عملیاتی اجرا نشد
و هیچ داده‌ای تغییر نکرد.
