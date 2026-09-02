# Call graph لایه‌ای Extensionهای وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۳۲ Capability؛ ۱۴۹ UI→Business، ۴۲ UI→DataAccess و ۱۸۴ Business→DataAccess Edge**

## نتیجهٔ معماری

از ۳۲ Capability، تعداد ۳۱ مورد شاهد Business/IBusiness mediation دارند؛ اما ۱۳
Capability هم‌زمان DataAccess را مستقیم از UI صدا می‌زنند. بنابراین Legacy نه
یک معماری سه‌لایهٔ پاک است و نه CRUD کاملاً مستقیم. ERP وب باید Command/Query
boundary صریح بسازد و هیچ Adapter داده را به Browser/UI منتقل نکند.

## شواهد عددی

- ۱٬۴۰۲ Edge First-party از UI؛
- ۱۴۹ Edge به ۷۳ Type Business/IBusiness با ۲۹۲ Method body؛
- ۴۲ Edge مستقیم UI به DataAccess؛
- ۱۸۴ Edge Business به ۵۸ Type DataAccess با ۸۰۷ Method body؛
- ۳۱ Capability با Business mediation و ۱۳ Capability با Direct DataAccess؛
- صفر Type First-party-like حل‌نشده، صفر Method error و صفر Hash mismatch.

## سیزده Coupling مستقیم UI→DataAccess

- POS: Charge device، Instalment receipt، Barcode print، Safe، Session، Setting،
  Scale و Subscriber group؛
- Report: Dynamic selector؛
- Setting: Accounting article template، General config و Web-service config؛
- VNMembers: Contact selector.

`party.contact_selector` تنها Capability بدون Business mediation صریح است. این
نتیجه استفاده واقعی هر Edge یا Atomicity را ثابت نمی‌کند، اما برای طراحی Target
یک هشدار ساختاری قوی است.

## پیامد برای Command/Query مقصد

- POS Safe/Session/Instalment باید Application service و Scope خزانه/فروش داشته
  باشد؛ QueryHelper یا Adapter در UI ممنوع؛
- General/WebService config باید Policy/Secret service باشد و Secret به UI یا
  Config table خام نرود؛
- Article template به Accounting application service و Approval وصل می‌شود؛
- Report selector فقط از Query registry مجاز و پارامتری استفاده می‌کند؛
- Contact selector Read model Scopeدار است و مالک Contact را دور نمی‌زند؛
- Tablet Business mediation حفظ می‌شود، ولی Concrete legacy handler عیناً
  Service مستقل نمی‌شود؛ Modular monolith first باقی می‌ماند.

## محدودیت

Call graph ایستا Branch اجراشده، Dependency injection concrete type، Transaction
atomicity یا Permission مؤثر را ثابت نمی‌کند. Interface dispatch می‌تواند Concrete
implementation را پنهان کند. Direct DataAccess نیز ممکن است Lookup/Query باشد؛
قبل از Command design باید Method/SQL و Side effect هدفمند Trace شود.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_extension_dependency_graph_20260827.json`
- `scripts/windows/extract_varanegar_extension_dependency_graph.py`
- `tests/test_varanegar_ui_evidence.py`

گام بعدی: انتخاب Couplingهای مادی POS/Setting و Trace تا Method/SQL/Transaction،
بدون اجرای Command.
