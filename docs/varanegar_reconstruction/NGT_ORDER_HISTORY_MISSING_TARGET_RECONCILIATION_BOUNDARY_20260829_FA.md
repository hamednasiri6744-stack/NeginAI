# مرز تطبیق تاریخچهٔ سفارش NGT با هدف مفقود — ۲۰۲۶-۰۸-۲۹

## نتیجه

Snapshot فقط‌خواندنی نشان می‌دهد `TourHistory(Type=1)` برای ۱٬۱۱۸٬۲۴۴ خط
سفارش وجود دارد. ۱٬۱۱۲٬۷۱۱ تاریخچه با هر دو کلید UUID و Ref به همان سفارش جاری
در `SLE.tblOrderHdr` می‌رسند، اما ۵٬۵۳۳ تاریخچه با هیچ‌کدام از دو کلید هدفی
پیدا نمی‌کنند. حالت UUID-only، Ref-only و تعارض دو کلید همگی صفر است.

این ۵٬۵۳۳ خط به ۱٬۰۲۴ جفت هدف مفقود در ۱٬۰۲۲ سفارش والد تعلق دارند. Crosswalk
جاری خطوط دقیقاً با History برابر است، خطوط و والدها Removed نیستند، والدها
Canceled نیستند و هیچ‌کدام History فروش Type=8 ندارند. این Artifact به‌تنهایی فقط
«هدف جاری مفقود است» را ثابت می‌کرد؛ تطبیق بعدی `GNR.tblLog` در سند Delete Log
ثابت کرد هر ۱٬۰۲۴ Target پس از آخرین History حذف شده است. Procedure و علت تجاری
حذف هنوز معلوم نیست و این شاهد مجوز ساخت دوباره نیست.

## شکل جمعیت مفقود

| شاخص | مقدار |
|---|---:|
| History نوع ۱ | ۱٬۱۱۸٬۲۴۴ |
| هدف حل‌شده با UUID و Ref | ۱٬۱۱۲٬۷۱۱ |
| History با هدف مفقود | ۵٬۵۳۳ |
| جفت هدف مفقود متمایز | ۱٬۰۲۴ |
| سفارش والد درگیر | ۱٬۰۲۲ |
| والد با همهٔ اهداف مفقود | ۱٬۰۲۱ |
| والد Mixed | ۱ |
| خطوط مفقود سه ماه اخیر | ۶۳۴ |
| والدهای درگیر سه ماه اخیر | ۱۱۴ |

والد Mixed شانزده خط دارد: پانزده خط به هدف جاری می‌رسند و یک خط هدف مفقود
دارد. هفت والد Split-target هستند و سه مورد از آن‌ها هم‌زمان Target مفقود دارند.
هیچ هدف مفقودی بین چند والد مشترک نیست و بیشترین تعداد خط برای یک هدف مفقود ۸۷
است.

## Guard و مسیر Runtime

برای `TourHistory.EntityUniqueId` یک Unique index فیلترشدهٔ Type=1 وجود دارد؛ پس
Duplicate History همان خط را محدود می‌کند، اما وجود، حذف یا تطبیق هدف خارجی SLE
را تضمین نمی‌کند.

```text
TourDomain.ReplicateTour
  ├─ NewReplicateTour
  ├─ سپس اولین BeginTransaction مدیریت‌شده
  ├─ Commit میانی
  ├─ BackOfficeOrderUniqueId setter
  ├─ BackOfficeOrderRef setter
  ├─ BackOfficeOrderNo setter
  └─ Commitهای بعدی
```

سه Assembly فقط از طریق PE metadata/IL و بدون Load یا Execute خوانده شد. IL نشان
می‌دهد `NewReplicateTour` پیش از Transaction مدیریت‌شده و پیش از سه setter خط
سفارش است و Commit در دو سوی write-back دیده می‌شود. این ترتیب یک failure window
ساختاری را ثابت می‌کند؛ Reachability شاخه و علت هر Target مفقود فقط با شواهد
حذف/بایگانی و Fault test ایزوله تعیین می‌شود.

## قرارداد مقصد

1. `OrderReplicationAttempt` پایدار با command id و canonical payload hash؛
2. Current crosswalk یکتای نسخه‌دار، جدا از History append-only؛
3. وضعیت صریح Target: موجود، حذف‌شده، بایگانی‌شده، منتقل‌شده یا unresolved؛
4. Outbox/Saga برای ایجاد سفارش و انتشار همهٔ Crosswalkهای خطوط؛
5. Parent-completeness guard تا یک خط مفقود مانع promotion کل والد شود؛
6. Reconciliation مستقل UUID و Ref و قرنطینهٔ neither-match/conflict؛
7. تصمیم اپراتوری مستند برای retain، relink، void یا recreate تأییدشده.

`R-069` با شدت بحرانی افزوده شد. رجیستر فعلی ۶۹ ریسک، ۴۰ بحرانی، ۲۶ بالا،
۲۷۱ اتصال Traceability و صفر ماژول Command-ready دارد.

## Artifactها

- `scripts/sql/extract_varanegar_ngt_order_history_target_boundary.py`
- `scripts/sql/extract_varanegar_ngt_order_history_runtime_boundary.py`
- `artifacts/varanegar_analysis/domains/ngt_order_history_target_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_order_history_runtime_boundary_20260829.json`
- `tests/test_varanegar_ngt_order_history_target_boundary.py`
- `scripts/windows/build_varanegar_ngt_order_history_checkpoint_20260829.py`
- `artifacts/varanegar_analysis/varanegar_ngt_order_history_checkpoint_20260829.json`

## حدود شاهد

- هیچ Stored Procedure، Endpoint، Assembly یا Command عملیاتی اجرا نشد؛
- هیچ UUID، شماره سند، مشتری، مقدار پیکربندی، SQL definition یا ردیف خام ذخیره نشد؛
- بازهٔ اخیر در Artifact برابر June تا August 2026 و صرفاً شمارشی است؛
- این شاهد Target loss را ثابت می‌کند؛ Delete log بعدی حذف پس از History را نیز
  ثابت کرد، اما Procedure/علت و مجاز بودن بازسازی همچنان اثبات نشده است.
