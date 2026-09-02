# قرارداد Snapshot و تاریخ در Organization Context

این بسته طراحی مقصد را از شواهد ایستا می‌سازد و هیچ فرم، فرمان، تغییر تاریخ یا Stored Procedure عملیاتی را اجرا نمی‌کند.

شش فرمان Save/Delete سال عملیاتی، Save/Delete رابطهٔ StockDC، انتشار پنجرهٔ تاریخ و فعال‌سازی ContextSnapshot را پوشش می‌دهند. Snapshot immutable سازمان، سال عملیاتی، سال مالی، DC، دفتر، انبار، پنجرهٔ تاریخ، calendar/timezone policy و نسخهٔ رابطه را برای تمام عمر یک فرمان pin می‌کند.

چهار مفهوم تاریخ جدا هستند: timestamp رخداد، مرز باز/بسته، selector تاریخ سند/Replication و ساعت Server. null یا نبود مرز reject/quarantine می‌شود و از ambient default استفاده نمی‌شود. استثنای نوع سفارش فقط همان open-date check نام‌دار را رد می‌کند، نه دیگر مصرف‌کنندگان تاریخ.

شواهد ۶۴ Golden Case در چهار فرمان، سه فرم و ۴۱ method، ۶۴۳ method منتخب تاریخ، ۱۱ SQL consumer، سه profile با OperationDate تهی و یک profile با OperationDate پس از LastDate را pin می‌کند. permission تغییر تاریخ در server command دوباره ارزیابی نمی‌شود و runtime parity/owner approval صفر است.
