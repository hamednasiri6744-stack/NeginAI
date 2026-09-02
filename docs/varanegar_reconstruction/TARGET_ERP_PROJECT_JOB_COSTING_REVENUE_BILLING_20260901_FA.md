# قرارداد پروژه، بهایابی کار، درآمد و صورتحساب — ۱۴۰۵/۰۶/۱۰

این بسته شکاف P0 چرخهٔ پروژه را در سطح طراحی می‌بندد: دامنه و WBS نسخه‌دار، بودجه و تعهد، هزینهٔ نیروی انسانی/هزینه/مواد/پیمانکار، سربار، پیشرفت، صورتحساب، شناسایی درآمد، تغییر قرارداد و تطبیق زیر‌دفتر پروژه با WIP، حساب دریافتنی، درآمد، هزینه، حاشیه و دفترکل.

## پوشش و کنترل‌ها

- ۱۲ بُعد برای هر ۱۴ ماژول (۱۶۸ تخصیص)، ۱۰ مرحلهٔ چرخه (۱۴۰ تخصیص)، ۱۶ failure case (۲۲۴ تخصیص)، ۲۰ gate (۲۸۰ تخصیص) و ۸ نقش تفکیک‌شده (۱۱۲ تخصیص) تعریف شده است.
- ۲۰ فیلد سیاست، ۱۷ فیلد receipt تراکنش و ۱۸ فیلد receipt تطبیق، نسخهٔ WBS، نرخ، approval، idempotency، شواهد پیشرفت و hashهای کنترل را الزام می‌کنند.
- ارزیاب خالص و مصنوعی ۲۴ بردار ثابت دارد: ۶ مسیر مثبت و ۱۸ مسیر منفی؛ هیچ دادهٔ عملیاتی را نمی‌خواند و هیچ تغییری ایجاد نمی‌کند.

## مرز حقیقت

PASS این بسته فقط سازگاری طراحی و رفتار روی بردارهای مصنوعی را اثبات می‌کند. اتصال به وارانگار، اجرای posting/billing/revenue recognition، انتخاب ارائه‌دهنده، پذیرش مالک کسب‌وکار و آمادگی command/pilot همچنان صفر و اثبات‌نشده‌اند.

## بازتولید

```powershell
.venv\Scripts\python.exe -m pytest -q tests/test_varanegar_project_job_costing_reference.py tests/test_varanegar_target_erp_project_job_costing_revenue_billing_contract.py tests/test_varanegar_target_erp_project_job_costing_revenue_billing_checkpoint.py tests/test_varanegar_target_erp_project_job_costing_synthetic_reference_evaluator_contract.py tests/test_varanegar_target_erp_project_job_costing_synthetic_reference_evaluator_checkpoint.py
```
