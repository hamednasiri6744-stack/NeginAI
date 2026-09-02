# خط مبنای نسخه و Drift وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۱۷۸ Source؛ Snapshot نهایی پایدار و نتیجهٔ نهایی `NO_SEMANTIC_DRIFT`**

## چرا این Artifact لازم است؟

شناخت یک ERP بدون شناسنامهٔ نسخه قابل اعتماد نیست. اگر DLL، منو، Procedure،
Workflow یا مجوز عوض شود، نتیجه‌ای که امروز درست بوده ممکن است فردا بی‌اعتبار
شود. این Baseline به هر گروه شاهد Hash معنایی مستقل می‌دهد تا تغییر واقعی از
تغییر زمان تولید فایل جدا شود.

## شناسنامهٔ Release مشاهده‌شده

- ۶۲ فایل First-party با مجموع حدود ۳۷ مگابایت؛
- ۶۰ فایل با Version `5.9.0.376`؛
- دو فایل استثنا با Versionهای `1.0.0.0` و `12.0.30723.0`؛
- ۲۹ Assembly تحلیل‌شده، ۴٬۲۸۶ Type و ۳۹٬۷۵۹ Method؛
- Hash فایل اجرایی Process باز روی `192.168.1.184` یک Match دقیق با
  `VN.SDS.Container.exe` در Inventory ۶۲ فایل داشت؛
- ۱۲ قرارداد SQL هدفمند با Signature/Dependency/Definition hash؛
- ۸۳۶ Route سراسری، ۴۴۵ Form candidate و ۴۰ Node مجوز چهار Route فعال؛
- شناسهٔ معنایی کل Baseline در Artifact ماشین‌خوان ثبت می‌شود؛ سند عمداً Hash
  خودارجاعی یا موقت را مرجع نهایی معرفی نمی‌کند.

پوشش جاری شامل مرزهای عمیق خزانه، سفارش→فروش، سند انبار، توزیع→خروج و
فاکتور/برگشت خرید، Screen candidateها، Entry pointهای حسابداری، مشتری/کالا،
تأمین‌کننده، Context، قیمت/تخفیف، مدیریت کاربر/دسترسی، تنظیمات سیستم و تاریخ قطعی
و Snapshotهای ۰۳:۰۰، ۰۵:۴۵، Baseline روش جدید ۰۷:۴۰ و ۰۹:۰۰ است. مدل منبع،
Guard فرمان، فیلدهای فرم‌های مبهم، مرز SQL کاردکس مغایرت بانکی و اسکن reference
کل Deployment، کاتالوگ مجوز، مرز Persistence صورت‌حساب بانکی و تفکیک
Delete/Unmatch/Discard/Cancel، Profile/Parser/Summary/Confirm semantics، Role/UAT،
سه Root و قراردادهای مقصد Profile/Staging/ReadModel/State/Command نیز به Baseline
و Runbook اجرای UAT، بسته درخواست شواهد، Aggregate امن Aliasهای Type و قرارداد
تشخیص Crosswalk برگشت NGT و Reconciliation Component خرید/رسید نیز افزوده
شدند. اجرای نهایی روی همین ۱۷۸ Source باید
`NO_SEMANTIC_DRIFT` و صفر Source تغییرکرده بدهد. Artifactهای مشتق‌شده‌ای
که خودشان به Risk/Drift وابسته‌اند (`requirements_traceability`، Stack decision
و Process atlas) عمداً از ورودی Hash حذف شدند تا چرخهٔ خودارجاعی و Drift کاذب
ایجاد نشود؛ خود آن‌ها در Manifest شبانه Hash و Validation مستقل دارند.

Hash کل به‌تنهایی برای تشخیص علت کافی نیست؛ Artifact هشت گروه مستقل دارد:

1. `runtime_package`: Binary، Metadata و IL هدفمند؛
2. `navigation_surface`: Menu route، Form crosswalk، Form catalog، Route محدود
   هفت Gap اولویت‌بالا، نقشهٔ ۸۳۶ Route به ۳۱ Root/ماژول مقصد و کاتالوگ
   Scope-freeze برای ۲۳۹ Route تطبیق‌نشده و Resolution سراسری ۳۴ Route
   Present-package؛
