# اصلاح Inventory فرمان‌های حسابداری — ۱۴۰۵/۰۶/۰۷

Inventory اولیه هفت candidate داشت. پس از resolve ایستای Manual Voucher، یک false candidate حذف شد و شش فرمان/مسیر mutation-capable باقی ماند: چهار External Voucher، یک confirm/unconfirm انبار و یک Manual Voucher Save.

`accounting.manual_voucher.cancel` حذف شد، چون فقط بستن UI است. Save اکنون تا generic `ManualVoucherAdapter/BaseDataV2Adapter` و Commit مسیرهای context-taking resolve شده، ولی branch runtime و effect parity همچنان اثبات‌نشده‌اند.

این correction مرجع authoritative جدید است؛ artifact هفت‌تایی قبلی به‌عنوان تاریخچهٔ استنتاج حفظ می‌شود. در ERP مقصد Manual Cancel تا یافتن یک مسیر reversal واقعی نباید API شود.
