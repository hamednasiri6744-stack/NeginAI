# موجودی Runtime رابط کاربری وارانگار

تاریخ شروع: ۲۰۲۶-۰۸-۲۶، ادامه تا ۰۹:۰۰ روز بعد  
وضعیت: **Snapshot اولیه تأییدشده روی سیستم ۱۹۲٫۱۶۸٫۱٫۱۸۴**

## هدف و مرز

این سند رابط کاربری واقعی وارانگار را به قراردادهای داده‌ای ۱۸ دامنه متصل
می‌کند تا ERP مقصد فقط از روی نام جدول یا ظاهر فرم ساخته نشود. مشاهده با
Windows UI Automation و Win32 window metadata انجام می‌شود و هیچ عملیات
`Invoke`، `SetValue`، `SendKeys`، کلیک، ثبت، حذف، تأیید یا تغییر وضعیت ندارد.

- Process: `VN.SDS.Container.exe`
- مسیر اجرا: `\\192.168.1.171\exe\VN.SDS.Container\VN.SDS.Container.exe`
- سیستم مشاهده: `192.168.1.184`
- Artifact:
  `artifacts/varanegar_analysis/ui/varanegar_ui_inventory_20260827.json`
- Extractor:
  `scripts/windows/extract_varanegar_ui_inventory.ps1`
- برچسب‌های مجاز:
  `scripts/windows/varanegar_ui_safe_labels.json`

نام‌های Data-bound، تاریخ، مبلغ، شناسه و متن آزاد در Artifact ذخیره نمی‌شوند؛
فقط طول و SHA-256 آن‌ها ثبت می‌شود. عنوان و Label فقط با Allowlist دقیق UTF-8
قابل ذخیره است.

## Snapshot اولیه

- یک پنجره اصلی و ۷۶ Automation element مشاهده شد؛
- مسیر Win32 تعداد ۸۵ Child window/control را بدون ارسال Message خواند؛
- چهار فرم تجاری فعال در همان Session دیده شد:
  - `اقلام انبار`؛
  - `پيگيري چکهاي دريافتني`؛
  - `پيگيري چکهاي پرداختني`؛
  - `مديريت توزيع`.

این فهرست «کل منوهای وارانگار» نیست؛ فقط پنجره‌هایی است که در Snapshot فعلی
باز بوده‌اند.

## قرارداد UI چک دریافتی و پرداختنی

دو فرم پیگیری ساختار مشترک زیر را دارند:

```text
فهرست/انتخاب چک
  -> تاریخ پیگیری
  -> تغییر به وضعیت
  -> تعداد انتخابی
  -> مبلغ تجمیعی
  -> توضیحات
  -> تغییر وضعیت
```

در هر دو فرم، کنترل `تغيير وضعيت` در Snapshot مرئی ولی غیرفعال است؛ این با
Guard «ابتدا انتخاب رکورد» سازگار است. فرم چک دریافتی علاوه بر آن کنترل
`محل چک برگشتی` را دارد که فعلاً غیرفعال است و یک Context مخفی `نزد بانک`
دیده شد. فعال‌شدن شرطی این دو کنترل باید در Snapshotهای بعدی و بدون اجرای
Transition بررسی شود.

تطبیق داده‌ای:

| فرم | دامنه مرجع | State source | قرارداد مقصد |
|---|---:|---|---|
| پیگیری چک دریافتی | ۱۲ | `Acc.tblChqHist.IsLast=1` + Workflow ۱۸ انتقالی | Event append-only + Context شرطی + selection guard |
| پیگیری چک پرداختنی | ۱۴ | `PCheque.PChequeHistoryId` + `PChequeHistory` | Event append-only + current pointer + selection guard |

شباهت ظاهری دو فرم مجوز یکی‌کردن State machine آن‌ها نیست. چک دریافتی وضعیت
میانی انتقال صندوق، واگذاری، برگشتی و حقوقی دارد؛ چک پرداختنی Workflow جداگانه
صادره/پرداختنی/پرداخت/عودت/ابطال را مصرف می‌کند.

## اقلام انبار و مدیریت توزیع

`اقلام انبار` به دامنه‌های ۴ و ۸ متصل است. تحلیل IL هدفمند بعدی مشخص کرد
`FormStockGoods.LoadInitData` از
`StockGoodsUIHelper.StockGoodsGridServerModeDC` و مدل
`GNR.vwStockGoods_serverMode` استفاده می‌کند؛ پس Grid یک Projection موجودی به تفکیک
سال مالی و انبار است، نه Master کالا به‌تنهایی. جزئیات در
`DOTNET_RUNTIME_ARCHITECTURE_20260827_FA.md` ثبت شده است.

`مديريت توزيع` به دامنه ۹ و کلاس `FormDistManagementList` متصل است. Call graph
Commandهای Create/Exit/Follow/Reverse/Revoke/RemoveExit/Free را جدا نشان می‌دهد.
مدل مقصد باید ماشین حالت، تاریخچه تخصیص Sale، خروج انبار و تیم توزیع را جدا
نگه دارد؛ وجود یک فرم واحد دلیل ادغام این Aggregateها نیست.

## Golden Caseهای UI لازم

1. بازشدن هر فرم و ثبت فقط عنوان/نوع کنترل بدون داده ردیف؛
2. انتخاب صفر ردیف و تأیید غیرفعال‌بودن Command؛
3. انتخاب یک ردیف ماسک‌شده و مشاهده Enable/Context بدون اجرای Command؛
4. مقایسه گزینه‌های وضعیت با Master/Workflow همان دامنه؛
5. بررسی Role دیگر و ثبت تفاوت Visibility/Enablement؛
6. بستن فرم بدون تغییر و تأیید نبود Write در Audit/SQL.

## ابهام‌های باز

1. نام SQL View/Procedure نهایی پشت Handlerهای چهار فرم؛
2. ترتیب و شرط فعال‌شدن Context «نزد بانک» و «محل چک برگشتی»؛
3. تفاوت Permission نمایش فرم با Permission اجرای Transition؛
4. ستون‌ها، فیلترها و Export گزارش بدون ذخیره مقدارهای PII؛
5. وضعیت MDI فرم‌های باز در برابر منوی کامل مجاز کاربر جاری.

Crosswalk بعدی Route چهار Caption را یکتا حل کرد و نشان داد دو فرم چک فعال از
Variant قدیمی `frmRChequeTracking` و `frmPChequeTracking` می‌آیند. Catalog
سراسری منو ثبت شده، اما منوی مؤثر Role جاری همچنان نیازمند شاهد Session است.

## دستور بازتولید

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File G:\NeginAI\scripts\windows\extract_varanegar_ui_inventory.ps1 `
  -Output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_ui_inventory_20260827.json

G:\NeginAI\.venv\Scripts\python.exe -m pytest `
  G:\NeginAI\tests\test_varanegar_ui_evidence.py -q
```
