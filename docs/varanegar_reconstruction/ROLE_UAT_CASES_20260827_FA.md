# سناریوهای UAT نقش، Scope و تفکیک وظایف

تاریخ: ۲۰۲۶-۰۸-۲۷  
وضعیت: **۱۸۴ Case مصنوعی؛ تأیید مالک و Provisioning واقعی صفر**

برای ۱۵ Role template و ۴۵ Capability اتمی، سناریوهای زیر ساخته شد:

- ۷۵ Allow case با الزام Context/Scope/Feature/State تازه؛
- ۷۱ Deny-pattern case با تقدم Deny و Explanation امن؛
- ۱۵ Context-invalidation case هنگام تغییر سال، مرکز، انبار، دفتر یا Tenant؛
- ۱۰ SoD case، ۹ Negative scenario عمومی و ۴ Non-inference case؛
- در مجموع ۱۸۴ Case؛ هیچ هویت، Grant جاری یا Assignment تولیدی خوانده/ذخیره نشد.

Templateها موقت‌اند. قبل از Provisioning، مالک کسب‌وکار باید Allow list را تأیید
کند، مسئول امنیت Scope/Deny/Break-glass را امضا کند، مسئول مالی SoDهای مادی را
تأیید کند و UAT احراز هویت‌شده با Readback Audit انجام شود.

Artifact: `artifacts/varanegar_analysis/ui/negin_erp_role_uat_cases_20260827.json`

Builder: `scripts/windows/build_negin_erp_role_uat_cases.py`