3. `behavioral_contracts`: Capability، Workflow، Report، قرارداد صفحه، State
   machine، Side effect، SQL contract، IL هر ۱۴۱ فرم Data-entry و Trace عمیق
   دوازده فرم پرتراکم تا Business/DataAccess، ده قرارداد Orchestrator مقصد و
   Call contract Compact تمام ۴۴۲ فرم High-confidence و کاتالوگ Gap هر ۴۴۵
   Candidate، Call graph دقیق هفت Gap اولویت‌بالا و اسکن Entrypoint سه Root در
   تمام ۶۲ فایل .NET، Capability map سی‌ودو Type افزونهٔ POS/Tablet/Setting و
   Trace آن‌ها تا ۷۳ Business و ۵۸ DataAccess type و مسیر Method-level دوازده
   قابلیت مادی، Command/Query و Data-boundary مقصد، Catalog/Anchor/Gap و Semantic
   footprint افزونه‌ها؛
4. `deep_command_boundaries`: Treasury، Order/Sale/Return، Stock voucher،
   Distribution/Exit و Supplier invoice/return تا SQL/Trigger؛
5. `target_verification`: ۹۷۰ Golden case مصنوعی مقصد در گروه‌های Core،
   Orchestrator، Extension، Report، Master، Foundation و مغایرت بانکی؛
6. `authorization_surface`: Node/حقوق تجمیعی و شانزده Route مدیریت
   کاربر/گروه/Scope بدون هویت؛
7. `session_surface`: Snapshotهای فقط‌خواندنی UI ساعت ۰۳:۰۰، ۰۵:۴۵، ۰۷:۴۰ و
   ۰۹:۰۰ همراه با مقایسه‌های روش‌مند؛
8. `reconstruction_bundle`: Manifest ۱۸ دامنه.

## سیاست برخورد با Drift

| گروه تغییر | اقدام الزامی |
|---|---|
| Runtime package | استخراج دوباره Metadata/IL و تست Call graph فرم‌های تحت اثر |
| Navigation | بازسازی Menu/Form/AccessNode crosswalk |
| Behavior/SQL | تعلیق ادعای Parity دامنهٔ تحت اثر تا Review و Golden test |
| Target verification | بازبینی Test plan مقصد؛ Caseها هرگز روی وارانگار اجرا نمی‌شوند |
| Authorization | بازبینی Capability و SoD؛ تغییر تجمیعی هویت شخص را ثابت نمی‌کند |
| Session UI | ابتدا تفکیک تغییر Selection/session از تغییر Release |
| Manifest | تولید مجدد Evidence و PASS شدن همه تست‌ها |

## روش مقایسهٔ بعدی

ابتدا Extractorهای ورودی با همان مرز فقط‌خواندنی دوباره اجرا می‌شوند؛ سپس:

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\windows\build_varanegar_runtime_drift_baseline.py `
  --artifact-root G:\NeginAI\artifacts\varanegar_analysis `
  --previous G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_runtime_drift_baseline_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_runtime_drift_baseline_NEXT.json
```

نتیجه یکی از `NO_SEMANTIC_DRIFT` یا `DRIFT_DETECTED` است و Sourceهای تغییرکرده
را نام می‌برد. زمان تولید Artifact از Hash معنایی حذف شده، ولی Version، Hash
DLL، ساختار Route، قرارداد SQL و محتوای شواهد حفظ می‌شوند.

## مرز ایمنی

Builder کاملاً Offline است و فقط Artifactهای Redacted موجود را می‌خواند؛ هیچ
اتصال دیتابیس، Network share، UI action، Command برنامه یا دادهٔ عملیاتی ندارد.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/varanegar_runtime_drift_baseline_20260827.json`
- `scripts/windows/build_varanegar_runtime_drift_baseline.py`
- `tests/test_varanegar_ui_evidence.py`
