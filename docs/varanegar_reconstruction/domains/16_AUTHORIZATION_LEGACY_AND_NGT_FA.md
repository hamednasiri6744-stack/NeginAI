# دامنه ۱۶: مجوزهای Legacy، دامنه داده و RBAC مستقل NGT

تاریخ استخراج: ۲۰۲۶-۰۸-۲۸  
وضعیت: **مدل داده و Guard مستقر NGT تأییدشده؛ Crosswalk دو مدل و پوشش همه Endpointها باز است**

## مرز حریم و منبع

- Extractor: `scripts/sql/extract_varanegar_authorization_domain.py`
- Artifact: `artifacts/varanegar_analysis/domains/authorization_legacy_ngt_20260826.json`
- Runtime extractor: `scripts/windows/extract_varanegar_ngt_authorization_runtime_boundary.py`
- Effective extractor: `scripts/sql/extract_varanegar_ngt_authorization_effective_boundary.py`
- Endpoint extractor: `scripts/windows/extract_varanegar_ngt_authorization_endpoint_coverage.py`
- Manual-guard extractor: `scripts/windows/extract_varanegar_ngt_authorization_manual_guard_boundary.py`
- Role short-circuit extractor: `scripts/windows/extract_varanegar_ngt_authorization_role_short_circuit.py`
- Runtime artifact: `artifacts/varanegar_analysis/domains/ngt_authorization_runtime_boundary_20260828.json`
- Effective artifact: `artifacts/varanegar_analysis/domains/ngt_authorization_effective_boundary_20260828.json`
- Endpoint artifact: `artifacts/varanegar_analysis/domains/ngt_authorization_endpoint_coverage_20260828.json`
- Manual-guard artifact: `artifacts/varanegar_analysis/domains/ngt_authorization_manual_guard_boundary_20260829.json`
- Role short-circuit artifact: `artifacts/varanegar_analysis/domains/ngt_authorization_role_short_circuit_20260829.json`
- ۲۹ جدول، ۶۳۷ FK رسمی، ۸۱۸ Consumer و ۱۱ قرارداد انتخابی بررسی شد.
- Username/Name، Password/Hash، Contact، Token/API key، عضویت فردی و ردیف خام
  Grant در Artifact ذخیره نشده است.

## نتیجه اصلی: سه محور مستقل مجوز وجود دارد

```text
Legacy functional permission
  AppUser/UserGroup
    └─ AccessNode -> AccessValue 0/1/2

Legacy data scope
  DC / SaleOffice / StockDC(operation)
  Customer / Supervisor / Manufacturer / PaymentUsance / OrderType / ...

NGT authorization
  Principal / Role / AtomicPermission / PermissionCatalog
```

این سه محور نباید در یک Role ساده ادغام شوند. کاربر می‌تواند حق یک عملیات را
داشته باشد ولی به DC/انبار/مشتری موردنظر Scope نداشته باشد.

## کاربران و گروه‌های Legacy

بدون ذخیره هویت:

- ۱۴۳ AppUser؛ ۱۴۱ فعال و حذف‌نشده، دو غیرفعال، حذف‌شده صفر؛
- هر ۱۴۳ کاربر Personnel معتبر دارد؛
- هفت Admin؛
- ۲۲ گروه و ۱۵۲ عضویت؛
- ۱۳ کاربر بدون گروه، ۱۱۵ کاربر دقیقاً یک گروه و ۱۵ کاربر چند گروه؛
- بیشینه ۹ گروه برای یک کاربر؛
- Membership یتیم یا تکراری صفر.

پرچم‌های All/Open نیز بخشی از مجوزند:

| پرچم | کاربر |
|---|---:|
| Open همه DC | ۱۳۸ |
| Open همه SaleOffice | ۱۴۱ |
| Open همه StockDC | ۱۲۸ |
| همه Supervisor | ۱۲ |
| همه Personnel | ۰ |
| نمایش همه حساب بانکی | ۱۴۲ |
| نمایش همه صندوق | ۰ |

