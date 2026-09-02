# قرارداد Command/Query افزونه‌های مادی برای ERP مقصد

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **PASS — طراحی مقصد، نه آمادگی اجرا یا پایلوت**

این سند خروجی Method-level trace افزونه‌های POS، Tablet و Setting را به مرزهای
قابل‌آزمون ERP شخصی نگین تبدیل می‌کند. هیچ Command روی وارانگار، Clone یا
دیتابیس مقصد اجرا نشده است.

## نتیجه اصلی

- ۱۲ Capability مادی بررسی شد.
- ۱۱ Command مقصد طراحی شد: ده مورد با ۵۵ Method فرمانی UI و یک مورد با شاهد
  عمیق `ExecuteNonQuery` و Procedure.
- `pos.safe` فقط Query محدودشده است؛ `pos.session` هم Query مستقل و هم Command
  ارسال/Replication رسید دارد.
- پنج Command از سطحی می‌آیند که در Legacy اتصال مستقیم UI→DataAccess دارد؛
  مقصد حق کپی این Coupling را ندارد.
- Transaction signal صریح در UI و Business methodهای مستقیم منتخب صفر بود؛ این
  نبودن، Atomicity عمیق‌تر Legacy را رد یا اثبات نمی‌کند.

## Commandهای مقصد

| Command | مالک مقصد | Aggregate | شاهد UI |
|---|---|---|---|
| `authorization.publish_stock_accounting_scope_matrix` | identity_authorization | stock_accounting_scope_policy | `CheckAndSaveAccess`، `SaveAccess` و مسیرهای ذخیره Scope |
| `configuration.save_accounting_article_template_version` | accounting | accounting_article_template | `SaveCommand`، `DeleteCommand` و Validation |
| `configuration.publish_general_version` | configuration | general_configuration | `SaveCommand` و Validation |
| `configuration.publish_web_service_version` | configuration | web_service_configuration | `SaveCommand`، `EditCommand` و Validation |
| `pos.save_charge_device` | receivables_treasury | pos_charge_device | `SaveCommand`، `EditCommand`، `DeleteCommand` |
| `pos.save_instalment_method_version` | receivables_treasury | instalment_method | `SaveCommand`، `DeleteCommand` |
| `pos.replicate_session_sales_receipts` | sales | pos_receipt_replication_batch | `POSSessionHandler.Send`، `POSSessionAdapter.Send`، `usp_ReplicateSalesReceipt` |
| `pricing.publish_linear_discount_version` | pricing_rules | linear_discount_rule | `SaveCommand`، `EditCommand`، `DeleteCommand` |
| `party.save_pos_subscriber` | master_data | pos_subscriber | `SaveCommand`، `DeleteCommand` |
| `distribution.publish_dealer_day_path_version` | distribution | dealer_day_path | `InternalEditCommand`، `DeleteDealerPath` |
| `distribution.publish_visit_template_version` | distribution | visit_template | `InternalEditCommand`، `InternalInsertToExcelCommand`، `Delete` |

تمام Commandها باید Envelope شامل `command_id`، `correlation_id`،
`aggregate_id`، `expected_version`، Actor/Organization context و تاریخ عملیاتی
داشته باشند. تکرار همان `command_id` با Payload یکسان باید همان نتیجه نخست را
برگرداند؛ Payload متفاوت با همان شناسه باید رد شود.

## Queryهای عمداً فقط‌خواندنی

### `pos.read_scoped_safes`

Projection صندوق‌های POS را فقط در Scope کاربر، سازمان و عملیات می‌خواند.
نمایش مانده حساس Capability جدا می‌خواهد و خود Query مجوز تغییر یا تسویه ندارد.

### `pos.read_scoped_sessions`

خلاصه نشست‌های POS را با Safe، تاریخ عملیاتی، واحد پول و وضعیت Reconciliation
می‌خواند. خود Query بدون Mutation است؛ Command مستقل Replication رسید، Scope و
Idempotency جدا دارد.

## مرزهای اجباری پیاده‌سازی

1. یک Application service مالک Atomic transaction شامل append Aggregate، حرکت
   current pointer و transactional outbox است.
2. اثر میان‌ماژولی با consumer دارای Idempotency انجام می‌شود؛ Dual write میان
   دیتابیس/سرویس پذیرفته نیست.
3. تاریخچه immutable است؛ Edit، Retirement و Rollback با Version/Transition
   جدید ثبت می‌شوند.
4. Scope مجوز داخل Application service و در زمان Command دوباره کنترل می‌شود؛
   Menu visibility مجوز نیست.
5. Web-service secret فقط با Vault handle وارد قرارداد می‌شود و هرگز در Log،
   Result یا Artifact قرار نمی‌گیرد.
6. هر failure stage اعلام‌شده باید تست crash/retry/duplicate/reconciliation داشته
   باشد.

## محدودیت شاهد

- نقش Methodها و Callها از IL استاتیک به دست آمده و ترتیب Runtime را ثابت نمی‌کند.
- Field و Scope نهایی، مالکیت و UX به Role UAT و تأیید صاحب فرایند نیاز دارد.
- این سند اجازه نوشتن در وارانگار یا اعلام Command/Pilot-ready بودن نیست.

منبع ماشین‌خوان:
`artifacts/varanegar_analysis/ui/varanegar_extension_target_contracts_20260827.json`

سازنده تکرارپذیر:
`scripts/windows/build_varanegar_extension_target_contracts.py`
