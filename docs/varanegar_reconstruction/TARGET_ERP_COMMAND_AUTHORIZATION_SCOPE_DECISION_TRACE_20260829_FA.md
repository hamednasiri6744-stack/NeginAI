# قرارداد Authorization، Scope و Decision Trace فرمان‌های ERP مقصد

## هدف

این بسته ۴۹ فرمان چهارده ماژول را به کنترل server-side و fail-closed متصل می‌کند تا Role name، Route/UI، Admin بودن یا حق تجمیعی Legacy به‌تنهایی Grant مقصد نسازد. هیچ Authentication، Session، Token، Command یا UAT اجرا نشده و هیچ Identity Provider یا Policy Engine انتخاب نشده است.

## پوشش

- دوازده بُعد Authorization برای هر فرمان، یعنی ۵۸۸ انتساب، Principal، Tenant، Context، Fiscal/Operation date، Location، Action، Resource، State، Threshold، SoD، Policy freshness و Repository enforcement را پوشش می‌دهد.
- چهارده Negative case برای هر فرمان، یعنی ۶۸۶ انتساب، از session نامعتبر تا admin bypass، stale policy و bulk mixed-scope تعریف شده است.
- Decision Trace بیست‌ودو فیلد دارد و فقط reference/hash/status نگه می‌دارد.
- شانزده Gate برای هر فرمان ۷۸۴ انتساب و پنج Role برای هر فرمان ۲۴۵ انتساب می‌سازد؛ ده Outcome یک Allow معتبر را از انواع Deny جدا می‌کند.

## قواعد fail-closed

- Default deny و explicit deny-wins است؛ admin یا role name bypass ندارد.
- نمایش UI/Route مجوز نیست و check در Service بدون scope اجباری Repository کافی نیست.
- درخواست bulk با scope مختلط partial success ندارد و self-approval ممنوع است.
- Policy stale/revoked/version-mismatched فرمان را رد می‌کند.
- Decision Trace اجازهٔ ذخیرهٔ Identity، PII، Token یا مقدار تجاری خام ندارد.
- وجود حق تجمیعی Legacy یا کد مسیر هیچ Grant مقصدی ایجاد نمی‌کند.

## وضعیت فعلی

تمام ۵۸۸ بُعد `UNPROVEN`، همهٔ ۶۸۶ Negative case `UNEXECUTED`، ۷۸۴ Gate `UNMET` و ۲۴۵ Role `UNASSIGNED` است. Implementation، UAT، Allow/Deny receipt، Repository scope proof، route-to-repository coverage، Owner approval، Runtime authorization و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
