# Checkpoint مجوز NGT — ۲۰۲۶-۰۸-۲۹

وضعیت: **PASS؛ نقطهٔ ادامه، نه مجوز پیاده‌سازی Command**

## خروجی تثبیت‌شده

Artifact:
`artifacts/varanegar_analysis/varanegar_authorization_checkpoint_20260829.json`

- ۲۸ منبع Hash-pinned؛
- ۷۰ Gate معنایی PASS و صفر Failure؛
- ۷۸۴ Endpoint صفت‌دار؛
- ۶۰ شکاف اعلان مجوز و ۳۸ شکاف تغییردهنده؛
- سه Subject دارای Admin assignment به‌صورت Aggregate و بدون هویت؛
- ۶۱ ریسک، ۳۴ بحرانی و ۲۳۹ اتصال Traceability؛ `R-060` از مرز زمانی و
  `R-061` از مرز تقدم/انتقال تنظیمات بعد از این بررسی مجوز افزوده شده‌اند؛
- ۵۸ Membership با Scope گروه متفاوت از User و صفر Grant مؤثر بین Applicationها؛
- صفر ماژول Command-ready.

## آنچه قطعی شد

1. Direct و Group هر دو فقط `Grant=1` را وارد مجموعه مجاز می‌کنند؛ Group به
   Query سه‌پارامتری فیلترشده Delegate می‌کند.
2. Action با ویرگول Split، Trim/Lower و با Membership دقیق مقایسه می‌شود؛
   Resource Equality است.
3. Veto پس از Union مقدار `-1` است، اما Snapshot مقدار `-1` ندارد.
4. Catalog مستقیماً در Guard خوانده نمی‌شود و لینک‌های مستقیم فعلی به Atomic
   هم‌جهت Materialize شده‌اند.
5. ۶۰ شکاف اعلان، پس از دنبال‌کردن ۴۳ Async `MoveNext`، صفر فراخوانی نام‌دار
   تصمیم مجوز دارند؛ این عدم وجود، Host/delegated/obfuscated enforcement را رد
   نمی‌کند.
6. Role دقیق `admin` پیش از Base authorization true برمی‌گرداند و سه Subject
   Aggregate فعلی دارد؛ Incident یا نامناسب‌بودن انتساب ادعا نشده است.
7. Guard مجوز فقط OwnerKey را می‌خواند و Queryهای Direct/Group مسیر `GetQuery`
   خام را مصرف می‌کنند؛ Owner filtering در `GetQueryByOwner` جدا است.
8. Snapshot فعلی ۳۲۴ Grant مؤثر و صفر Cross-Application دارد؛ این عدم رخداد،
   ریسک ساختاری مسیر خام را نمی‌بندد (`R-059`).

## مرز ایمنی

- هیچ Assembly Load/Execute نشده؛
- هیچ Endpoint یا فرم اجرا نشده؛
- هیچ Stored Procedure عملیاتی اجرا نشده؛
- Clone با READ_ONLY، `can_update=0` و `db_denydatawriter=1` استفاده شده؛
- هیچ هویت، Role assignment فردی، Credential یا Route template ذخیره نشده است.

## شکاف‌های بعدی

1. Manual owner disposition و تست Runtime کنترل‌شده برای ۶۰ Route gap؛
2. Actionهای convention-only خارج از ۷۸۴ مورد؛
3. Host/Middleware policy و delegated guardهای نامبهم؛
4. Crosswalk رسمی Legacy AccessNode ↔ NGT Permission؛
5. Owner-approved semantics برای ۵۸ Group-scope membership، مرکز پیش‌فرض،
   `IsActive=0/IsRemoved=0` و عضویت یتیم؛
6. تبدیل Admin به Break-glass/JIT و UAT هویتی خارج از Artifact ردشده؛
7. Feature precedence و رفتار Null/missing؛ مرز OperationDate در سند مستقل
   `NGT_OPERATION_DATE_AND_REPLICATION_SELECTOR_BOUNDARY_20260829_FA.md` بسته شد.

## بازتولید Offline Checkpoint

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\build_varanegar_authorization_checkpoint_20260829.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\varanegar_authorization_checkpoint_20260829.json
```

مرحلهٔ بعد در برنامهٔ ۱۵ساعته، پس از بستن Owner scope و OperationDate، به مرز
Feature/configuration precedence می‌رود.
