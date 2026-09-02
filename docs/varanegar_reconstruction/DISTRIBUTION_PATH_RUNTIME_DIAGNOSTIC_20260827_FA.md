# قرارداد واقعی مسیر توزیع در ورانگار

## نتیجهٔ قطعی

`SLE.tblDist.DistPath` در نصب فعلی نگین، FK به `GNR.tblDistPath.ID` نیست.
این ستون یک کد عددی وابسته به حالت تنظیمات است. بنابراین عبارت قبلیِ
«۲۶٬۰۸۶ توزیع بدون مستر مسیر/رکورد یتیم» از نظر مدل داده غلط بود.

شواهد مستقل این نتیجه را تثبیت می‌کنند:

1. ستون `DistPath` هیچ Foreign Key رسمی ندارد؛
2. `SLE.usp_sdsnet_CreateDist` پارامتر `@DistPath INT` را مستقیم در Insert و
   Update می‌نویسد و اصلاً `GNR.tblDistPath` را نمی‌خواند؛
3. در `DistPathLookUpEdit_EditValueChanged` مقدار انتخاب‌شده از
   `DistPathTreeNo` به `txtDistpath` منتقل می‌شود، نه `ID` مستر؛
4. در `FillDistPathLookUpEdit` انتخاب‌گر مسیر برای `DistLimitType=0` یا `3`
   پر نمی‌شود؛
5. `FormFollowDist_Load` ورود عددی آزاد را فقط وقتی فعال می‌کند که هم
   `DistPathingType=0` و هم `DistLimitType=0` باشند؛
6. هر دو ردیف تنظیمات مؤثر Clone دقیقاً همین جفت `0/0` را دارند.

سطح اطمینان: بالا، بر پایهٔ Schema، تعریف SQL، IL فرم و مقادیر تجمیعی تنظیمات.

## معنای ۲۶٬۰۸۶ ردیف

این ۲۶٬۰۸۶ Header هفت کد عملیاتی دارند: `1، 2، 3، 4، 5، 11، 12`.
کدهای ۱ و ۲ غالب‌اند، اما کد ۵ نیز در بازهٔ سه‌ماههٔ اخیر ۱۲۰ بار ظاهر شده؛
پس این فیلد یک Flag دوحالته نیست و نباید فقط به ۱/۲ محدود شود.

جدول‌های قدیمی Zone/Area/Path همگی خالی‌اند و View درخت مسیر فقط Root مصنوعی
را برمی‌گرداند. نتیجه این نیست که Headerها خراب‌اند؛ نتیجه این است که عنوان،
ناحیه و سلسله‌مراتب انسانی این کدها از مستر فعلی قابل بازیابی نیست.

## قرارداد تشخیص مشکل

برای هر خطای مربوط به مسیر توزیع باید به‌ترتیب زیر جلو رفت:

1. مشخص شود مشکل دربارهٔ `DistPath`، شناسهٔ Distribution، تیم پخش، یا عنوان
   جغرافیایی Route است؛
2. مقدار مؤثر `DistPathingType` و `DistLimitType` در Scope همان اجرا خوانده شود؛
3. `DistPath` به‌عنوان کد عددی حفظ شود و هرگز برای تشخیص Orphan به
   `GNR.tblDistPath.ID` Join نشود؛
4. مجوزهای `DistManagement.View/AddNew/Edit` جدا از DC، سال مالی، تاریخ عملیات
   و State توزیع ارزیابی شوند؛
5. اگر عنوان لازم است، Crosswalk معتبر از منبع مستقل یا تأیید اپراتور گرفته
   شود؛ عنوان حدسی یا Default ممنوع است؛
6. نتیجهٔ `CreateDist` و Commit واحد کار بررسی شود؛ موفقیت ظاهری فرم به‌تنهایی
   اثبات Commit نیست.

## قرارداد نسخهٔ وب و مهاجرت

- در مدل Distribution یک Value Object عددی مثل `distribution_path_code` نگه
  داشته شود؛
- `path_mode` و نسخهٔ تنظیمات مؤثر کنار تصمیم اعتبارسنجی ثبت شوند؛
- `route_master_id` فقط در حالتی ساخته شود که منبع معتبر و Crosswalk تأییدشده
  وجود داشته باشد؛
- کد خام، Scope، Provenance و وضعیت `unlabeled` حفظ شوند؛
- هیچ کدی به Route پیش‌فرض جذب نشود؛
- تغییر از حالت عدد آزاد به Lookup یک تغییر تنظیماتی نسخه‌دار است، نه Migration
  بی‌اثر؛
- مجوز View، AddNew و Edit و همچنین Guardهای State/Date/Scope مستقل بمانند.

## رفتار خطا و Transaction

فرم یک `DataContext` می‌سازد، `CreateDist` را صدا می‌زند، `ErrMsg` را به
Validation Failure تبدیل می‌کند و فقط در نتیجهٔ معتبر `Commit` می‌زند.
خود Stored Procedure `BEGIN TRAN` صریح ندارد؛ بنابراین مالکیت دقیق Transaction
در Framework/DataContext است و بدون آزمون Fault نمی‌توان جزئیات Rollback را قطعی
دانست. در نسخهٔ وب، Command باید Transaction را صریحاً مالک باشد و خطای اعتبارسنجی
قبل از Commit کل واحد کار را رد کند.

## شواهد سه‌ماهه

در بازهٔ `۱۴۰۵/۰۳/۰۱` تا `۱۴۰۵/۰۵/۳۱` تعداد ۳٬۳۷۹ Distribution جاری ثبت شده
است. گزارش ماهانه در Artifact بر حسب کد، وضعیت و شمارش ناشناس تیم ذخیره شده است.
این Snapshot وضعیت فعلی Headerهاست و Event log انتقال وضعیت محسوب نمی‌شود.

## محدودیت‌ها

- Clone مقدار تنظیمات فعلی را ثابت می‌کند، نه تمام تنظیمات تاریخی را؛
- IL شکل Branch قابل اجرا را ثابت می‌کند، نه Branch واقعی تک‌تک ردیف‌های قدیمی؛
- نام انسانی کدها در مسترهای فعلی وجود ندارد؛
- Aggregate مجوزها هویت هیچ کاربر خاصی را اثبات نمی‌کند؛
- هیچ فرم، SP یا Command عملیاتی اجرا نشده است.

## بازتولید

```powershell
.\.venv\Scripts\python.exe scripts\sql\extract_varanegar_distribution_path_diagnostic_contract.py `
  --source-directory '\\192.168.1.171\exe\VN.SDS.Container' `
  --output artifacts\varanegar_analysis\ui\varanegar_distribution_path_diagnostic_contract_20260827.json
```

- Artifact: `artifacts/varanegar_analysis/ui/varanegar_distribution_path_diagnostic_contract_20260827.json`
- Extractor: `scripts/sql/extract_varanegar_distribution_path_diagnostic_contract.py`

