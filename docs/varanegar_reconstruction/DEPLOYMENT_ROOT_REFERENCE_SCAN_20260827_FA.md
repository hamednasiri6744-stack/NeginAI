# اسکن کامل بستهٔ استقرار برای Entry pointهای حل‌نشده — ۱۴۰۵/۰۶/۰۵

## نتیجه

سه فرم Root زیر پس از اسکن دقیق ۶۲ اسمبلی فعال هنوز launcher نداشتند:

- `TreasuryOld.Forms.frmBankReconciliationList`
- `TreasuryOld.Forms.frmReconciliationSetup`
- `VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict`

برای بستن احتمال Plugin، فایل غیرفعال یا پیکربندی بیرون از Inventory، تمام ۸۵۳
فایل منتخب بستهٔ استقرار با پسوندهای DLL، EXE، Disable، Config، XML، Manifest،
TXT و RESX فقط برای سه نام کامل/کوتاه allowlist‌شده اسکن شد. حجم خوانده‌شده
۵۹۸٬۵۵۸٬۴۳۱ بایت و خطای خواندن صفر بود.

هیچ reference بیرونی مشاهده نشد. Matchها فقط در چهار فایل بودند:

- اسمبلی تعریف‌کنندهٔ فعال `TreasuryOld.Forms.dll` و کپی غیرفعال همان؛
- اسمبلی تعریف‌کنندهٔ فعال `VN.SDS.MainData.UI.dll` و کپی غیرفعال همان.

فایل‌های `.disable` به‌درستی «کپی غیرفعال اسمبلی هدف» طبقه‌بندی شدند، نه launcher خارجی.

## معنای این شاهد

این نتیجه احتمال launcher استاتیک در Plugin/Config/Manifest بستهٔ فعلی را بسیار
کم می‌کند، اما ثابت نمی‌کند فرم‌ها مرده‌اند. هنوز این مسیرها بازند:

- نام فشرده/رمز‌شده یا ساخته‌شده در Runtime؛
- route ذخیره‌شده در دادهٔ محیطی دیگری غیر از Clone؛
- invocation از ماژول خارج از بستهٔ فعلی؛
- فرم قدیمی/غیرفعال که فقط با مسیر عملیاتی خاص ظاهر می‌شود.

بنابراین وضعیت هر سه Root همچنان `unresolved` است. حذف از Scope، ساخت route حدسی
یا اعطای Capability مقصد مجاز نیست. برای بستن نهایی باید یا شاهد Runtime
فقط‌خواندنی/مالک کسب‌وکار ارائه شود یا در Release واقعی absence با telemetry امن
و sign-off تأیید شود.

## ایمنی و محدودیت

- هیچ فایل/assembly بارگذاری یا اجرا نشد؛ فقط byte signature دقیق خوانده شد.
- متن فایل، surrounding string، credential و connection string ذخیره نشد.
- هیچ UI action، اتصال دیتابیس، network write یا command برنامه اجرا نشد.
- نبود signature دقیق، نام dynamic/compressed/encrypted را رد نمی‌کند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_deployment_root_reference_scan_20260827.json`
- `scripts/windows/extract_varanegar_deployment_root_reference_scan.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_deployment_root_reference_scan.py `
  --source-directory "\\192.168.1.171\exe\VN.SDS.Container" `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_deployment_root_reference_scan_20260827.json
```

وضعیت Artifact: `PASS`؛ ۸۵۳/۸۵۳ فایل خوانده شد، خطا و reference بیرونی هر دو صفر.
