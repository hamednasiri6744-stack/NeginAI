# مرز حذف Target سفارش و Tombstone آگاه از NGT — ۲۰۲۶-۰۸-۲۹

## نتیجه

تحلیل فقط‌خواندنی Catalog نشان داد ۴۰۴ ماژول SQL به `SLE.tblOrderHdr` اشاره
دارند، اما پس از حذف Commentها و String literalها فقط چهار Procedure، حذف مستقیم
و ایستای Header سفارش دارند:

- `dbo.NGT_RollBackTour`
- `dbo.usp_sdsnet_Order_Delete`
- `dbo.USP_sdsnet_UndoUserExtraInfo`
- `SLE.usp_sdsnet_ConfirmFreeInvoice`

فقط مسیر Rollback مخصوص NGT به `TourHistory` هم اشاره می‌کند. سه Procedure دیگر
نه `TourHistory`، نه خطوط سفارش NGT و نه Crosswalkهای `BackOfficeOrder*` را
می‌شناسند. این شاهد Catalog به‌تنهایی Reachability یا اجرای تاریخی آن سه مسیر را
ثابت نمی‌کند. تطبیق Delete log بعدی حذف هر ۱٬۰۲۴ Target مفقود را ثابت کرد، اما
هنوز Procedure دقیق را تعیین نمی‌کند.

## Trigger و Audit

روی Header سفارش سه Trigger فعال DELETE وجود دارد. هیچ‌کدام History یا Crosswalk
NGT را اصلاح نمی‌کند و فقط یک Trigger به `InsertToLog` عمومی Replication اشاره
دارد. جدول:

- Temporal نیست؛
- CDC ندارد؛
- Change Tracking ندارد؛
- History table سیستمی ندارد.

پس Log عمومی Replication تنها سیگنال حذف است و نباید به‌عنوان Tombstone پایدار
و Domain-aware در ERP مقصد استفاده شود.

## قیدهای حذف

دوازده FK فعال به `SLE.tblOrderHdr` ارجاع دارند: یازده `NO_ACTION` و یک
`CASCADE`. همهٔ دوازده `is_not_trusted=1` هستند. این وضعیت حذف را بدون پاک‌سازی
فرزندان تضمین نمی‌کند و هم‌زمان صحت کامل دادهٔ Legacy را هم از روی FK ثابت
نمی‌کند. تنها Caller کاتالوگی مستقیم برای چهار Procedure حذف،
`dbo.usp_sdsnet_Order_Save → dbo.usp_sdsnet_Order_Delete` است؛ نبود Caller
کاتالوگی برای بقیه، فراخوانی Runtime، Dynamic یا Application را رد نمی‌کند.

## قرارداد مقصد

1. `OrderTargetTombstone` append-only با UUID/Ref هدف، علت و actor class؛
2. یک Orchestrator حذف که قبل از Header، Crosswalk فعال NGT را تعیین تکلیف کند؛
3. Outbox حذف/بایگانی/انتقال در همان Commit با Tombstone؛
4. Deny-by-default برای حذف Target دارای Mapping فعال بدون disposition مصوب؛
5. Reconciliation پنج‌حالته: never-created، deleted، archived، relocated، unresolved؛
6. Audit مستقل از Transport log عمومی و سیاست retention آزمون‌پذیر؛
7. Fault test در مرز child cleanup، header delete، tombstone و outbox.

`R-070` با شدت بالا ثبت شد و با Delete log بعدی دقیق‌تر شد. رجیستر فعلی ۷۰ ریسک،
۴۰ بحرانی، ۲۷ بالا، ۲۷۵ اتصال Traceability و صفر ماژول Command-ready دارد.

## Artifactها

- `scripts/sql/extract_varanegar_ngt_order_target_deletion_boundary.py`
- `artifacts/varanegar_analysis/domains/ngt_order_target_deletion_boundary_20260829.json`
- `tests/test_varanegar_ngt_order_target_deletion_boundary.py`
- `scripts/windows/build_varanegar_ngt_order_deletion_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/varanegar_ngt_order_deletion_checkpoint_20260829.json`

## حدود شاهد

- هیچ Procedure، Trigger، Endpoint یا Command اجرایی صدا زده نشد؛
- هیچ SQL definition، ردیف تجاری، شناسه یا مقدار پیکربندی ذخیره نشد؛
- تطبیق متن می‌تواند مسیرهای Dynamic یا Encrypted را جا بیندازد؛
- حذف Targetهای مفقود با Log اثبات شد؛ رابطهٔ علّی با هرکدام از چهار Procedure
  هنوز اثبات نشده است.
