# Delta رجیستر ریسک: پوشش مجوز وب NGT

تاریخ: ۲۰۲۶-۰۸-۲۹  
وضعیت: **PASS؛ ریسک باز و Reachability Runtime اثبات‌نشده**

## نتیجه

رجیستر قبلی ۵۶ ریسک را منجمد نگه می‌دارد. خروجی جدید، بدون تغییر Artifact قبلی،
سه ریسک را افزوده است:

```text
R-057: web command route authorization coverage is not mechanically complete
Severity: CRITICAL
Gate: P0_BEFORE_ANY_WEB_COMMAND
Modules: identity_authorization / platform / integration_migration

R-058: ambient admin role bypasses resource/action and standard role authorization
Severity: CRITICAL
Gate: P0_BEFORE_IDENTITY_PROVISIONING_OR_WEB_COMMAND
Modules: identity_authorization / platform

R-059: functional permission scope relies on grant consistency instead of the owner-filtered repository path
Severity: CRITICAL
Gate: P0_BEFORE_IDENTITY_PROVISIONING_OR_WEB_COMMAND
Modules: identity_authorization / platform / integration_migration
```

مبنای ریسک:

- ۷۸۴ Action دارای HTTP/Route attribute؛
- ۶۰ Action بدون اعلان NGT/Standard/Claims/Anonymous؛
- ۳۸ مورد از آن‌ها با فعل تغییردهنده؛
- صفر Constructor نام‌دار Authorization در Global filterهای
  `Startup.ConfigureWebApi`؛
- صفر فراخوانی نام‌دار تصمیم مجوز پس از خواندن Body مستقیم هر ۶۰ مورد و
  `MoveNext` هر ۴۳ Endpoint async، با صفر خطای Body؛
- سه قرارداد Resource/Action بدون Permission row در همه ApplicationOwnerهای
  Snapshot فعلی.
- Branch دقیق Admin قبل از Base authorization مقدار true می‌دهد؛ یک Role Admin،
  سه Assignment و سه Subject فعلی به‌صورت Aggregate و بدون هویت دیده شد.
- Guard مجوز فقط OwnerKey را مصرف می‌کند و همان Key در سازندهٔ تک‌پارامتری سه
  بار پخش می‌شود؛ Direct/Group permission از `GetQuery` خام استفاده می‌کنند، نه
  `GetQueryByOwner/CalcExtraPredict`.
- Snapshot فعلی ۳۲۴ Grant مؤثر و صفر Grant بین Applicationها دارد؛ رخداد
  Cross-tenant ادعا نشده است. ۵۸ Membership در Scope گروه با Scope User متفاوت،
  یک Membership یتیم و یک Default-center هم‌کلید با DataOwner ثبت شد.

Severity اثر بالقوه را بیان می‌کند، نه احتمال. Manual/async Body از نظر
فراخوانی‌های نام‌دار بررسی شد، اما Guard مبهم/واگذارشده، Host policy، Middleware
بیرونی و Reachability Runtime هنوز رد نشده‌اند؛ بنابراین نه Anonymous access و
نه Incident جاری ادعا نشده است.

## کنترل مقصد

- Route manifest اجباری؛ هر Route دقیقاً یک Policy یا Anonymous disposition
  بازبینی‌شده داشته باشد؛
- Middleware fail-closed برای Policy غایب؛
- Permission مستقل برای هر mutation و Data scope؛
- Cross-check ساخت `Route ↔ Permission` در Scope ApplicationOwner؛
- انتقال Manual guardها به Policy مرکزی و Audit تصمیم با نسخه سیاست؛
- Owner hierarchy اجباری، Constraint ضد Grant بین Applicationها و جداسازی
  Group scope از User default scope؛
- تست مستقیم ۳۸ mutation برای رد درخواست پیش از ورود به Handler.

## خروجی‌های ماشین‌خوان

- `artifacts/varanegar_analysis/ui/negin_erp_risk_register_20260829.json`:
  ۶۱ ریسک، ۳۴ بحرانی، ۲۴ بالا، سه متوسط، Validation=PASS؛ `R-060` مربوط به
  مرز زمانی و `R-061` مربوط به تقدم/انتقال تنظیمات بعد از این Delta مجوز است.
- `artifacts/varanegar_analysis/ui/negin_erp_requirements_traceability_20260829.json`:
  ۲۳۹ Assignment، ۶۱ ریسک یکتا، ۱۴/۱۴ ماژول Traced، صفر Command-ready،
  Validation=PASS.

## بازتولید

```powershell
G:\NeginAI\scripts\windows\rebuild_negin_erp_risk_and_traceability.ps1 `
  -IncludeNgtAuthorization
```

این فرمان Offline است و هیچ DB/Network/UI/Command عملیاتی اجرا نمی‌کند؛ ورودی
NGT آن Artifact فقط‌خواندنی و Hash-pinned مرحله قبل است.
