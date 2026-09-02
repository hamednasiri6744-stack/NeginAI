# مدل منبع و مرز Snapshot رسیدهای POS

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS برای Schema Clone؛ داده‌ی عملیاتی POS در Clone قابل ارزیابی نیست**

ریشه‌ی فرمان Legacy سه پارامتر دارد: `@AccYear`، `@AppUserId` و `@PSessionId`.
برای فهم Snapshot منبع، کاتالوگ ۱۳ جدول مستقیم POS در Clone فقط‌خواندنی استخراج
شد؛ هیچ ردیف کسب‌وکاری، Definition یا Trigger body در Artifact ذخیره نشده است.

## نتیجه‌ی ساختاری

- ۱۳ جدول، ۳۰۹ ستون و ۱۷ کلید Primary/Unique؛
- ۸۹ رابطه‌ی FK که ۶۱ مورد `not trusted` هستند؛
- ۱۰ FK بین خود جدول‌های این Slice که ۷ مورد `not trusted` هستند؛
- ۵۱ Trigger فعال؛
- هیچ جدول دارای signal آشکار `rowversion/timestamp/version` نیست؛
- ۳۷ ستون `money` و یک ستون `float` دیده شد؛ تبدیل Amount باید با Decimal و
  قاعده‌ی Rounding صریح انجام شود.

## زنجیره‌ی اصلی

`Safe → PSession → POrder → POrderLine / PPayment`

ارتباط‌های مهم دیگر:

- `BaseChargeDevice → PSession / Safe`؛
- `POrder → Subscriber / RefPOrder`؛
- `POrderXBO` برای Cross-referenceهای Order/Sale/Exit/Distribution/Voucher/Receipt/Pay؛
- `PRetSaleXBO` برای Return-to-order crosswalk؛
- `PCredit` برای Credit وابسته به Order؛
- `tblPayWithPaymentRelation` برای رابطه‌ی Pay/Payment/Return.

هفت FK از ده FK داخلی Slice قابل اعتماد اعلام نشده‌اند. پس Join موفق، نبود
Orphan را اثبات نمی‌کند و Import باید Missing parent، Duplicate key و Crosswalk
ناسازگار را Quarantine کند.

## محدودیت حیاتی Clone

در Snapshot فعلی، ۱۲ جدول POS صفر ردیف و فقط `dbo.Safe` دارای ۳۰ ردیف است. این
یعنی Clone برای شناخت نام فیلد، نوع، کلید، FK و Trigger مناسب است، اما برای سنجش
توزیع واقعی Receipt، نرخ خطا، حجم Session یا رفتار Runtime مناسب نیست.

## قرارداد Snapshot مقصد

هر Snapshot منبع باید این‌ها را تغییرناپذیر نگه دارد:

- شناسه‌ی Snapshot و Extraction watermark؛
- `AccYear/AppUser/PSession` و Scope صندوق؛
- Order، Line، Return line، Payment و Credit با Payload hash؛
- XBO/Crosswalkهای Legacy و Missing-parent diagnostics؛
- Count/Amount control totals قبل و بعد از Import؛
- Provenance هر ردیف بدون نوشتن ACK یا Status به وارانگار.

چون Rowversion آشکار نداریم، `PSessionId` به‌تنهایی کلید Idempotency کافی نیست؛
نسخه‌ی Snapshot و Payload hash نیز الزامی‌اند.

Artifact:
`artifacts/varanegar_analysis/ui/varanegar_pos_source_model_20260827.json`

Extractor:
`scripts/sql/extract_varanegar_pos_source_model.py`

