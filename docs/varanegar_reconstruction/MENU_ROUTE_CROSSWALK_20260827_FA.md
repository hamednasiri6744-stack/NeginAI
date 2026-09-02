# Crosswalk منو، فرم و AccessNode وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **Catalog سراسری Clone + تطبیق یکتای چهار فرم باز**

## مرز ایمنی

فقط Config ثابت `GNR.tblMenuConfig`، `dbo.tblFormInfo` و `dbo.AccessNode` از
Clone `READ_ONLY` خوانده شد. هیچ User/group right، نام کاربر، URL یا داده
عملیاتی خوانده/ذخیره نشد و هیچ Procedure اجرا نشد.

## ساختار Route

```text
MenuConfig (tree/order/caption/container flags)
  -> FormInfo (ClassName/FileName/Resource/OpenReason/ShowModal)
     -> AccessNode (Key/Parent/level/product scope)
        -> runtime UserPermissionS + feature locks
           -> MdiManager.ShowForm
```

شمارش Snapshot:

- ۸۳۶ MenuConfig؛
- ۴۳۳ FormInfo؛
- ۴٬۵۰۶ AccessNode؛
- ۳۹۹ Route دارای FormInfo؛
- ۲۴۱ Route دارای `IsShowInContainer=1`؛
- ۱۷ Route Modal و سه Action menu؛
- ۱۶۰ Route با فرم‌های ۲۹ Assembly هسته تطبیق شد: ۱۵۸ Exact و دو Unique-simple.

۶۷۶ Route تطبیق‌نشده الزاماً خرابی نیست: بخشی Folder/Group است و بخشی به
ماژول‌های Report/Accounting/DirectSales خارج از مجموعه Assembly هسته فعلی
اشاره می‌کند.

## چهار فرم فعال

| عنوان زنده | MenuId | AccessNode/Key | Type مقصد Route |
|---|---:|---|---|
| اقلام انبار | ۱۰۹ | `109 / StockGoods` | `VN.SDS.Stock.UI.StockGoods.FormStockGoods` |
| مدیریت توزیع | ۴۱۲ | `412 / DistManagement` | `VN.SDS.Sales.UI.DistManagement.FormDistManagementList` |
| پیگیری چکهای دریافتنی | ۲۰۰۱۲ | `42 / RchequeTracking` | `TreasuryOld.Forms.frmRChequeTracking` |
| پیگیری چکهای پرداختنی | ۲۰۰۱۳ | `43 / PChequeTracking` | `TreasuryOld.Forms.frmPChequeTracking` |

هر چهار Caption بعد از Normalization نویسه‌های فارسی، فقط یک Route داشتند.
این شاهد ابهام Variant چک را حل می‌کند: Route تنظیم‌شده به کلاس قدیمی، نه
`...TrackingNew` اشاره دارد. تا وقتی شاهد Redirect runtime دیده نشده، تحلیل
فرم فعال باید بر Variant قدیمی بنا شود.

## نکات مدل مقصد

1. Route و Permission دو موجودیت جدا هستند؛ MenuConfig به‌تنهایی HasAccess را
   ثابت نمی‌کند.
2. `AccessNodeId` شناسه مهاجرتی/Legacy است؛ کلید پایدار مقصد باید Namespaced
   capability key باشد و Crosswalk شناسه قدیمی را حفظ کند.
3. `FileName` در عمل گاهی Full type و `ClassName` گاهی Simple type یا خالی است؛
   Resolver مقصد باید Contract یکدست داشته باشد و این ناهمگونی را Import کند.
4. `ShowModal`، `OpenReason` و `ResourceId` بخشی از Navigation contract هستند؛
   تبدیل همه صفحات به Route معمولی رفتار را از دست می‌دهد.
5. `IsShow=0` در هر چهار Route فعال دیده شد؛ پس تفسیر ساده «صفر=پنهان» با
   واقعیت Session سازگار نیست. تصمیم نمایش باید از همان Query/Handler runtime و
   Permission tree بازسازی شود، نه از یک ستون منفرد.
6. پوشه‌های منو، Routeهای فرم و Action menu باید در مدل مقصد نوع مجزا داشته
   باشند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_menu_route_catalog_20260827.json`
- `artifacts/varanegar_analysis/ui/varanegar_menu_form_crosswalk_20260827.json`
- `scripts/sql/extract_varanegar_menu_route_catalog.py`
- `scripts/windows/build_varanegar_menu_form_crosswalk.py`

گام بعدی برای «منوی مؤثر کاربر جاری» نیازمند Snapshot مجوز همین Session یا
Role کنترل‌شده است. بدون آن، Catalog سراسری را نباید به‌عنوان منوی مجاز شخص
اعلام کرد.
