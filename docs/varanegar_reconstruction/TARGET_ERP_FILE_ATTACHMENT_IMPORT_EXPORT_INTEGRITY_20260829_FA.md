# قرارداد File/Attachment Import-Export Integrity مقصد

چهارده بُعد File integrity برای چهارده ماژول ۱۹۶ assignment و دوازده Stage تعداد ۱۶۸ assignment دارد. File manifest و Scan receipt هرکدام بیست‌ودو و Quarantine/Disposition receipt هرکدام بیست فیلد دارد.

شانزده Failure case تعداد ۲۲۴، بیست‌ودو Gate تعداد ۳۰۸ و هفت Role تعداد ۹۸ assignment دارد. Extension/MIME اعلامی قابل اعتماد نیست؛ path traversal، zip-slip، symlink، archive bomb و parser resource نامحدود ممنوع است.

Scanner error/timeout/unknown fail-closed و Quarantine غیرقابل preview/download/export است. Sanitized derivative جای Original immutable را نمی‌گیرد؛ Download دوباره authorization و TTL/revocation را بررسی می‌کند.

هیچ File/Attachment/Archive/Import/Export/Body عملیاتی باز یا خوانده و هیچ Scanner/Parser/Quarantine اجرا نشد. Provider/Scan/Release/Disposition/Readiness همگی صفر و پایهٔ ۸۴/۳۴۳ و lower bound ۱۴۰۴ ثابت است.