نبود Row scope همیشه به معنی Deny نیست؛ ابتدا پرچم All/Open باید تفسیر شود.

## AccessNode و سه‌حالته بودن حق

۴٬۵۰۶ AccessNode با ۲۸ Root وجود دارد. کلید همه Nodeها پر و Duplicate sibling
key/name صفر است. ۳٬۸۳۸ Node قابل نمایش، ۳٬۹۷۵ مورد SDS و ۳٬۷۹۶ مورد FRU
هستند.

۱۹ Node به Parent موجود وصل نیستند و باید Quarantine شوند. `LevelOfNode` برای
همه مقدار ۱ دارد و عمق درخت را نشان نمی‌دهد؛ ParentId منبع ساخت Hierarchy است.

توزیع UserRights:

| AccessValue | معنی | ردیف |
|---:|---|---:|
| ۰ | خنثی | ۶۰۲٬۹۲۱ |
| ۱ | اجازه | ۲۲٬۶۷۶ |
| ۲ | عدم دسترسی | ۵۶ |

توزیع UserGroupRights:

| AccessValue | معنی | ردیف |
|---:|---|---:|
| ۰ | خنثی | ۸۶٬۲۲۵ |
| ۱ | اجازه | ۸٬۹۲۳ |
| ۲ | عدم دسترسی | ۲۰ |

Pair تکراری، Ref یتیم و مقدار خارج از ۰/۱/۲ صفر است.

## قرارداد Effective Permission

تابع رسمی `dbo.GetUsersRightsSByAccessNodeId` دقیقاً این ترتیب را اجرا می‌کند:

```text
if IsAdmin: allow
effective = direct_allow OR any_group_allow
if direct_deny OR any_group_deny: deny
neutral does not grant
```

پس Deny هم در User و هم در هر Group بر Allow غلبه می‌کند. در ۶۸۰٬۶۵۸ ترکیب
Membership/Node:

- ۸۵٬۴۸۲ Group allow؛
- ۱۵۲ Group deny؛
- ۹ مورد direct allow + group deny؛
- ۱۳ مورد direct deny + group allow؛
- ۹٬۳۷۰ مورد بدون ردیف direct.

هر ۲۲ تعارض با قانون deny-wins به Deny تبدیل می‌شود. مقصد نباید «نزدیک‌ترین
Role» یا «آخرین رکورد» را انتخاب کند.

پوشش Rights بسیار متراکم ولی یکنواخت نیست: کمینه حقوق مستقیم یک کاربر ۲، بیشینه
۴٬۵۰۶ و میانگین ۴٬۴۰۶ است. Import فقط Allowها بدون Neutral/Deny می‌تواند معنی
نسخه‌های بعدی Node tree را عوض کند؛ Rule version لازم است.

## دامنه داده Legacy

| Scope | User row | Group row |
|---|---:|---:|
| DC | ۷۳ | ۱۴ |
| SaleOffice | ۱۴۸ | ۵۷ |
| StockDC | ۳۹۰ | ۱۲۶ |

Scopeهای تخصصی:

- Customer: ۸۲۷؛
- Stock: ۴۸۵؛
- Supervisor: ۱٬۵۷۹؛
- PaymentUsance: ۳٬۲۹۹؛
- Manufacturer: ۳۷۹؛
- OrderType: ۳۱۰.

StockDC scope خودش شش قابلیت دارد. برای User، Order/Sale/Inventory هرکدام ۱۴۴،
Report تعداد ۱۴۸ و Return/DistributedReturn هرکدام ۳۹۰ Grant دارند. برای Group
این اعداد ۵۷/۵۷/۵۷/۵۷/۱۲۶/۱۲۶ است.

پس Claim عمومی `stock_id in [...]` کافی نیست؛ Scope باید
`(stock, operation)` باشد.

## RBAC مستقل NGT

بدون ذخیره هویت:

