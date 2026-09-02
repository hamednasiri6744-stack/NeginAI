# قرارداد Type، Scope و Parity گزارش مرکز تماس (`RPT-06`)

مسیر `CallCenterProductCustomerReport` تا متد DataAccess به‌صورت PE/CLR metadata و
IL ایستا دنبال شد. برخلاف Gap قبلی که صفر Candidate داشت، binding دقیق
`dbo.USP_CallCenter_ProductCustomer_Report` اکنون با چهار پارامتر `AccYear`،
`DCRef`، `UserRef` و `Type` ثبت شده است. Catalog فقط‌خواندنی ۱۰ dependency و ساختار
Branch وابسته به `@Type` را تأیید کرد؛ Procedure اجرا نشد.

دو label رابط کاربری «عملکرد به ریز مشتری» و «فروش به ریز کالا» وجود دو mode را
پشتیبانی می‌کنند، اما mapping عددی/مقداری `Type` عمداً ذخیره یا حدس زده نشده است.
ERP مقصد باید enum تایپ‌شده، mapping نسخه‌دار و رد صریح مقدار ناشناخته داشته باشد.
Customer mode و Product mode دو schema و grain جدا دارند و نباید در یک جدول مبهم
ادغام شوند.

Scope باید deny-first روی سال مالی، DC، کاربر و منابع مشتری اعمال شود. Artifactهای
تشخیصی فقط filter hash و watermark نگه می‌دارند و شناسه/مقدار خام مشتری یا کاربر را
ذخیره نمی‌کنند. اختلاف‌ها ابتدا به تفکیک mode و key-set و سپس visit/order count،
quantity، amount و no-sale/no-visit classification بررسی می‌شوند. تاریخ replication
یا watermark مرکز تماس نیز باید pin شود.

شش Golden Case برای دو mode، Type ناشناخته، منع DC، رویداد بدون فروش و تکرار read
در watermark ثابت ثبت شد. Formula، mapping مقدار Type و Result parity هنوز
اثبات‌نشده‌اند. Risk count برابر ۸۴ و mutation/اجرای عملیاتی صفر است.
