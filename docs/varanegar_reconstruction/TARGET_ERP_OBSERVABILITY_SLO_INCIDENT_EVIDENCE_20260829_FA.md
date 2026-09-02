# قرارداد Observability، SLO، Alert و Incident مقصد

دوازده کلاس Signal برای چهارده ماژول ۱۶۸ assignment و دوازده مرحلهٔ چرخهٔ پایش تا بستن Incident نیز ۱۶۸ assignment دارد. SLI receipt و SLO policy هرکدام هجده فیلد، Alert receipt بیست فیلد و Incident receipt بیست‌ودو فیلد است.

چهارده Failure case در چهارده ماژول ۱۹۶ assignment، بیست Gate تعداد ۲۸۰ و شش Role تعداد ۸۴ assignment دارد. بالا بودن Process موفقیت نیست؛ Technical health جای Business invariant را نمی‌گیرد و Missing/Stale telemetry هرگز Healthy محسوب نمی‌شود.

Label/Log/Trace حساس یا بی‌کران ممنوع است. Alert بدون Owner/Route/Runbook actionable نیست؛ Restart خودکار Incident را نمی‌بندد و Severity یا residual difference بدون Evidence کاهش یا waive نمی‌شود.

هیچ Metric، Log، Trace، Health sample یا Telemetry واقعی خوانده یا query نشد؛ Alert ارسال و Incident ایجاد نشد و Provider انتخاب نشده است. SLI implementation، SLO approval، Alert route، Rehearsal، Incident، Health receipt و Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