- ۷۸۶ User، ۷۸۲ فعال، چهار Removed و همه دارای Principal؛
- ۸۰۷ Principal؛
- هشت UserGroup و ۵۹ عضویت؛
- هشت Role و ۸۸۷ Role assignment؛
- ۳۶۹ Permission، ۵۹ Action و ۴۵۵ Catalog؛
- ۲٬۴۱۷ PrincipalPermission: ۳۲۴ ردیف با جهت ذخیره‌شده ۱ و ۲٬۰۹۳ ردیف با
  جهت ذخیره‌شده ۰؛
- ۲٬۴۱۵ PrincipalCatalog: ۳۲۲ ردیف با جهت ذخیره‌شده ۱ و ۲٬۰۹۳ ردیف با
  جهت ذخیره‌شده ۰.

برچسب قبلی «Grant/Deny» برای این اعداد بیش از شواهد بود. معنی عملی مقدارها را
نباید فقط از نام ستون یا Boolean بودن ViewModel نتیجه گرفت؛ قرارداد Guard مستقر
در بخش بعد تعیین‌کننده است.

همه Permission/Catalog/Principal Refهای اصلی معتبرند. اما مدل Legacy سازگاری
خاصی دارد:

- `UserRoles.IdentityRole_Id` رسمی در هر ۸۸۷ ردیف خالی است؛
- `UserRoles.RoleId` ضمنی برای هر ۸۸۷ ردیف به Role معتبر وصل می‌شود؛
- ۲۳ subject ردیف Role، User نیستند ولی Principal معتبرند؛ یعنی جدول عملاً
  Principal-role نیز مصرف شده است؛
- ۲۱۳ گروه Pair تکراری `(subject,RoleId)` دارد؛
- ۲۸ Pair تکراری `(Principal,Catalog)` وجود دارد، اما جهت Grant/Deny در هر Pair
  یکسان است؛
- Atomic permission pair تکراری صفر.

این ردیف‌های تکراری را نباید قبل از شناخت Application/DataOwner scope حذف کرد.

## قرارداد مؤثر Guard مستقر NGT

هشت اسمبلی سرور مستقر با Metadata و IL به‌صورت Static بررسی شد: ۱۳۴ Type و
۶۸۰ Method کاندید، ۶۷۸ Body خوانده‌شده، بدون خطای Body. هیچ Assembly
Load/Execute نشد و Config، Resource، User string یا Credential خوانده نشد.

مسیر `NGT.WebApi.Classes.AnatoliAuthorizeAttribute.HasWebApiAccess` چنین است:

```text
direct = GetPermissionsForPrincipal(user, resource, action)
group  = GetPermissionsByGroup(user, resource, action)
effective = direct UNION group
if effective is empty: deny
if any effective.Grant == -1: deny
otherwise: allow
```

تفکیک overloadها مهم است. دو متد هم‌نام `GetPermissionsByGroup` وجود دارد؛ Guard
وب overload سه‌پارامتری را صدا می‌زند. این overload برای هر گروه دوباره overload
سه‌پارامتری `GetPermissionsForPrincipal(group, resource, action)` را اجرا می‌کند،
و آن Query پیش از بازگرداندن نتیجه صریحاً `Grant == 1` را فیلتر می‌کند. بنابراین:

- Direct و Group فقط با مقدار ۱ وارد Union مجاز می‌شوند؛
- مقدار ۰ در این Guard «رد صریح» نیست؛ قبل از Union حذف می‌شود؛
- Predicate مقدار `-1` یک Veto پس از Union است، ولی در Snapshot فعلی هیچ ردیف
  Atomic یا Catalog با `-1` یا مقدار خارج از ۰/۱ وجود ندارد؛
- از ۳۲۴ ردیف Atomic مقدار ۱، تعداد ۳۲۲ برای هفت Group و دو ردیف برای دو User
  است؛ هر ۲٬۰۹۳ ردیف مقدار ۰ برای هفت Group است؛
- ۲۷۸ ردیف Group با مقدار ۱ و ۱٬۷۹۲ ردیف Group با مقدار ۰ روی گروهی قرار دارند
  که حداقل یک عضو فعال فعلی دارد؛ اما فقط مقدار ۱ وارد نتیجه Guard می‌شود؛
