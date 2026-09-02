# انتقال Template قواعد سند و مرز انتشار

تاریخ شاهد: ۱۴۰۵/۰۶/۰۶ (2026-08-28)

## نتیجهٔ اصلی

در بستهٔ کامل مستقر، ویرایش Rule به یک فرم کاربری نسبت داده نشد. در عوض دو
Procedure ادمینی قدیمی وجود دارد که View و پیکربندی اجرایی صدور سند را مرحله‌ای
می‌سازد:

- `dbo.VoucherTemplateTransfer`
- `dbo.VoucherTemplateArticleTransfer`

این دو Procedure اجرا نشدند. نتیجه فقط از SQL definition و IL/metadata ۶۲ فایل
Hash-pinned به دست آمده است.

Artifact اصلی:

- `artifacts/varanegar_analysis/domains/voucher_creation_atomicity_and_policy_20260828.json`
- بخش `rule_configuration_write_authority_profile`

## سطح Application مستقر

اسکن هر ۶۲ فایل Inventory چنین نتیجه داد:

- Hash mismatch: صفر؛
- Assembly مدیریت‌شدهٔ parse‌شده: ۶۲؛
- Type هدف‌نام‌دار مرتبط با ExternalVoucherType/VoucherCreator/Article: ۱۱؛
- Form هدف‌نام‌دار: صفر؛
- Caller برای `ExternalVoucherTypeHandler.SaveCommand`: صفر؛
- SQL literal مستقیم برای mutation پنج جدول Rule: صفر؛
- literal یا Caller برای دو Procedure انتقال Template: صفر.

`ExternalVoucherTypeHandler.SaveCommand` فقط هشت instruction دارد، هیچ Branch،
DataAdapter، DataContext یا Commit ندارد و بدون شرط یک `ValidationFailure` داخل
`ValidationResult` می‌سازد. Entity نیز فقط Procedure خواندنی
`dbo.USP_SDSNET_ExternalVoucherType_GetList` را معرفی می‌کند.

پس Authority نوشتن از مسیر عمومی Application اثبات نشد. این Absence به معنی
«هرگز اجرا نشده» نیست؛ ابزار خارجی یا DBA ممکن است Procedureها را اجرا کند.

## زنجیرهٔ Template Transfer

### Parent: `VoucherTemplateTransfer`

- پارامتر: صفر؛
- Dynamic execution site: چهار؛
- Viewهای سازنده را Drop و Create می‌کند؛
- `ExternalVoucherType`، `VoucherCreator` و `VoucherCreatorField` را پر می‌کند؛
- سپس Child را صدا می‌زند؛
- از Cursor برای پیمایش Catalog حسابداری استفاده می‌کند.

### Child: `VoucherTemplateArticleTransfer`

- پارامتر: صفر؛
- Dynamic execution site: یک؛
- `Article` و `ArticleComment` را پر می‌کند؛
- Caller کاتالوگی آن Parent است؛
- از Cursor استفاده می‌کند.

مقایسهٔ Column list همین Dynamic INSERT با Schema جاری یک ناسازگاری قطعی نشان
داد:

- جدول `Article` اکنون ۱۶ ستون دارد؛ Template فقط ۱۱ ستون نام می‌برد؛
- `VoucherCreatorId` و `ArticleCaption` در جدول جاری وجود ندارند؛
- شش ستون اختیاری جاری را نمی‌نویسد: `ShowDateRange`، `FromAccYear`،
  `ToAccYear`، `SeventhLedger`، `ArticleTemplateId` و `ArticleComment`؛
- ستون Required بدون Default جاافتاده: صفر؛
- با این حال وجود دو نام ستون حذف‌شده باعث شکست Dynamic statement می‌شود.

برای هر دو Procedure:

- Transaction صریح: ندارد؛
- TRY/CATCH: ندارد؛
- Rollback صریح: ندارد؛
- Authorization signal درون‌کدی: ندارد؛
- Rule version / publish / approval / audit signal: ندارد؛
- Permission صریح Object در Snapshot: ثبت نشده؛
- دسترسی Execute حساب تحلیل فقط‌خواندنی: ندارد.

