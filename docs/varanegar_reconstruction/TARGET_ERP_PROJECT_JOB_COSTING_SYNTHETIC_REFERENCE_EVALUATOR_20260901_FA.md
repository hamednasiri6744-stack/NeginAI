# ارزیاب مصنوعی پروژه و بهایابی کار — ۱۴۰۵/۰۶/۱۰

تابع `varanegar_project_job_costing_reference.py` یک ماشین تصمیم خالص برای عملیات COMMIT، POST_COST، MEASURE، BILL، RECOGNIZE_REVENUE و RECONCILE است. تقدم fail-closed آن schema، دامنه/WBS، version/idempotency، وضعیت commit نامعلوم، unknown مسدودکننده، قواعد هر عملیات و سپس تطبیق است.

مجموعهٔ ثابت شامل ۲۴ بردار (۶ مثبت و ۱۸ منفی) است و نتیجهٔ هر بردار expected/actual ثبت می‌شود. این ارزیاب به پایگاه داده، شبکه، assembly یا دادهٔ واقعی دسترسی ندارد و گواه runtime یا صحت حسابداری/قراردادی مشتری نیست.
