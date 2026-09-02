# کاتالوگ شکاف شواهد فرم‌های وارانگار

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۴۴۵ Candidate طبقه‌بندی شد؛ هفت شکاف با اولویت بالا**

## چرا این سند لازم است؟

پوشش Static بالا نباید با شناخت کامل اشتباه شود. این کاتالوگ برای هر Candidate
معلوم می‌کند Domain، Call، Route یا Permission evidence کجا هنوز ناقص است و چه
شاهدی باید بعداً جمع شود.

## اعداد اصلی

- ۴۴۲ Form با اطمینان بالا و سه Candidate متوسط؛
- ۶۶ فرم بدون Primary domain، شامل ۶۳ فرم High-confidence؛
- ۲۲ فرم High-confidence بدون Call مستقیم First-party؛
- ۱۵۷ فرم دارای Route مستقیم، از آن‌ها ۱۵۳ Route قابل نمایش در Container؛
- ۱۷۹ فرم بدون Route که شکل آن‌ها Child surface محتمل است؛
- ۱۰۹ فرم بدون Route از شکل‌های غیرChild که Entrypoint آن‌ها باید بررسی شود؛
- ۲۷۷ فرم Write-like بدون Permission method محلی؛
- اولویت نهایی: ۷ High، ۱۴۰ Medium و ۲۹۸ Low.

## هفت اولویت بالا

شش مورد در `TreasuryOld` حول Bank reconciliation، Reconciliation/Setup و دو فرم
نام‌مبهم `frmChek`/`frmList` هستند. مورد هفتم
`SpecialOptionsDistrict.FormSpecialOptionsDistrict` است. برای این‌ها باید Parent
launcher، Business/DataAccess owner، Route مخفی و Domain مقصد صریح پیدا شود.

Formهای Login/Logoff/Password، Container/Sample/Test، Report preview و Zoom chart
به‌عنوان Framework/system shell جدا شدند؛ نبود Domain کسب‌وکاری آن‌ها شکاف High
محسوب نشد. HIX/TTAC نیز Integration/compliance طبقه‌بندی شدند و به صف تخصصی خود
رفتند.

## تفسیر Route

نبود Route برای Dialog، Selector، Dual-list و Data-entry معمولاً طبیعی است چون
از Parent باز می‌شوند. حتی در شکل‌های دیگر نیز نبود Route به معنی فرم مرده نیست؛
Action menu، Modal launcher، Feature flag یا Event می‌تواند Entrypoint باشد.

## تفسیر Permission

عدد ۲۷۷ به معنی ۲۷۷ فرم بی‌مجوز نیست. فقط Method مجوز در همان Type دیده نشده؛
Base template، Menu node، Handler یا Server می‌تواند کنترل را انجام دهد. قبل از
فعال شدن هر Command مقصد، مجوز Server-side باید با تست Deny اثبات شود.

## برنامه بستن شکاف

1. Trace Base/Interface/Event برای ۲۲ فرم بدون Call مستقیم؛
2. یافتن Parent launcher و Route برای هفت اولویت بالا؛
3. تعیین Aggregate owner فرم‌های Reconciliation و SpecialOptionsDistrict؛
4. نگاشت HIX/TTAC به Integration/compliance نه Domain عملیاتی اصلی؛
5. بازبینی ۶۳ Unmapped با Call module و Menu semantics، بدون نگاشت حدسی.

## Artifact و کد

- `artifacts/varanegar_analysis/ui/varanegar_form_evidence_gaps_20260827.json`
- `scripts/windows/build_varanegar_form_evidence_gap_catalog.py`
- `tests/test_varanegar_ui_evidence.py`
