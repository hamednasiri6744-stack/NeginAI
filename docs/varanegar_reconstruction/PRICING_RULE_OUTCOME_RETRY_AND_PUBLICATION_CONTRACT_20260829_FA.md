# قرارداد نتیجه، Retry و انتشار قواعد قیمت‌گذاری — ۲۰۲۶۰۸۲۹

این موج هفت قرارداد مقصد را برای ذخیره/بستن قیمت زمینه‌ای، تغییر اولویت، ذخیره/بستن تخفیف، اعتبارسنجی شرط و تخصیص و ثبت Linear Discount تعریف می‌کند. چهار فرمان Save/Delete موجود از ۶۴ Golden Case قبلی دوباره استفاده می‌کنند؛ مسیرهای جدید به‌صورت Delta آزموده می‌شوند.

## نتیجهٔ قطعی شناخت

- UI قیمت و تخفیف مسیرهای Save/Delete دارد؛ دو متد UI مالک `DataContext.Commit` دیده شده‌اند، اما این مالکیت برای معماری مقصد پذیرفته نیست.
- مجوزهای New/Edit/Delete/View از Snapshot نشست و Toolbar می‌آیند؛ مقصد باید در Application Service، deny-first و با Scope جاری دوباره مجوز را بررسی کند.
- شرط پیشرفته در Legacy به `SqlCondition` و اجرای پویا می‌رسد. مقصد فقط AST/DSL نسخه‌دار و Allowlist‌شده را می‌پذیرد؛ متن SQL اجرایی ذخیره نمی‌شود.
- `GenerateLinearDiscountId` از `MAX(Id)+1` استفاده می‌کند. مقصد باید تخصیص اتمیک با Sequence/Identity/UUID یا هم‌ارز و Unique constraint داشته باشد.
- انتشار محلی، Audit و Outbox یک تراکنش‌اند؛ انتقال به مراکز Async است و Receipt پایدار، ترتیب، احراز اصالت Package، Deadline و Quarantine لازم دارد.

## چرخهٔ عمر و Retry

چرخهٔ مقصد `DRAFT → VALIDATED → PUBLISHED → CLOSED` است. Copy فقط Draft جدید با هویت و Version مستقل می‌سازد. قاعدهٔ Published یا استفاده‌شده حذف فیزیکی نمی‌شود و Explain/Calculation provenance آن باقی می‌ماند. `CommandId + PayloadHash + ExpectedVersion` هویت اجرای فرمان است؛ نتیجهٔ نامعلوم قبل از Retry با Aggregate/Audit/Outbox/Replication receipt خوانده و قرنطینه می‌شود.

اولویت فقط عدد اعشاری مبهم نیست؛ Tuple قطعی شامل Scope specificity، Priority، Version/effective time و Stable tie-breaker است. Validation هیچ اثر کسب‌وکاری ندارد و فقط Compile/Explain receipt نوع‌دار برمی‌گرداند.

## مرز ادعا

این Artifact طراحی مقصد است، نه اثبات پیاده‌سازی یا Runtime parity. هیچ فرم، Query، Stored Procedure، Rule یا Package اجرا نشده و هیچ متن خام Rule، شناسهٔ شخص یا مقدار کسب‌وکاری نگهداری نشده است.
