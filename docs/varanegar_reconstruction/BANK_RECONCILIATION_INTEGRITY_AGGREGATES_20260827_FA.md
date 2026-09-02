# Snapshot تجمیعی Integrity مغایرت بانکی

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS؛ Clone جاری Fixture Runtime ندارد و شدت Defect قابل‌اندازه‌گیری نیست**

## نتیجهٔ صریح

روی Clone فقط‌خواندنی، شمارش‌های جاری این‌هاست:

| موجودیت | تعداد |
|---|---:|
| Reconcile | ۰ |
| BankBill | ۰ |
| ReconcileItem | ۰ |
| چهار جدول Profile/Column | ۰ |

بنابراین صفر بودن marker ناسازگار، Multi-link یا Instrument flag mismatch در این
Snapshot **به معنی نبود مشکل در Production نیست**؛ فقط یعنی داده‌ای برای اندازه‌گیری
Frequency یا Row parity در Clone جاری وجود ندارد.

## Queryهای Aggregate آماده‌شده

Extractor هیچ ID/Date/Amount/Comment/File/User value ذخیره نمی‌کند و فقط Count/Sum
می‌گیرد:

- markerهای Unconfirmed/Confirmed/Partial و Amount صفر/Null/غیرصفر؛
- Header بدون Bill، Bill بدون Link، Bill/Session چندLinkی؛
- تعداد Referenceهای نوع‌دار صفر/یک/چند در هر Link؛
- برای شش خانواده Instrument: Source گمشده، IsReconciled true/false، Confirmed با
  Instrument false و Unconfirmed با Instrument true.

همهٔ Partitionها با Totalها Cross-check شدند و Validation error صفر است.

## استفادهٔ بعدی

همین Queryها باید روی Snapshot تازه، Redacted، READ_ONLY و موردتأیید مالک اجرا شوند.
هر مقدار غیرصفر در Partial marker، Confirmed/unreconciled، Zero/multiple typed ref یا
Orphan header به Quarantine می‌رود؛ Source Legacy خودکار Repair نمی‌شود.

## مرز ایمنی

- Login دارای `can_update=0` و Deny write است؛
- Stored procedure یا Application command اجرا نشد؛
- خروجی فقط Aggregate است و هیچ Row identifier یا Business value ندارد؛
- این Snapshot ممکن است از Production عقب باشد.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_bank_reconciliation_integrity_aggregates_20260827.json`
- `scripts/sql/extract_varanegar_bank_reconciliation_integrity_aggregates.py`
- `tests/test_varanegar_ui_evidence.py`

نتیجهٔ عملی: برای عبور از Runtime parity gate، دسترسی جدید نوشتنی لازم نیست؛ فقط
یک Clone/Snapshot تازه و فقط‌خواندنی با Fixture واقعی Redacted لازم است.