شش Trigger فعال روی `Article` و `ArticleComment` وجود دارد و مرز Side effect را
گسترش می‌دهد. تعریف‌ها Hash شده‌اند و متن خامشان در Artifact ذخیره نشده است.
هر شش Trigger یک پارامتر خروجی `int` از `dbo.InsertToLog` می‌گیرند. خود Procedure
این خروجی را با `IDENT_CURRENT('gnr.tblLog')` می‌سازد، نه `SCOPE_IDENTITY`؛ اما
اسکن ساختاری نشان داد متغیر خروجی در هیچ‌یک از شش Trigger بعد از Call دوباره مصرف
نمی‌شود. بنابراین رقابتی‌بودن این خروجی یک ضعف API است، ولی اثر مستقیم آن بر
Control-flow یا Watermark همین شش Trigger **اثبات نشد**. این تفکیک مانع تبدیل یک
Signal مشکوک به Incident ادعایی می‌شود.

این محدودیت فقط برای همان شش Trigger Rule است و به کل سامانه تعمیم داده نشد:
کاتالوگ وابستگی `InsertToLog` را در ۱۱۴۲ Trigger و ۱۱ Stored Procedure می‌بیند.
همهٔ ۱۱۴۲ Trigger فعال‌اند و روی ۳۷۶ جدول در شش Schema قرار دارند؛ ۱۱۴۰ تعریف
نشانهٔ Cursor دارند، هیچ‌کدام `TRY/CATCH` ندارند، فقط سه تعریف نشانهٔ
`XACT_ABORT` دارند و هیچ Trigger با `NOT FOR REPLICATION` علامت‌گذاری نشده است.
Event edgeها شامل ۳۸۴ `INSERT`، ۳۸۴ `UPDATE` و ۳۷۸ `DELETE` هستند. این Snapshot
وابستگی فراگیر ثبت تغییر را ثابت می‌کند، نه استفادهٔ اخیر از تک‌تک جدول‌ها یا
Delivery موفق downstream را.

Blast radius به یک Domain محدود نیست: `dbo` شامل ۴۲۶ Trigger روی ۱۴۰ جدول،
`GNR` شامل ۳۲۱ روی ۱۰۷ جدول، `SLE` شامل ۲۸۲ روی ۹۲ جدول، `Acc` شامل ۵۳ روی
۱۷ جدول، `inv` شامل ۴۵ روی ۱۵ جدول و `ICA` شامل ۱۵ روی پنج جدول است. پس پورت
جداگانهٔ فروش، انبار، خرید یا حسابداری بدون Contract مشترک Outbox می‌تواند
Side effectهای Cross-domain را حذف یا تکرار کند. نام Schema/تعدادها ساختاری‌اند؛
فعالیت اخیر تک‌تک جدول‌ها از آن‌ها نتیجه نمی‌شود.

Event shape اختلاف ۱۱۴۶ Edge و ۱۱۴۲ Trigger را کامل توضیح می‌دهد: ۳۷۶ Trigger
تک‌رویدادی `DELETE`، ۳۸۲ تک‌رویدادی `UPDATE` و ۳۸۲ تک‌رویدادی `INSERT` همگی
نشانهٔ Cursor دارند؛ فقط دو Trigger بدون نشانهٔ Cursor هر سه Event را پوشش
می‌دهند. این ساختار ضرورت Golden testهای multi-row و multi-event را ثابت می‌کند،
نه وقوع Duplicate یا Lost event در Runtime.
دو Trigger درج باینری Voucher خروجی `@LogId` را واقعاً در جدول‌های
`vocherHdrInserttolog` و `vocheritmInserttolog` ذخیره می‌کنند. هر دو جدول ستون
`LogId` دارند، ولی Index، Unique index و FK آن‌ها صفر است و Snapshot فعلی هر دو
را با صفر ردیف نشان می‌دهد. پس Race window خروجی `IDENT_CURRENT` در این دو Caller
واقعی است، اما Mapping اشتباه جاری از Snapshot اثبات نشد. چهار وابستگی SQL این
دو جدول همان Triggerهای Insert/Delete هستند و Reader مبتنی بر `SELECT/JOIN` صفر
است؛ در ۶۲ Assembly Hash-pinned کاتالوگ اصلی نیز literal مستقیم این دو جدول صفر
بود. این نبود شاهد، مصرف Dynamic یا ابزار بیرونی را رد نمی‌کند، ولی اثر Downstream
فعال را هم نباید حدس زد.