- Direct/User و Group permission فعلی روی یک `(user, permission)` هم‌پوشانی
  Aggregate ندارند؛ پس تقدم تعارض Direct/Group از داده فعلی قابل مشاهده نیست.

Action ورودی با `,` شکسته، سپس `trim/lower` می‌شود و با نام Action permission
به‌صورت عضویت دقیق `Enumerable.Contains` مقایسه می‌شود؛ تطبیق substring نیست.
Resource نیز با Equality سنجیده می‌شود. پس Attribute چندAction باید به چند
Contract مستقل Normalize شود.

### نقش Catalog در زمان اجرا

Guard وب هیچ فراخوانی Catalog ندارد. مسیر ذخیره‌ی Catalog از
`PermissionCatalogPermissions` ردیف Atomic `PrincipalPermission` می‌سازد و جهت
را کپی می‌کند. در Clone، هر ۲٬۴۱۵ expansion مستقیم Catalog یک Atomic هم‌جهت دارد؛
Missing و Opposite-direction هر دو صفر است. این شاهد برای لینک مستقیم Catalog
است و Recursive parent/child expansion را اثبات نمی‌کند.

نتیجه‌ی طراحی مقصد: Catalog باید ابزار انتخاب/Materialization باشد و تصمیم نهایی
Backend روی Permission اتمیِ نسخه‌دار انجام شود. برای Effect از Enum صریح
`ALLOW/DENY/NEUTRAL` استفاده شود؛ نگاشت `0/1/-1` نباید بدون Golden test وارد
موتور جدید شود.

## پوشش اعلان مجوز Endpointها

Metadata صفت‌های `NGT.WebApi.dll` و ارث‌بری مستقیم از
`Anatoli.Common.WebApi.dll` بدون Load/Execute بررسی شد. دامنه فقط Methodهایی است
که صفت HTTP verb یا Route دارند؛ Actionهای صرفاً convention-based در این شمارش
نیستند:

| مرز اعلان | تعداد Endpoint |
|---|---:|
| کل HTTP/Route-attributed | ۷۸۴ |
| دارای `AnatoliAuthorize` NGT | ۵۹۵ |
| NGT با `Resource+Action` | ۲۵۰ |
| NGT فقط Role/احراز هویت یا خالی | ۳۴۵ |
| Standard Authorize، با احتساب base خارجی | ۹۱ |
| Claims authorize | ۱ |
| AllowAnonymous | ۳۸ |
| بدون NGT/Standard/Claims/Anonymous declaration | ۶۰ |
| از مورد قبل با فعل POST/PUT/PATCH/DELETE | ۳۸ |

در ۳۴۵ مورد Role-only، تعداد ۳۴۴ واقعاً Roles contract دارند؛ یک `hooktest`
صفت NGT کاملاً خالی دارد. صفت خالی به‌تنهایی anonymous bypass را ثابت نمی‌کند،
چون کلاس از Authorize استاندارد ارث می‌برد و احراز هویت پایه هنوز باید سنجیده شود.
`ByPassAuthorization=true` در هیچ Endpoint مشاهده نشد.

`Startup.ConfigureWebApi` مسیرهای Attribute را Register می‌کند و دو Global filter
فقط برای ValidateModel و CatchExceptions می‌سازد؛ Constructor نام‌دار مجوز در
این متد صفر است. بااین‌حال ۶۰ مورد بدون اعلان هنوز «شکاف پوشش Static» هستند، نه
اثبات دسترسی ناشناس.

تحلیل بعدی Body مستقیم هر ۶۰ مورد و `MoveNext` هر ۴۳ Async state machine را با
صفر خطای Body خواند. فراخوانی نام‌دار تصمیم مجوز در هر ۶۰ مورد صفر بود. شش مورد
فقط Authorization/Permission data را می‌خوانند یا تغییر می‌دهند و سه مورد فقط
CurrentUser context مصرف می‌کنند؛ هیچ‌یک به‌عنوان Enforcement شمرده نشد. هنوز
کنترل Obfuscated/delegated، Host policy یا Middleware بیرونی ممکن است وجود داشته
باشد. قبل از ساخت ERP وب، تک‌تک این ۶۰ مورد باید Disposition شوند و CI باید هر
Command تغییردهنده بدون Policy صریح را Fail کند.

