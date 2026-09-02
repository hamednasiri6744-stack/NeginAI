# تشخیص Fork میان Current pointer و تاریخچه وضعیت سند حسابداری

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ Clone فقط‌خواندنی و SQL رسمی؛ اجرای Command صفر**

## نتیجه

در ۱٬۰۹۴ سند حسابداری، `Voucher.VoucherStatusHistoryId` معتبر و متعلق به همان
سند است، اما آخرین شناسه‌ی History نیست. این اختلاف یک «Rollback سالم» اثبات‌شده
نیست: پس از Pointer فعلی ۱۴٬۹۴۶ رخداد باقی مانده و در ۱٬۰۹۱ سند حداقل یک رخداد
با وضعیت متفاوت وجود دارد. ۱٬۰۹۰ Pointer هنوز رخداد اول سند را انتخاب می‌کنند.

مدل صحیح فعلی:

```text
Current read projection = Voucher.VoucherStatusHistoryId
Later history branch    = unresolved detached events / UNKNOWN_OUTCOME
Migration incident      = CURRENT_POINTER_HISTORY_FORK
```

نه جایگزینی Pointer با `MAX(HistoryId)` امن است و نه حذف رخدادهای بعدی. هر دو
شاخه باید تا تصمیم حسابداری حفظ شوند.

## دامنه عددی

| سنجه | مقدار |
|---|---:|
| سند حسابداری | ۲۰۵٬۹۴۴ |
| رخداد وضعیت | ۳۲۲٬۵۷۶ |
| Pointer نامعتبر/متعلق به سند دیگر | ۰ |
| Pointer غیرآخرین | ۱٬۰۹۴ |
| رخداد بعد از Pointer | ۱۴٬۹۴۶ |
| Fork دارای وضعیت متفاوت | ۱٬۰۹۱ |
| Pointer روی رخداد اول | ۱٬۰۹۰ |
| بیشینه رخداد بعدی برای یک سند | ۲۴۴ |
| رخداد بعدی دارای Comment | ۰ |

هر ۱٬۰۹۴ سند Manual و بدون `ExternalVoucherHeaderId` است. وضعیت فعلی همه ۲
«موقت» است؛ آخرین History در ۱٬۰۸۳ مورد دوباره ۲ و در ۱۱ مورد ۱ «پیش‌نویس» است.
رخدادهای آخر از آوریل ۲۰۲۴ تا مه ۲۰۲۵ پراکنده‌اند و تمرکز اصلی در فوریه ۲۰۲۵
است. این تمرکز علت تاریخی را به‌تنهایی ثابت نمی‌کند.

## قرارداد رسمی و ریسک خطا

- `Voucher2` و `VoucherFast` وضعیت جاری را از Pointer روی Header می‌خوانند؛
- `DoVoucher_SetVoucherNo` اگر Pointer با آخرین History برابر نباشد صریحاً
  خطای «تاریخچه سند بررسی شود» می‌دهد؛ پس اختلاف برای عملیات بی‌اثر نیست؛
- `Get_ChangeVoucherStatus` ابتدا History را Insert و سپس Pointer را Update
  می‌کند؛ هر دو در Transaction محلی قرار دارند؛
- اما CATCH همان Procedure Rollback صریح ندارد. خطا می‌تواند Transaction باز
  با سرنوشت وابسته به Caller/Session باقی بگذارد. این یک Root-cause candidate
  معتبر است، نه اثبات علت هر ۱٬۰۹۴ سابقه؛
- مسیر جدیدتر `Usp_Sdsnet_Voucher_Save` نیز باید جداگانه با Fault injection و
  CAS روی Pointer آزموده شود.

## تصمیم Incident و مهاجرت

1. اختلاف Pointer و MAX باید Incident با کد `CURRENT_POINTER_HISTORY_FORK` باشد.
2. Pointer فعلی به‌عنوان Projection خواندن Legacy حفظ شود.
3. تمام Historyهای بعدی با Branch/Outcome برابر `UNKNOWN_OUTCOME` نگهداری شوند.
4. هیچ Pointer خودکار به MAX منتقل و هیچ History پاک نشود.
5. پیش از فعال‌کردن Posting/Numbering مقصد، حسابدار باید کلاس‌های Fork را
   disposition کند و مانده/شماره/وضعیت را Reconcile کند.
6. Command مقصد باید Insert event، CAS Pointer و اثر شماره‌گذاری را در یک
   Transaction نسخه‌دار و Idempotent انجام دهد.
7. تست اجباری: خطا دقیقاً میان Insert event و Pointer update؛ نتیجه باید Rollback
   کامل و Transaction count صفر باشد.

## سطح اطمینان و محدودیت

- وجود Fork و اندازه آن: **اطمینان بالا؛ Aggregate فقط‌خواندنی**.
- معنای Pointer در Read model و Guard شماره‌گذاری: **اطمینان بالا؛ SQL رسمی**.
- نبود Rollback صریح در CATCH: **اطمینان بالا؛ مسیر Deploy‌شده**.
- علت تاریخی هر Fork: **نامعلوم**؛ ممکن است مسیرهای دیگر، Caller یا Repair نیز
  دخیل بوده باشند.

هیچ شناسه سند، کاربر، Comment، مبلغ یا ردیف خام در Artifact ثبت نشده و هیچ
Procedure، فرم یا Transaction عملیاتی اجرا نشده است.

## بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_voucher_status_pointer_diagnostic_contract.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_voucher_status_pointer_diagnostic_contract_20260827.json
```
