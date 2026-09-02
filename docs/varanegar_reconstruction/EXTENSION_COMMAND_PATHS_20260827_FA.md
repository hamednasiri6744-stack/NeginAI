# مسیر Method-level قابلیت‌های مادی Extension وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۱۲ Capability؛ ۲۱۶ مسیر UI، ۸۹ Method کسب‌وکاری حل‌شده و Validation برابر PASS**

## دامنهٔ انتخاب

دوازده قابلیت با ریسک مالی/قواعد/مجوز/Integration/Planning انتخاب شدند:

- POS: Charge device، Instalment method، Linear discount، Safe، Session و Subscriber؛
- Setting: Accounting article template، General config، Stock accounting access و Web service config؛
- Tablet: Dealer-day path و Visit template.

این انتخاب کل ۳۲ Extension نیست؛ Trace هدفمند نقاط مادی است.

## نتیجهٔ Method-level

- ۲۶۵ Method body UI و ۲۱۶ Method دارای Edge First-party؛
- ۵۵ Command candidate، ۴۹ Permission/Validation guard و ۱۱۲ Query/Event/Context؛
- ۱۷۳ occurrence و ۹۰ Edge یکتای UI→Business؛
- ۴۲ occurrence و ۲۶ Edge یکتای UI→DataAccess مستقیم؛
- ۴۲ Business type، ۸۹ Member فراخوانی‌شده و هر ۸۹ Method body حل‌شده؛
- ۱۲۰ occurrence و ۱۰۵ Edge یکتای Business→DataAccess؛
- صفر Method error، صفر Hash mismatch و صفر مسیر Interface-body حل‌نشده.

## نقاط پرتراکم

`authorization.stock_accounting_access` دارای ۳۱ Method path، ۷۵ Business-edge
occurrence، ۱۶ Permission guard candidate و ۹ Command candidate است. این فرم
تنها «تنظیم نمایش» نیست؛ Authorization/Configuration/Inventory/Accounting را
Couple می‌کند.

`pos.charge_device` دارای ۲۴ Method path، ۱۶ Business-edge و ۲۲ Direct-DA
occurrence است. General/WebService config و Article template نیز Direct DA دارند.
این مسیرها نباید به API عمومی CRUD یا Adapter قابل فراخوانی از Browser تبدیل شوند.

Tablet path/templateها Delete/Write/Permission candidate دارند، اما Direct DA
ندارند؛ Business mediation آن‌ها حفظ‌شدنی است، هرچند Concrete Legacy handler
نباید الزاماً Microservice شود.

## Transaction signal

در Methodهای UI منتخب و ۸۹ Business method مستقیم هیچ `Start/Commit/Rollback`
صریح دیده نشد. این نتیجه به معنی «بدون Transaction» نیست؛ Transaction می‌تواند
در Base، DataAccess، ORM، Delegate یا Method عمیق‌تر باشد. اما Atomicity Legacy
از این مسیر اثبات نشده است.

در مقصد، Transaction owner باید Application command صریح باشد و برای هر Stage
Fault injection، Idempotency receipt، Outbox و Reconciliation تعریف شود. نبود
Signal قدیمی مجوز رفتار غیراتمیک نیست.

## محدودیت و تفسیر

Role Methodها از نام Method و Member فراخوانی‌شده استنتاج شده‌اند؛ اجرای واقعی،
Branch و Side effect قطعی نیست. Query/Event می‌تواند در عمق Mutation داشته باشد
و Command candidate می‌تواند فقط UI state را تغییر دهد. Trace SQL/Procedure یا
Data-layer IL برای Commandهای نهایی هنوز لازم است.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_extension_command_paths_20260827.json`
- `scripts/windows/extract_varanegar_extension_command_paths.py`
- `tests/test_varanegar_ui_evidence.py`

گام بعدی: تعریف Command/query contracts برای StockAccess، GeneralConfig،
ChargeDevice، LinearDiscount و Tablet planning با Golden/fault cases مصنوعی.
