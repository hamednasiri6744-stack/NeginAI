# قرارداد Release Promotion، Change و Rollback مقصد

دو Transition از Sandbox به UAT و UAT به Production برای چهارده ماژول ۲۸ assignment دارد. هشت کلاس Artifact در چهارده ماژول ۱۱۲ assignment و دوازده مرحلهٔ Release تعداد ۱۶۸ assignment ایجاد می‌کند.

Release manifest دارای ۲۲ فیلد، Change receipt بیست فیلد و Rollback receipt هجده فیلد است. دوازده Failure case در چهارده ماژول ۱۶۸ assignment، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ assignment دارد.

Artifact بین محیط‌ها rebuild نمی‌شود و digest باید یکسان بماند. UAT approval مجوز Production نیست؛ application start بدون Health/SLO/Business invariants موفقیت نیست؛ Migration بدون compatibility/rollback boundary و Rollback مخربِ forward-only data ممنوع است.

هیچ Build/Registry/Deploy/Migration/Health-check/Promotion/Rollback اجرا نشده و هیچ Provider انتخاب نشده است. Manifest/Digest/Deploy/Promotion/Production approval/Rollback/Health acceptance/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
