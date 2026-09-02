# مرز Runtime و مؤثر Owner Scope در NGT — ۲۰۲۶-۰۸-۲۹

## نتیجهٔ اصلی

NGT دو تصمیم جدا دارد که نباید در ERP مقصد یکی شوند:

1. **مجوز قابلیت** (`Resource/Action`)؛
2. **Scope داده** (`ApplicationOwner/DataOwner/DataOwnerCenter`).

در Runtime فعلی، Guard مجوز قابلیت فقط `OwnerKey` را می‌خواند. سازندهٔ
تک‌پارامتری `AuthorizationDomain` همان Key را سه بار به جای
`ApplicationOwnerKey`، `DataOwnerKey` و `DataOwnerCenterKey` می‌فرستد. بااین‌حال
Query مستقیم و گروهی مجوز، `GetQuery` را مصرف می‌کند؛ این Method فقط `DbSet` خام
را برمی‌گرداند. فیلتر Owner در مسیر جداگانهٔ
`GetQueryByOwner → CalcExtraPredict` ساخته می‌شود و سه Repository منتخب مجوز
`GetQuery` را Override نمی‌کنند.

این یک **ریسک ساختاری** است، نه ادعای رخداد جاری: Snapshot فقط‌خواندنی هیچ
`Grant=1` بین Applicationهای متفاوت نشان نداد.

## قرارداد Header و fallback

سه Header کدیِ مجاز و مشاهده‌شده:

- `OwnerKey`؛
- `DataOwnerKey`؛
- `DataOwnerCenterKey`.

هر مقدار با `Guid.Parse` خوانده می‌شود. زنجیرهٔ fallback:

```text
DataOwnerCenterKey missing → DataOwnerKey
DataOwnerKey missing       → OwnerKey
OwnerKey                   → mandatory direct header parse
```

`BaseAnatoliApiController.OwnerInfo` سه Key و `CurrentUserId` را Materialize و
Cache می‌کند. `ValidateModelAttribute.OwnerInfo` سه Key را می‌سازد، اما UserId
را در همان شیء قرار نمی‌دهد. وجود Header یا ساخته‌شدن OwnerInfo به‌تنهایی عضویت
کاربر در آن Scope را ثابت نمی‌کند.

در `GetUserId`، اگر Framework Identity یک UserId غیرخالی بدهد، همان Guid پیش از
Lookup نام/ایمیل/تلفن برگردانده می‌شود. فقط fallback مبتنی بر Claim name،
`OwnerKey` و `DataOwnerKey` را به Lookup کاربر می‌دهد؛ `DataOwnerCenterKey` در
آن Lookup نیست. Runtime request و جعل Header اجرا نشده، بنابراین Exploitability
ادعا نمی‌شود.

## قرارداد Repository

### مسیر خام

`BaseAnatoliRepository.GetQuery` تنها `DbSet` را برمی‌گرداند. Direct permission و
Group membership در `AuthorizationDomain` همین Method را صدا می‌زنند.

### مسیر Owner-aware

`AnatoliRepository.GetQueryByOwner`، `CalcExtraPredict` را می‌سازد و با
`Queryable.Where` اعمال می‌کند. Predicate ایستا این مؤلفه‌ها را دارد:

- `ApplicationOwnerId == OwnerInfo.ApplicationOwnerKey`؛
- `DataOwnerId == OwnerInfo.DataOwnerKey`؛
- سیاست `IsRemoved == OwnerInfo.RemovedData ? IsRemoved : false`؛
- اگر Entity، مرکز را Ignore نکند:
  `DataOwnerCenterId == ownerCenterId`؛
- برای Entity متمرکز، `ownerCenterId` از `DataOwnerKey` و برای Entity غیرمتمرکز
  از `DataOwnerCenterKey` می‌آید؛
- `ExtraPredicate` نیز در انتها AND می‌شود.

پس در مقصد، نام Method نباید مبهم باشد. API خام باید داخلی/ممنوع باشد و Query
مجوز همیشه Scope صریح و تست‌شده داشته باشد.

## Snapshot تجمیعی Clone

منبع: `NeginPakhsh_WebDev` با `READ_ONLY`، `can_update=0` و
`db_denydatawriter=1`.