### Cross-check قرارداد Resource/Action با Catalog

۲۵۱ اعلان Endpoint پس از شکستن Action چندمقداری به ۱۲۸ زوج یکتا تبدیل شد:

- ۱۰۰ زوج دقیقاً یک Permission row در همه ApplicationOwnerها دارند؛
- ۲۵ زوج چند ردیف دارند که می‌تواند ناشی از Scope مستقل ApplicationOwner باشد و
  Duplicate defect نامیده نشد؛
- سه زوج در هیچ ApplicationOwner وجود ندارند:
  `AreaLayer/View`، `Tours/ConfirmTourReceived` و `Tours/Viewpreview`.

این سه مورد به‌احتمال قوی در Guard Resource/Action نتیجه خالی و Deny می‌دهند، اما
Reachability و پاسخ Runtime اجرا نشده است. مقصد باید Contract registry یکتا در
Scope ApplicationOwner و Build-time cross-check Route↔Permission داشته باشد.

## Short-circuit نقش Admin

`NGT.WebApi.Classes.AnatoliAuthorizeAttribute.IsAuthorized` پیش از فراخوانی Base،
Roleهای CurrentUser را می‌گیرد. Predicate دقیق نقش را `lower()` کرده و با literal
کدی `admin` با Equality مقایسه می‌کند. اگر `Any` برقرار باشد، Branch مقدار
`true` را برمی‌گرداند؛ فقط non-admin به Base می‌رود.

Base به‌ترتیب ByPass صفت جاری/همتا، `HasWebApiAccess` و سپس
`System.Web.Http.AuthorizeAttribute.IsAuthorized` را اجرا می‌کند. پس Admin مسیر
Resource/Action، Unauthorized handler و Authentication/standard-role پایه را
دور می‌زند. Endpoint دارای `ByPassAuthorization=true` فعلی صفر است، اما Admin
short-circuit مستقل از آن است.

Snapshot بدون هویت نشان می‌دهد یک Role دقیق Admin، سه Assignment و سه Subject
منتسب فعلی وجود دارد. این Aggregate سوءاستفاده یا نامناسب‌بودن انتساب را ثابت
نمی‌کند؛ اما مقصد نباید آن را به Role دائمی محیطی تبدیل کند. Superuser باید
Break-glass/JIT، دارای MFA، تأیید دوم، انقضا، Reason، Audit و SoD باشد و حتی برای
فرمان‌های مالی/مجوز/تنظیمات حساس Step-up مستقل داشته باشد.

## قرارداد مدل مقصد

- `Identity` و `PersonnelLink` جدا؛
- `AuthorizationPrincipal` برای User/Group/Service principal؛
- `Role` و `PrincipalRole` با کلید یکتا و Source multiplicity audit؛
- `Permission` اتمی با Resource/Action؛
- `PermissionCatalog` و expansion نسخه‌گذاری‌شده؛
- `PrincipalPermissionEffect` با Allow/Deny و deny-wins؛
- `LegacyAccessNodeCrosswalk` با Parent hierarchy؛
- `DataScopeGrant(principal, scope_type, scope_id, operation)`؛
- `AllScopePolicy` برای Open/ShowAll flags؛
- `AuthorizationDecisionLog` بدون PII حساس؛
- `SourceCrosswalk` مستقل برای Legacy و NGT.

API باید اول functional permission و سپس data scope را بررسی کند. مخفی‌کردن
دکمه در Frontend کنترل امنیتی نیست؛ Backend باید همان Decision را enforce کند.

## Golden Caseهای لازم