## Failure window

چون Parent ابتدا چند View و جدول را تغییر می‌دهد و سپس Child را اجرا می‌کند، هر
خطا میان مراحل می‌تواند ترکیبی از این وضعیت‌ها بسازد:

- View جدید با Type/Creator ناقص؛
- Creator و Field جدید بدون Article کامل؛
- Article ایجادشده بدون Comment کامل؛
- بخشی از اثر Trigger replication و بخشی از پیکربندی محلی؛
- Rule جدیدی که Validator یا صدور آن را در SQL پویا مصرف می‌کند ولی publish کامل
  و قابل توضیح ندارد.

این Failure window فقط فرضی نیست: Child در Schema جاری هنگام رسیدن به Dynamic
INSERT شکست می‌خورد، در حالی که Parent می‌تواند پیش‌تر Viewها و سه جدول Rule را
تغییر داده باشد. اجرای تاریخی Procedure یا یک وضعیت ناقص نگه‌داری‌شده مشاهده
نشده است؛ Authority و فراوانی اجرا همچنان نامعلوم‌اند.

## قرارداد مقصد ERP نگین

1. Template ابتدا در staging ایزوله و immutable وارد شود.
2. View/Projection، Field، Type، Article، Comment و همه Predicateها پیش از publish
   کامل compile و validate شوند.
3. publish یک Command سمت Server با `CommandId` و transaction owner یکتا باشد.
4. نسخهٔ فعال فقط پس از PASS کامل با یک pointer اتمیک عوض شود.
5. Publisher و Approver جدا و هر تصمیم مجوز با Scope و Policy version ثبت شود.
6. Diff قبل از انتشار فقط نام/Hash/Shape امن و اثرهای مالی Golden را نشان دهد.
7. Replay همان Template همان Result را برگرداند و Duplicate نسازد.
8. Rollback به نسخهٔ immutable قبلی باشد، نه ویرایش/حذف تاریخچه.
9. شبکهٔ ۱۱۴۲ Trigger replication با Outbox تراکنشی صریح جایگزین یا اثر آن در
   multi-row، bulk، failure، write-amplification و Reconciliation کامل آزموده شود.
10. هیچ UI، integration یا SQL مستقیم نتواند publish command را دور بزند.

## ریسک و سطح اطمینان

- `R-054` — انتشار جزئی Rule اجرایی از Template transfer — `CRITICAL`.
- `R-055` — Receipt انتقال بدون Provenance نسخهٔ مصوب Rule — `HIGH`؛ جزئیات در
  `25_RULE_REPLICATION_TRANSPORT_AND_RECEIPT_FA.md`.
- وجود Procedure، ترتیب کلی mutation، فقدان transaction و فقدان Caller مستقر:
  **تأییدشده از شواهد ایستا**.
- هویت/نقش اجراکننده، فراوانی اجرا و اثر تاریخی: **نامعلوم**.
- نسبت‌دادن این مسیر به کاربر عادی Application: **اثبات نشده**.

## ایمنی و بازتولید

- هیچ Procedure، Trigger، View یا Assembly اجرا نشد.
- هیچ دسترسی Write یا Grant ایجاد نشد.
- حساب تحلیل برای هر دو Procedure `EXECUTE = false` دارد.
- هیچ definition خام، پیام فارسی، Rule value، کد حساب یا ردیف کسب‌وکار در Artifact
  ذخیره نشد.
- تست متمرکز: `tests/test_varanegar_voucher_creation_atomicity_policy.py`.
