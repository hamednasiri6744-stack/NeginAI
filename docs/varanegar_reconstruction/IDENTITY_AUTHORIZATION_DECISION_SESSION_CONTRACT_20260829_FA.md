# قرارداد تصمیم، انتساب و Session در هویت و مجوزدهی

این بسته فقط طراحی مقصد و crosswalk شواهد ایستا است؛ هیچ هویت، نقش، grant، scope، credential یا فرمان runtime خوانده یا تغییر داده نشده است.

شش فرمان مقصد انتشار نسخهٔ policy، انتساب capability مستقیم، عضویت گروه، انتساب data scope، revoke همراه با invalidation نشست و break-glass زمان‌دار را پوشش می‌دهند. هر فرمان `CommandId/PayloadHash/ExpectedVersion`، رسید تصمیم، audit، outbox و read-back پیش از retry دارد.

تصمیم deny-first است: نشست تازه و authenticated، deny صریح، مرز Application/Owner، action capability، data scope، SoD/self-grant و expiry به همین ترتیب بررسی می‌شوند. deny صریح بر allow مستقیم، گروهی، inherited یا admin مقدم است. Repository مقصد باید owner-filtered باشد و revoke با افزایش `SessionEpoch` اتمیک شود.

شاهد موجود ۷۸۴ endpoint، ۶۰ endpoint بدون declaration روشن، ۳۸ endpoint تغییردهنده در همان گروه، صفر manual decision نام‌دار، short-circuit نقش admin، سه subject منتسب به آن نقش و ۵۸ ناسازگاری scope را نشان می‌دهد. این اعداد proof مجوز مؤثر production نیستند.

۱۸۴ Case موجود reuse می‌شوند، ولی owner approval، production assignment، اجرای UAT، runtime parity، command readiness و pilot readiness همگی صفر باقی می‌مانند. Artifact فقط opaque principal-reference hash و hashهای policy/scope را مجاز می‌داند؛ نام، شناسه، credential و ردیف خام grant ممنوع است.