1. Admin بدون Node row؛
2. User allow مستقیم؛
3. Group allow بدون direct row؛
4. direct allow + group deny؛
5. direct deny + group allow؛
6. کاربر چندگروهی با یک deny؛
7. Neutral-only؛
8. permission مجاز ولی DC خارج Scope؛
9. StockDC مجاز برای Report ولی غیرمجاز برای Sale؛
10. Open-all با/بدون row محدودکننده؛
11. NGT direct مقدار ۱ و حذف مقدار ۰ پیش از Union؛
12. NGT group مقدار ۱ از overload سه‌پارامتری و رد حالت result-empty؛
13. Veto مقدار `-1` و رفتار نبود این مقدار در Snapshot؛
14. NGT catalog direct-link expansion و Materialization اتمی هم‌جهت؛
15. Principal غیرUser دارای Role؛
16. duplicate role/catalog source rows با نتیجه یکتا؛
17. Node با Parent گمشده در Quarantine.

## ابهام‌های باز

1. Crosswalk رسمی Legacy AccessNode به NGT Permission/Catalog.
2. پوشش Attribute و Guard برای همه Endpointهای NGT؛ تحلیل فعلی Guard اصلی وب را
   و ۷۸۴ Action صفت‌دار را ثابت می‌کند، اما ۶۰ شکاف اعلان، Manual guardهای async،
   Actionهای convention-only و Reachability تک‌تک Routeها باز است.
3. معنای ApplicationOwner/DataOwner برای ۲۱۳ Role pair تکراری.
4. ۱۹ Parent گمشده و اینکه Nodeها هنوز در UI قابل دسترس‌اند یا Legacy orphan.
5. رفتار All/Open در کنار Scope denyهای تخصصی.
6. تفاوت IsActive/IsDeleted و تاریخ Start/End در Login policy واقعی.

## دستور بازتولید

مرز تکمیلی Owner scope، fallback Header، Repository خام/Owner-aware و Cross-check
Aggregate در
`../NGT_OWNER_SCOPE_RUNTIME_AND_EFFECTIVE_BOUNDARY_20260829_FA.md` ثبت شده است.
نتیجهٔ کلیدی آن: Guard قابلیت فقط `OwnerKey` را مصرف می‌کند و Queryهای مجوز از
`GetQuery` خام می‌آیند؛ Snapshot فعلی هیچ Grant مؤثر بین Applicationها ندارد،
اما این ایمنی به سازگاری داده متکی است و در مقصد باید Constraint و Policy صریح
شود (`R-059`).

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_authorization_domain.py `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\authorization_legacy_ngt_20260826.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_ngt_authorization_runtime_boundary.py `
  --source-directory "\\192.168.1.171\exe\NGTApp\Server\bin" `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_runtime_boundary_20260828.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_ngt_authorization_endpoint_coverage.py `
  --assembly "\\192.168.1.171\exe\NGTApp\Server\bin\NGT.WebApi.dll" `
  --base-assembly "\\192.168.1.171\exe\NGTApp\Server\bin\Anatoli.Common.WebApi.dll" `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_endpoint_coverage_20260828.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_ngt_authorization_manual_guard_boundary.py `
  --assembly "\\192.168.1.171\exe\NGTApp\Server\bin\NGT.WebApi.dll" `
  --endpoint-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_endpoint_coverage_20260828.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_manual_guard_boundary_20260829.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_ngt_authorization_role_short_circuit.py `
  --ngt-webapi "\\192.168.1.171\exe\NGTApp\Server\bin\NGT.WebApi.dll" `
  --common-webapi "\\192.168.1.171\exe\NGTApp\Server\bin\Anatoli.Common.WebApi.dll" `
  --endpoint-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_endpoint_coverage_20260828.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_role_short_circuit_20260829.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_ngt_authorization_effective_boundary.py `
  --runtime-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_runtime_boundary_20260828.json `
  --endpoint-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_endpoint_coverage_20260828.json `
  --manual-guard-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_manual_guard_boundary_20260829.json `
  --role-short-circuit-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_role_short_circuit_20260829.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_effective_boundary_20260828.json
```
