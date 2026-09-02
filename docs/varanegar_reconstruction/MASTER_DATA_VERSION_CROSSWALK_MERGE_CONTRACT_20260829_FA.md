# قرارداد Version، Crosswalk و Merge در Master Data

این بسته فقط از شمارهای تجمیعی و قراردادهای ایستا استفاده می‌کند؛ هیچ PII، barcode، contact، credential یا مقدار خام master خوانده یا ذخیره نشده و هیچ فرمانی اجرا نشده است.

ده فرمان شامل Save/Delete مشتری، کالا و تأمین‌کننده، Save مشترک POS، Quarantine، انتشار Crosswalk و Merge کنترل‌شده است. ۱۱۴ Case قابل reuse دقیقاً از ۶۴ Customer/Goods، ۳۲ Supplier و ۱۸ POS Subscriber تشکیل شده و overlap شناسهٔ Case صفر است.

شباهت barcode/contact/name/route هرگز proof هویت نیست. sentinel در quarantine می‌ماند؛ path code دستی به route master ناموجود join نمی‌شود. Crosswalk namespace و source mode صریح دارد. Merge فقط با تأیید مستقل، reconciliation همهٔ referenceها و redirect event برگشت‌پذیر مجاز است و history یا provenance را حذف نمی‌کند.

شاهد ۱۴۲ ورودی UI، ۶۲ ورودی بدون متن ایستای کافی، پنج method دارای Commit و ۲۶۰۸۶ کد توزیع در mode دستی را pin می‌کند. runtime parity، owner approval، automatic merge و readiness صفرند.
