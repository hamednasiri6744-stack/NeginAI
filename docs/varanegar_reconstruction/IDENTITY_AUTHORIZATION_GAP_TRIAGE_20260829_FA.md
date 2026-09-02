# Triage شکاف‌های Identity و Authorization

این Triage بر پایهٔ Metadata و IL ایستای Hash-pinned موجود است. هیچ Endpoint، Login، Grant، Revoke یا Identity operation اجرا نشده و هیچ هویت، Credential یا مقدار Permission خامی ذخیره نشده است.

## Endpoint declaration gaps

۶۰ Endpoint فاقد NGT/Standard/Claims/Anonymous declaration هستند: ۳۱ POST، شش PUT، یک DELETE و ۲۲ GET. از ۳۸ Endpoint تغییردهنده، ۳۰ مورد هیچ Named signal، پنج مورد فقط Authorization data و سه مورد فقط Identity context دارند. در ۲۲ Read endpoint، ۲۱ مورد هیچ Named signal و یک مورد فقط Authorization data دارد. Named authorization decision در هر ۶۰ مورد صفر است.

این نتیجه اثبات anonymous reachability یا Incident نیست؛ Host policy، Middleware خارجی، delegated/obfuscated check و Runtime behavior هنوز بررسی عملی نشده‌اند. بااین‌حال خواندن Permission data یا CurrentUserId به‌تنهایی Enforcement نیست.

## Scope و ساختار Policy

هر ۵۸ Scope mismatch مشاهده‌شده از کلاس `membership_user_scope_mismatch` است؛ به سایر ابعاد Scope تعمیم داده نمی‌شود. یک Orphan membership user و یک Cross-type owner-key collision نیز جدا باقی مانده‌اند. Permission repository owner-filtered نیست، Admin role مسیر Base authorization را Short-circuit می‌کند و سه Resource/Action mapping در هیچ ApplicationOwner موجود نیستند؛ مورد آخر Fail-closed availability/configuration gap است، نه Grant.

## هفت Lane پذیرش

هفت Lane برای Mutating endpoints، Scope mismatches، Read endpoints، سه mapping مفقود، Admin policy، Owner-filtered repository و شانزده Identity navigation route تعریف شد. مجموع واحدها ۱۳۹ است؛ disposition و آزمون deny/no-leak هر Endpoint یک واحد مرکب‌اند و دوباره‌شماری نمی‌شوند. Endpoint فقط با یکی از وضعیت‌های «Protected با receipt»، «Anonymous صریح و تصویب‌شده»، «Removed/unroutable اثبات‌شده» یا «Rejected incomplete» تعیین تکلیف می‌شود.

۱۸۴ Role UAT case موجود همچنان طراحی‌اند و Approval مالک صفر است. Snapshot فعلی: پذیرش ۰/۱۳۹، Runtime authorization و Security approval صفر، CG-01 باز و Command/Pilot readiness صفر؛ پایهٔ ۸۴/۳۴۳ ثابت است.