| شاخص | مقدار |
|---|---:|
| Application | ۱ |
| ApplicationOwner | ۱ |
| DataOwner | ۱ |
| DataOwnerCenter | ۲ |
| Principal | ۸۰۷ |
| User | ۷۸۶ |
| UserGroup | ۸ |
| Membership | ۵۹ |
| Permission | ۳۶۹ |
| PrincipalPermission | ۲٬۴۱۷ |
| Grant=1 با زنجیرهٔ Application کامل | ۳۲۴ |
| Grant=1 بین Applicationهای متفاوت | ۰ |
| Group expansion با Permission در Application متفاوت | ۰ |

### نکات Scope

- یک `DataOwnerCenter.Id` با `DataOwner.Id` برابر است و همان DataOwner را Parent
  دارد؛ بنابراین fallback مرکز به DataOwner برای یک مرکز پیش‌فرض معتبر است.
- هیچ `ApplicationOwner.Id == DataOwner.Id` وجود ندارد؛ fallback کامل یک Key در
  هر سه سطح، Hierarchy معتبر نمی‌سازد.
- ۵۸ عضویت با Scope گروه دقیقاً هماهنگ‌اند ولی با Scope کاربر متفاوت‌اند؛ این
  فعلاً قرارداد «عضویت در Scope گروه» تلقی می‌شود، نه فساد داده.
- یک Membership به User فعلی وصل نمی‌شود؛ هویت یا اثر Runtime آن اثبات نشد.
- هر دو Center، `IsActive=0` و `IsRemoved=0` هستند، درحالی‌که ۷۸۶ User، هشت Group
  و ۵۹ Membership به آن‌ها ارجاع دارند. بنابراین `IsActive=0` را نمی‌توان بدون
  تصمیم مالک معادل حذف یا عدم قابلیت استفاده گرفت.

## اثر روی ERP شخصی نگین

مدل مقصد باید حداقل این قراردادها را جدا کند:

- `AuthenticatedPrincipal`؛
- `FunctionalPermission(resource, action)`؛
- `OwnerContext(application_owner, data_owner, center)`؛
- `DirectPermissionGrant` و `GroupPermissionGrant`؛
- `GroupScopeAssignment` مستقل از Scope پیش‌فرض User؛
- `OwnerHierarchyValidation`؛
- `AuthorizationDecision` با Policy version و Reason غیرحساس.

هر Request ابتدا باید Owner hierarchy را با Principal تطبیق دهد، سپس Permission
قابلیت و Data scope را Deny-first ارزیابی کند. Constraint/Command invariant باید
ساخت Grant بین Applicationهای متفاوت را رد کند. `admin` نیز همچنان باید به
Break-glass/JIT منتقل شود، نه اینکه این Scopeها را دور بزند.

## ریسک و محدودیت

- `R-059` این مرز را Critical ثبت می‌کند، چون اثر بالقوه Cross-tenant است؛
- Severity به معنی وقوع یا احتمال اثبات‌شده نیست؛
- Snapshot فعلی Cross-Application Grant مؤثر ندارد؛
- هیچ Endpoint، فرم، Stored Procedure عملیاتی یا Assembly اجرا نشده است؛
- هیچ Owner/User/Principal/Group/Permission ID یا Credential ذخیره نشده است؛
- SQL تولیدشدهٔ EF و Runtime request capture نشده‌اند.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/domains/ngt_owner_scope_runtime_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_owner_scope_repository_boundary_20260829.json`
- `artifacts/varanegar_analysis/domains/ngt_owner_scope_effective_boundary_20260829.json`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_ngt_owner_scope_runtime_boundary.py `
  --source-directory "\\192.168.1.171\exe\NGTApp\Server\bin" `
  --authorization-runtime-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_runtime_boundary_20260828.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_owner_scope_runtime_boundary_20260829.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\extract_varanegar_ngt_owner_scope_repository_boundary.py `
  --source-directory "\\192.168.1.171\exe\NGTApp\Server\bin" `
  --runtime-scope-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_owner_scope_runtime_boundary_20260829.json `
  --authorization-runtime-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_authorization_runtime_boundary_20260828.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_owner_scope_repository_boundary_20260829.json

G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_ngt_owner_scope_effective_boundary.py `
  --runtime-scope-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_owner_scope_runtime_boundary_20260829.json `
  --repository-scope-artifact G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_owner_scope_repository_boundary_20260829.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\domains\ngt_owner_scope_effective_boundary_20260829.json
```
