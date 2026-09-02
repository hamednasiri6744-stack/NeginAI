# ارزیابی فرم SpecialOptionsDistrict وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **پوسته یا قابلیت پویا و حل‌نشده؛ حذف یا ساخت حدسی مجاز نیست**

## نتیجهٔ روشن

پنج دسته شاهد مستقل برای
`VN.SDS.MainData.UI.SpecialOptionsDistrict.FormSpecialOptionsDistrict` هم‌راستا
شدند:

- کلاس فقط سه Method استاندارد `.ctor/Dispose/InitializeComponent` دارد؛
- Business method و Field مستقیم آن صفر است؛
- ۸۸ Field مشاهده‌شده فقط از Base framework می‌آید؛
- Route ثابت و Launcher/Reference بیرونی در اسکن ۶۲ Assembly صفر است؛
- نام کامل یا کوتاه فرم در String طولانی‌تر/assembly-qualified نیز در ۸۱٬۴۷۳
  Method body صفر بود؛
- چهار الگوی محدود نامی `specialoption/districtoption/specialdistrict/districtspecial`
  در نام Object یا Column کاتالوگ Clone صفر Candidate داد.

طبقه‌بندی ماشین‌خوان
`PLACEHOLDER_OR_DYNAMIC_FEATURE_CANDIDATE_UNRESOLVED` است. این شواهد احتمال یک
پوستهٔ متروک/ناتمام را بالا می‌برد، اما Reflection، Resource، Runtime factory،
نام SQL متفاوت یا قابلیت غیرفعال‌شده را رد نمی‌کند.

## تصمیم برای ERP مقصد

- Route، جدول، Command یا Permission مستقل از روی نام فرم ساخته نمی‌شود؛
- فرم هنوز از Scope حذف یا به‌عنوان dead code علامت قطعی نمی‌خورد؛
- Gate بعدی یکی از این دو شاهد است: تأیید مالک کسب‌وکار، یا مشاهدهٔ Launcher و
  DataObject binding در نشست احرازشده و ایزوله؛
- تا آن زمان Backlog آن با عدم‌قطعیت صریح حفظ می‌شود و مانع Foundationهای مستقل
  ERP نیست.

## ایمنی و حدود

- Clone `READ_ONLY` و `CAN_UPDATE=0` بود؛
- فقط `sys.objects/sys.columns/sys.partitions` و Artifactهای Redacted خوانده شد؛
- هیچ ردیف کسب‌وکار، مقدار Config یا Module/Trigger definition ذخیره نشد؛
- هیچ DLL/Form/Command/Procedure/Trigger اجرا نشد؛
- صفر Candidate نامی فقط چهار الگوی انگلیسی محدود را پوشش می‌دهد.

## Artifact و بازتولید

- `artifacts/varanegar_analysis/ui/varanegar_special_options_district_assessment_20260827.json`
- `scripts/sql/extract_varanegar_special_options_district_assessment.py`
- `tests/test_varanegar_ui_evidence.py`

```powershell
G:\NeginAI\.venv\Scripts\python.exe `
  G:\NeginAI\scripts\sql\extract_varanegar_special_options_district_assessment.py `
  --assembly-contracts G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_assembly_contracts_20260827.json `
  --priority-routes G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_priority_gap_routes_20260827.json `
  --call-graph G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_priority_gap_call_graph_20260827.json `
  --root-entrypoints G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_root_entrypoints_20260827.json `
  --declared-fields G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_priority_gap_declared_fields_20260827.json `
  --output G:\NeginAI\artifacts\varanegar_analysis\ui\varanegar_special_options_district_assessment_20260827.json
```
