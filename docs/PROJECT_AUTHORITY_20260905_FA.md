# NeginAI Project Authority — 2026-09-05

Status: ACTIVE / USER-CONFIRMED

## Canonical project baseline

از 2026-09-05 فایل `NEGINAI_MASTER_PROJECT_MAP_20260905.md` مرجع Master Baseline برای ادامه پروژه NeginAI است.

این مرجع تعیین می‌کند:
- Product mission و ownership boundary
- معماری هدف و ADRهای پذیرفته‌شده
- Commercialization roadmap و Release Gates
- وضعیت NO-GO / Pilot / Production readiness
- Safety boundaries و Definition of Done
- ترتیب مراحل C0 تا C7

## Authority order

در صورت تعارض، این ترتیب رعایت شود:

1. تصمیم صریح جدید مالک پروژه
2. `NEGINAI_MASTER_PROJECT_MAP_20260905.md` برای Product/Architecture/Commercialization
3. `UIUX_BASELINE_20260905_FA.md` برای UI/UX shell, navigation و feature-preservation
4. `VARANEGAR_SEMANTIC_SOURCE_CHATGPT.md` برای Business Semantics / KPI / Varanegar interpretation
5. منطق رسمی Varanegar (Crystal/RPT/Stored Procedure) طبق سیاست Semantic Reconciliation
6. Live repository/runtime evidence برای وضعیت واقعی implementation
7. Handoffهای قبلی برای history و evidence، مگر اینکه با Baseline جدید reconcile شده باشند
8. inference عمومی

## UI/UX binding

- ظاهر مرجع جدید + تجربه Bottom Navigation به‌عنوان جهت طراحی پذیرفته است.
- تمام Roleها باید Shell ناوبری واحد داشته باشند.
- تفاوت Role فقط در authorization/visibility است، نه شکل کلی navigation.
- هیچ Feature فعلی NeginAI در migration ظاهری حذف نمی‌شود.
- Big-bang frontend rewrite ممنوع است؛ modernization باید incremental و reversible باشد.

## Commercial binding

طبق Master Map، Commercial Production در وضعیت NO-GO است تا Gateهای اجباری بسته شوند.
اولین مسیر اجرایی همچنان C0 است:
Release identity / dirty-tree classification / reproducible baseline.

## Safety

- Varanegar analytics/discovery فقط Read-Only.
- Operational seller/order command path یک boundary جدا و govern شده است و نباید به arbitrary SQL write تبدیل شود.
- هیچ KPI رسمی بدون Semantic Parity پذیرفته نیست.
- هیچ Feature/Gate بدون verification evidence کالل محسوب نمی‌شود.

## Working tree

Primary working tree: `D:\Projects\NeginAI`
Current branch baseline: `dev/hamed`

هر تغییر باید روی همین نسخه برنچ‌شده انجام شود؛ نسخه مادر/شبکه بدون دستور صریح کاربر تغییر نکند.
