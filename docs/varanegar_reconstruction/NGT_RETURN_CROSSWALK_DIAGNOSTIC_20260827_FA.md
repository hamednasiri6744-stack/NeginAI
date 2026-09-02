# تشخیص Crosswalk برگشت موبایلی NGT به RetOrder/RetSale

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **تأیید Aggregate روی Clone فقط‌خواندنی؛ علت تاریخی حذف/ناپدیدشدن هدف اثبات‌نشده**

## نتیجه‌ی اصلاح‌شده

عبارت قبلی «دو NGT Return بدون Crosswalk و در انتظار Integration» بیش از حد
کلی بود. هر دو Header و Line فعال‌اند و هیچ‌کدام در Snapshot جاری به
`SLE.tblRetSale*` وصل نیستند، اما مسیر تاریخی آن‌ها یکسان نیست:

| حالت | تعداد Line | تفسیر مجاز |
|---|---:|---|
| نتیجه‌ی `TourHistory` ندارد | ۱ | `MOBILE_RETURN_PENDING_OR_UNATTEMPTED`؛ Pending، ردشده یا Attempt‌نشده هنوز قابل تفکیک نیست |
| نتیجه‌ی دقیق `TourHistory` دارد ولی RetOrder جاری پیدا نشد | ۱ | `MOBILE_RETURN_HISTORICAL_RESULT_CURRENT_TARGET_MISSING`؛ قبلاً نتیجه و Write-back گرفته، ولی هدف جاری اکنون غایب است |
| Crosswalk جاری به RetOrder | ۰ | هیچ RetOrder فعلی از UUID، Ref یا Number scoped پیدا نشد |
| Crosswalk جاری به RetSale رسمی | ۰ | هیچ سند برگشت مالی/انبار رسمی فعلی اثبات نشد |

برای Line دوم، `TourHistory` هم BackOffice UUID و هم Ref ذخیره‌شده در NGT را
دقیقاً تأیید می‌کند. بنابراین ساخت خودکار یک RetOrder یا RetSale تازه خطر
Duplicate مالی/انبار یا بازسازی نادرست تاریخ را دارد. نبود هدف جاری فقط ثابت
می‌کند Snapshot کنونی آن را ندارد؛ حذف، انتقال، Rollback ناقص یا پردازش در
منبع دیگری بدون Audit معتبر قابل انتخاب نیست.

## دو مدل موبایل که نباید مستقیم Join شوند

- `NGT.CustomerCallReturns.Id` از نوع UUID است و `Number_ID` کاندید پل Legacy؛
- `FRU.CustomerCallReturns.Id` عددی است؛
- FK رسمی `SLE.tblRetOrderHdr.CustomerCallReturnId` و
  `SLE.tblRetSaleHdr.CustomerCallReturnId` به **FRU** اشاره می‌کند، نه NGT؛
- در دو رکورد جاری حتی `NGT.Number_ID → FRU.Id` نیز Match ندارد.

پس Join مستقیم `SLE.CustomerCallReturnId = NGT.Id` هم از نظر Type و هم معنا
غلط است. مدل مقصد باید UUID موبایل، ID مدل FRU، Result تاریخ Replication و
Ref سند BackOffice را نقش‌های مستقل با Provenance نگه دارد.

## مسیر اجرایی و مرز Transaction

۴۱ SQL module به خانواده CustomerCallReturn اشاره می‌کنند. مسیر مادی
`dbo.NGT_DoReplicateTour` به‌صورت استاتیک این ترتیب را نشان می‌دهد:

1. Header/Line/QtyDetail را به Temporary model می‌برد؛
2. `dbo.NGT_ReplicateTour` را داخل Transaction و TRY/CATCH اجرا می‌کند؛
3. Commit انجام می‌شود؛
4. سپس خارج از آن Commit، UUID/Ref/No نتیجه را از `#FinalResult` روی Lineهای
   NGT می‌نویسد.

بنابراین یک Failure window واقعی بین Commit نتیجه BackOffice و Write-back
Crosswalk NGT وجود دارد. این ساختار علت دقیق رکورد فعلی را ثابت نمی‌کند، چون
برای همان رکورد Write-back و `TourHistory` هر دو موجودند؛ اما برای نسخه وب
الزام Idempotency و Reconciliation دوطرفه ایجاد می‌کند.

## مقدار و مبلغ

- جمع Net ردیف‌ها با Net Header در هر دو مورد برابر است؛
- Parent یا QtyDetail یتیم صفر است؛
- `CurrentQty` Line در هر دو مورد با جمع ساده `QtyDetail.Qty` متفاوت است؛
- این اختلاف فعلاً خطا نیست: مسیر deployed مقدار Detail را می‌خواند و چند
  مصرف‌کننده ConvertFactor واحد را نیز دخیل می‌کنند. بدون حل Unit/Package
  نباید `CurrentQty` را بر Detail تحمیل کرد.

## قرارداد تشخیص و مهاجرت

1. ابتدا سلامت Header/Line/Detail، Removed/Cancelled و Version بررسی شود.
2. `TourHistory(EntityUniqueId, Type in 2/12)` قبل از هر Crosswalk ضعیف خوانده شود.
3. UUID، Ref و Number scoped مستقل بررسی و هیچ‌کدام حدسی ادغام نشوند.
4. رکورد دارای نتیجه‌ی تاریخی و هدف غایب در Quarantine حسابرسی قرار گیرد؛
   ساخت خودکار سند ممنوع است.
5. رکورد بدون نتیجه در Pending Integration بماند؛ نبود نتیجه به معنی Reject
   قطعی نیست.
6. Promotion فقط با یک لینک رسمی غیرمبهم، تطبیق Quantity/Net و تأیید مالک مجاز است.
7. مقصد باید Commit نتیجه و ثبت Crosswalk/Outbox را اتمیک یا با Receipt
   idempotent و Reconciliation بازیابی‌پذیر کند.

## ایمنی و محدودیت

- دیتابیس `NeginPakhsh_WebDev` در حالت `READ_ONLY` و حساب `UPDATE=0` بود؛
- هیچ Procedure، فرم یا Assembly اجرا نشد و هیچ ردیفی تغییر نکرد؛
- Artifact فقط Aggregate، نام Object و SHA-256 Definition را نگه می‌دارد؛
- هیچ UUID، شماره سند، مشتری، کاربر، مبلغ یا ردیف خام ذخیره نشده است؛
- وضعیت جاری علت تاریخی ناپدیدشدن RetOrder را اثبات نمی‌کند.

## بازتولید

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_ngt_return_crosswalk_diagnostic_contract.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_ngt_return_crosswalk_diagnostic_contract_20260827.json
```

منابع ماندگار:

- `scripts/sql/extract_varanegar_ngt_return_crosswalk_diagnostic_contract.py`
- `artifacts/varanegar_analysis/ui/varanegar_ngt_return_crosswalk_diagnostic_contract_20260827.json`
