# مرز ایستای Save و Cancel در Manual Voucher — ۱۴۰۵/۰۶/۰۷

`InternalCancelCommand` فرمان لغو مالی نیست. IL ثبت‌شده و hash-pinned آن فقط سه instruction و یک فراخوانی `Form.Close` دارد؛ هیچ Business، DataContext، Adapter، SQL یا mutation دیده نمی‌شود. بنابراین candidate قبلی `accounting.manual_voucher.cancel` رد می‌شود و ERP مقصد نباید از روی دکمهٔ بستن فرم، API لغو یا reversal بسازد.

`SaveCommand` مسیر واقعی persistence است: `ManualVoucherHandler.GetInstance` و generic `TypeSpecRow.SaveCommand` را صدا می‌زند و DataContext می‌سازد، اما در خود متد Commit/Rollback محلی دیده نمی‌شود. Adapter، Procedure، mutation set و transaction owner دقیق پشت generic path هنوز باید resolve شوند.

این اصلاح از artifact IL موجود انجام شد؛ Assembly Load/Execute نشد و هیچ فرم یا فرمانی اجرا نشد.
