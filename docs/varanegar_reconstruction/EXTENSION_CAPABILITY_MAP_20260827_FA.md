# نقشهٔ قابلیت Extensionهای POS، Tablet، Setting و Report وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۳۲ Capability hint، ۳۳ Route association و Validation برابر PASS**

## نتیجه

۳۲ Type خارج از کاتالوگ Core به Capability و ماژول‌های مقصد نگاشت شدند: ۱۳ POS،
۹ Tablet، ۸ Setting، یک Report selector و یک Contact selector. این نگاشت Hint
طراحی است و بدون تأیید مالک کسب‌وکار Scope یا مالکیت نهایی ایجاد نمی‌کند.

## تراکم رفتار

- ۶۰۷ Method body و ۱٬۸۲۸ Call خارجی؛
- ۲۶ Capability دارای ۱۰۳ Method نام‌Write-like؛
- ۱۳ Capability دارای ۱۸ Method نام‌Delete/Reverse-like؛
- ۲۰ Capability دارای ۷۸ Method Validation-like؛
- ۱۳ Capability دارای ۲۵ Method Permission-like؛
- یک Route حل‌نشده (`20037`) و تصمیم Scope خودکار صفر.

نام Methodها Heuristic است. به‌ویژه نبود Permission محلی در بسیاری از POSها
اثبات بی‌مجوز بودن نیست و وجود Write-like اثبات اجرای Write نیست.

## POS

POS نوزده Assignment به Sales و علاوه بر آن Pricing، Master، Treasury،
Configuration، Reporting و Integration دارد. قابلیت‌ها شامل Subscriber/Group،
Safe/Session، Linear discount/Old price/Price-change، Barcode print، Scale،
Charge device، Setting و Instalment method/receipt است.

در مقصد، Subscriber master، Price rule، POS session، Safe/receipt و Device
integration نباید در یک Aggregate «فروش حضوری» ادغام شوند. هر کدام Capability،
Scope و در صورت Write قرارداد Command جدا می‌خواهند.

## Tablet

Tablet دوازده Assignment به Integration، همراه با Master/Sales/Distribution دارد:
Catalog، Product group، Product، Customer، Dealer، Calendar/Visit template،
Visit plan و Dealer-day path. این‌ها نشان می‌دهند Console تبلت هم Master
projection دارد و هم Planning؛ Sync صرف کافی نیست.

برای Product/Customer/Dealer/Path باید Crosswalk، Version/Freshness و Conflict
policy وجود داشته باشد. Methodهای Delete-like در چند List نیز نباید به حذف خام
Master در مقصد ترجمه شوند.

## Setting

Setting به Configuration، Authorization، Organization context، Accounting،
Inventory، Procurement، Reporting و Integration متصل است. `StockAccAccess`
به‌تنهایی ۵۲ Method و ۱۲ Permission-like دارد؛ `GeneralConfig` ده Validation-like
و سه Final-date surface مرزهای Close/Period را نشان می‌دهند.

در مقصد:

- Capability/Scope از Setting value جداست؛
- Final date یک Policy مؤثر و نسخه‌دار است؛
- Web-service secret در Config table/browser قرار نمی‌گیرد؛
- Article template با Posting/Accounting owner و Approval کنترل می‌شود.

## Report و Contact selectors

دو Route روی یک Dynamic report selector Resolve شدند و VNMembers Contact list
به Master data Hint شد. Selectorها لزوماً صفحهٔ مستقل یا مالک داده نیستند؛ Query،
Export/Print و Context باید جدا بررسی شوند.

## Gate مشترک

هر Capability به Owner disposition، Server-side capability/scope، قرارداد
Query/Command، Deny test و برای Write مادی به Idempotency/Reconciliation نیاز
دارد. TypeDef موجود یا Menu visibility هیچ‌یک این Gateها را رد نمی‌کند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_extension_capability_map_20260827.json`
- `scripts/windows/build_varanegar_extension_capability_map.py`
- `tests/test_varanegar_ui_evidence.py`

گام بعدی: استخراج Dependency familyهای این ۳۲ Capability و ساخت قراردادهای
اولویت‌بالای POS/Tablet/Setting، بدون اجرای Command.
