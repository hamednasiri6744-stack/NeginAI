# ماتریس Capability رابط وارانگار برای ERP مقصد

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **مشتق‌شده از UI Snapshot، IL و SQL Clone فقط‌خواندنی**

این ماتریس مرز بین «دیدن صفحه» و «اجرای Command» را ثبت می‌کند. در نسخه وب،
مخفی‌کردن دکمه کافی نیست؛ همان Permission، Context و Validator باید در API نیز
اجرا شود.

## مدل مجوز نهایی

```text
Allowed = MenuNode.HasAccess
          AND CommandPermission
          AND FeatureEntitlement
          AND FiscalYear/DC/DataPartition
          AND OperationDateOpen
          AND CurrentStateAllowsTransition
          AND DomainValidatorPasses
```

سال مالی یا DC با یک Filter ساده برابر نیست. تغییر آن‌ها در وارانگار Session،
تاریخ‌های عملیاتی، منو و فرم‌های وابسته را بازسازی می‌کند. در مقصد نیز Token یا
Server-side session باید Context صریح و قابل Audit داشته باشد.

## ماتریس صفحه و Command

| صفحه/Context | Capability | Permission/Feature | Guardهای لازم در API | Data partition |
|---|---|---|---|---|
| Container | تغییر سال مالی | Session access | معتبر بودن سال و تاریخ‌های عملیاتی | AccYear |
| Container | تغییر DC | Permission tree + MenuConfig + locks | SiteType و Context rebuild | DCRef + SalesOfficeRef |
| اقلام انبار | مشاهده | Menu/Page | Query فقط‌خواندنی | AccYear + StockDCRef |
| اقلام انبار | New/Edit/Delete | `HasPersmission` مستقل | Goods status، Open order/sale، Stock flow | AccYear + DC + StockDC |
| مدیریت توزیع | مشاهده | Menu node | CheckStatus/Where/Sort | AccYear + DC + user context |
| مدیریت توزیع | New/Edit | MenuButtonNew/Edit | OprDate، Sale آزاد، تیم/خودرو، Validator | AccYear + DC |
| مدیریت توزیع | Follow | `ApprovalDist` | وضعیت جاری | AccYear + DC |
| مدیریت توزیع | Follow after voucher | `DistAfterVch2Sale` + Config | `CanFollowDistAfterVch2Sale` | AccYear + DC |
| مدیریت توزیع | Back previous | `BackToOldStatus` | Mode برگشت و وجود Sale/RetSale | AccYear + DC |
| مدیریت توزیع | Issue exit | Config/Page command | Cardex، OprDate، Lock owner/host | AccYear + DC + StockDC |
| مدیریت توزیع | Remove exit | `RemoveExitFromDist` | Reason، LastClosedDate، Status | AccYear + DC |
| مدیریت توزیع | Free/Merge | `FreeDist` | Lock و Goods/Batch validation | DC + StockDC |
| چک دریافتی | Change status | `RchequeTracking.ChangeStatus` | انتخاب، تاریخ باز، Workflow، Reconcile، Context وضعیت | DCFilter + SaleOffice |
| چک دریافتی | Undo | `RchequeTracking.Undo` | آخرین History، Transfer/Cession/Balance | DCFilter |
| چک پرداختنی | Change status | `PChequeTracking.ChangeStatus` | انتخاب، تاریخ باز، Workflow، برگ چک، Pay/Balance | DCFilter + SaleOffice |
| چک پرداختنی | Undo | `PChequeTracking.Undo` | آخرین History و Current pointer | DCFilter |

## نتیجه طراحی API

1. Query endpoint و Command endpoint جدا باشند؛ Work queue چک‌ها گزارش جامع
   نیست و Status filter مخصوص خود را دارد.
2. هر Command نام صریح، Permission key، Expected current version، Idempotency
   key، Business date و Context لازم داشته باشد.
3. Transition از Client ارسال نشود که مستقیماً Status را Update کند؛ سرور باید
   Workflow و Validator را دوباره بخواند و Event بسازد.
4. تغییر DC/سال مالی Cache صفحه‌ها و Query cursorها را باطل کند.
5. Feature flag و Permission دو منبع جدا باقی بمانند تا فعال‌بودن ماژول به معنی
   مجازبودن کاربر نباشد.
6. Audit نتیجه مجوز، Context، Validator و شناسه Event/Procedure projection را
   ثبت کند، بدون ذخیره PII اضافی.

## شواهد و بازتولید

- Artifact:
  `artifacts/varanegar_analysis/ui/varanegar_ui_capability_matrix_20260827.json`
- Builder:
  `scripts/windows/build_varanegar_ui_capability_matrix.py`
- ورودی‌ها: UI inventory، Targeted IL و UI→SQL contract artifact.

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\build_varanegar_ui_capability_matrix.py `
  --ui G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_ui_inventory_20260827.json `
  --il G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_targeted_il_contracts_20260827.json `
  --sql G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_ui_sql_contracts_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_ui_capability_matrix_20260827.json
```

## محدودیت

این ماتریس Permission keyها و Guardهای چهار فرم فعال را پوشش می‌دهد، نه تمام
منوی کاربر جاری. Role دیگری هنوز مشاهده نشده و Variant دقیق old/new فرم چک باز
با عنوان مشترک قطعی نیست. هر دو مورد باید در Golden test کنترل‌شده بعدی پوشش
داده شود، بدون اجرای Command عملیاتی.
